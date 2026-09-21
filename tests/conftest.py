import os
import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1] / "universal-log-framework"
BACKEND_ROOT = PROJECT_ROOT / "backend"
sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def sample_logs():
    return {
        "json_object": '{"event_type":"login","severity":"LOW"}',
        "json_array": '[{"event_type":"login"},{"event_type":"logout"}]',
        "json_lines": '{"event_type":"login"}\n{"event_type":"logout"}\n',
        "cef": "CEF:0|Acme|Sensor|1.0|42|Login|5|src=10.0.0.1 dst=10.0.0.2 act=deny",
        "leef": "LEEF:2.0|Acme|Sensor|1.0|42|src=10.0.0.1\tact=deny",
        "keyvalue": "src=10.0.0.1 dst=10.0.0.2 action=deny",
    }


@pytest.fixture(scope="session")
def test_database_url():
    value = os.getenv("TEST_DATABASE_URL")
    if not value:
        pytest.skip("Set TEST_DATABASE_URL to run database-backed tests")
    if value == os.getenv("DATABASE_URL"):
        pytest.fail("TEST_DATABASE_URL must not point at DATABASE_URL")
    return value


@pytest.fixture(scope="session")
def test_engine(test_database_url):
    from sqlalchemy import create_engine

    from core.database import Base
    from models.normalized_event import NormalizedEvent
    from models.normalized_event_features import NormalizedEventFeatures
    from models.raw_event import RawEvent
    from models.upload import Upload

    engine = create_engine(test_database_url, pool_pre_ping=True)
    tables = [Upload.__table__, RawEvent.__table__, NormalizedEvent.__table__, NormalizedEventFeatures.__table__]
    Base.metadata.create_all(engine, tables=tables)
    yield engine
    Base.metadata.drop_all(engine, tables=list(reversed(tables)))
    engine.dispose()


@pytest.fixture
def db_session(test_engine):
    from sqlalchemy.orm import sessionmaker

    connection = test_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(bind=connection, expire_on_commit=False)()
    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()
