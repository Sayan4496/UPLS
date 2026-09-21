from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy.exc import IntegrityError

from models.normalized_event import NormalizedEvent
from models.raw_event import RawEvent
from models.upload import Upload


def _create_event(session, event_hash, upload_id, raw_event_id):
    return NormalizedEvent(
        raw_event_id=raw_event_id,
        upload_id=upload_id,
        event_hash=event_hash,
        parsed_log={},
        normalized_log={},
        parser_used="test",
        source_format="JSON",
        parser_confidence=1.0,
        parser_metadata={},
        processing_time=0.0,
    )


def test_same_event_twice_has_one_normalized_row(db_session):
    upload = Upload(filename="test.json", file_type="JSON")
    db_session.add(upload)
    db_session.flush()
    raw = RawEvent(upload_id=upload.id, raw_log="{}", original_format="JSON", checksum="a" * 64)
    db_session.add(raw)
    db_session.flush()
    db_session.add(_create_event(db_session, "b" * 64, upload.id, raw.id))
    db_session.commit()

    duplicate = _create_event(db_session, "b" * 64, upload.id, raw.id)
    db_session.add(duplicate)
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
    assert db_session.query(NormalizedEvent).filter_by(event_hash="b" * 64).count() == 1


def test_concurrent_same_fingerprint_is_constrained(test_engine, db_session):
    upload = Upload(filename="concurrent.json", file_type="JSON")
    db_session.add(upload)
    db_session.flush()
    raw_one = RawEvent(upload_id=upload.id, raw_log="{}", original_format="JSON", checksum="c" * 64)
    raw_two = RawEvent(upload_id=upload.id, raw_log="{}", original_format="JSON", checksum="d" * 64)
    db_session.add_all([raw_one, raw_two])
    db_session.commit()

    def insert_one(raw_id):
        from sqlalchemy.orm import sessionmaker

        session = sessionmaker(bind=test_engine, expire_on_commit=False)()
        try:
            session.add(_create_event(session, "e" * 64, upload.id, raw_id))
            session.commit()
            return "inserted"
        except IntegrityError:
            session.rollback()
            return "constrained"
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(insert_one, [raw_one.id, raw_two.id]))

    assert sorted(results) == ["constrained", "inserted"]
    assert db_session.query(NormalizedEvent).filter_by(event_hash="e" * 64).count() == 1