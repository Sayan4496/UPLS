import hashlib
import io
import json
import logging
import time
from datetime import datetime, timezone
from typing import Any

import boto3
import pyarrow as pa
import pyarrow.parquet as pq
from botocore.exceptions import BotoCoreError, ClientError, EndpointConnectionError
from sqlalchemy import text

from core.config import (
    DATA_LAKE_BATCH_SIZE,
    DATA_LAKE_ENABLED,
    DATA_LAKE_EXPORT_INTERVAL_SECONDS,
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
)
from core.database import SessionLocal
from models.normalized_event import NormalizedEvent


logger = logging.getLogger("ulpf-datalake-exporter")
MAX_UPLOAD_ATTEMPTS = 3
UPLOAD_RETRY_DELAY_SECONDS = 2
EXPORT_RETRY_DELAY_SECONDS = 2
EXPORT_RETRY_MAX_DELAY_SECONDS = 60


class MissingBucketError(RuntimeError):
    pass


class DataLakeExporter:
    def __init__(self):
        self.s3 = boto3.client(
            "s3",
            endpoint_url=MINIO_ENDPOINT,
            aws_access_key_id=MINIO_ACCESS_KEY,
            aws_secret_access_key=MINIO_SECRET_KEY,
            region_name="us-east-1",
        )

    def ensure_bucket(self) -> None:
        try:
            self.s3.head_bucket(Bucket=MINIO_BUCKET)
        except ClientError as error:
            code = str(error.response.get("Error", {}).get("Code", ""))
            status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
            if code in {"404", "NoSuchBucket", "NotFound"} or status == 404:
                self.s3.create_bucket(Bucket=MINIO_BUCKET)
                return
            if code in {"403", "AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
                raise RuntimeError("MinIO authentication or authorization failed") from error
            raise RuntimeError(f"MinIO bucket check failed: {code or status}") from error
        except (EndpointConnectionError, BotoCoreError) as error:
            raise RuntimeError("MinIO is unreachable") from error

    def export_once(self) -> dict[str, Any]:
        if not DATA_LAKE_ENABLED:
            return self._update_state(status="disabled", error=None)

        db = SessionLocal()
        try:
            state = self._read_state(db)
            rows = self._read_batch(db, state)
            if not rows:
                return self._update_state(
                    status="idle",
                    error=None,
                    watermark=state,
                    partition_count=len(state["partition_coverage"]),
                    partition_coverage=state["partition_coverage"],
                )

            self.ensure_bucket()
            partition_keys = self._write_partitions(rows)
            last = rows[-1]
            watermark = {
                "normalized_at": last.normalized_at,
                "event_id": last.id,
            }
            partition_coverage = sorted(set(state["partition_coverage"]) | set(partition_keys))
            exported = self._update_state(
                status="idle",
                error=None,
                rows_exported=(state["rows_exported"] + len(rows)),
                watermark=watermark,
                partition_count=len(partition_coverage),
                partition_coverage=partition_coverage,
            )
            db.commit()
            return exported
        except Exception as error:
            db.rollback()
            logger.exception("Data lake export failed")
            return self._update_state(status="error", error=str(error))
        finally:
            db.close()

    def run_forever(self) -> None:
        logger.info(
            "Data lake exporter started: enabled=%s interval=%ss bucket=%s",
            DATA_LAKE_ENABLED,
            DATA_LAKE_EXPORT_INTERVAL_SECONDS,
            MINIO_BUCKET,
        )
        retry_delay = EXPORT_RETRY_DELAY_SECONDS
        while True:
            started = time.monotonic()
            result = self.export_once()
            elapsed = time.monotonic() - started
            if result.get("status") == "error":
                time.sleep(retry_delay)
                retry_delay = min(retry_delay * 2, EXPORT_RETRY_MAX_DELAY_SECONDS)
            else:
                retry_delay = EXPORT_RETRY_DELAY_SECONDS
                time.sleep(max(DATA_LAKE_EXPORT_INTERVAL_SECONDS - elapsed, 1))

    def _read_batch(self, db, state: dict[str, Any]) -> list[NormalizedEvent]:
        query = db.query(NormalizedEvent).order_by(
            NormalizedEvent.normalized_at.asc(),
            NormalizedEvent.id.asc(),
        )
        if state["normalized_at"] is not None:
            query = query.filter(
                (NormalizedEvent.normalized_at > state["normalized_at"])
                | (
                    (NormalizedEvent.normalized_at == state["normalized_at"])
                    & (NormalizedEvent.id > state["event_id"])
                )
            )
        return query.limit(DATA_LAKE_BATCH_SIZE).all()

    def _write_partitions(self, rows: list[NormalizedEvent]) -> list[str]:
        partitions: dict[tuple[str, str, str, str], list[NormalizedEvent]] = {}
        for row in rows:
            timestamp = row.normalized_at or datetime.now(timezone.utc)
            source = self._safe_partition_value(row.source_format or "UNKNOWN")
            key = (timestamp.strftime("%Y"), timestamp.strftime("%m"), timestamp.strftime("%d"), source)
            partitions.setdefault(key, []).append(row)

        partition_keys = []
        for (year, month, day, source), partition_rows in partitions.items():
            table = pa.Table.from_pylist([self._row_to_dict(row) for row in partition_rows])
            buffer = io.BytesIO()
            pq.write_table(table, buffer, compression="snappy")
            first_id = str(partition_rows[0].id)
            last_id = str(partition_rows[-1].id)
            digest = hashlib.sha256(f"{first_id}:{last_id}".encode("utf-8")).hexdigest()[:16]
            object_key = (
                f"normalized_events/year={year}/month={month}/day={day}/"
                f"source={source}/part-{digest}.parquet"
            )
            self._upload_with_retry(object_key, buffer.getvalue())
            partition_keys.append(f"normalized_events/year={year}/month={month}/day={day}/source={source}")
        return partition_keys

    def _upload_with_retry(self, object_key: str, payload: bytes) -> None:
        delay = UPLOAD_RETRY_DELAY_SECONDS
        for attempt in range(1, MAX_UPLOAD_ATTEMPTS + 1):
            try:
                self.s3.put_object(
                    Bucket=MINIO_BUCKET,
                    Key=object_key,
                    Body=payload,
                    ContentType="application/vnd.apache.parquet",
                )
                return
            except ClientError as error:
                code = str(error.response.get("Error", {}).get("Code", ""))
                if code in {"403", "AccessDenied", "InvalidAccessKeyId", "SignatureDoesNotMatch"}:
                    raise RuntimeError("MinIO authentication or authorization failed") from error
                if attempt == MAX_UPLOAD_ATTEMPTS:
                    raise RuntimeError(f"MinIO upload failed: {code}") from error
            except (EndpointConnectionError, BotoCoreError) as error:
                if attempt == MAX_UPLOAD_ATTEMPTS:
                    raise RuntimeError("MinIO upload failed after retries") from error
            time.sleep(delay)
            delay *= 2

    @staticmethod
    def _row_to_dict(row: NormalizedEvent) -> dict[str, Any]:
        return {
            "id": str(row.id),
            "raw_event_id": str(row.raw_event_id),
            "upload_id": str(row.upload_id),
            "event_hash": row.event_hash,
            "normalized_at": row.normalized_at,
            "event_timestamp": row.event_timestamp,
            "source_format": row.source_format,
            "parser_used": row.parser_used,
            "parser_confidence": row.parser_confidence,
            "severity": row.severity,
            "event_type": row.event_type,
            "action": row.action,
            "device_type": row.device_type,
            "vendor": row.vendor,
            "message": row.message,
            "parsed_log": str(row.parsed_log),
            "normalized_log": str(row.normalized_log),
            "universal_event": str(row.universal_event),
        }

    @staticmethod
    def _safe_partition_value(value: str) -> str:
        return "".join(character if character.isalnum() or character in "-_" else "_" for character in value)

    @staticmethod
    def _read_state(db) -> dict[str, Any]:
        row = db.execute(text("""
            SELECT last_run_at, last_error, rows_exported, watermark_normalized_at,
                     watermark_id, partition_count, partition_coverage, status
            FROM datalake_export_state
            WHERE id = 1
        """)).mappings().one()
        return {
            "last_run_at": row["last_run_at"],
            "last_error": row["last_error"],
            "rows_exported": row["rows_exported"],
            "normalized_at": row["watermark_normalized_at"],
            "event_id": row["watermark_id"],
            "partition_count": row["partition_count"],
            "partition_coverage": row["partition_coverage"] or [],
            "status": row["status"],
        }

    @staticmethod
    def read_status() -> dict[str, Any]:
        db = SessionLocal()
        try:
            state = DataLakeExporter._read_state(db)
            return {
                "enabled": DATA_LAKE_ENABLED,
                "status": state["status"],
                "last_run_at": state["last_run_at"],
                "last_error": state["last_error"],
                "rows_exported": state["rows_exported"],
                "current_watermark": {
                    "normalized_at": state["normalized_at"],
                    "id": state["event_id"],
                },
                "partition_count": state["partition_count"],
            }
        finally:
            db.close()

    @staticmethod
    def _update_state(
        status: str,
        error: str | None,
        rows_exported: int | None = None,
        watermark: dict[str, Any] | None = None,
        partition_count: int | None = None,
        partition_coverage: list[str] | None = None,
    ) -> dict[str, Any]:
        db = SessionLocal()
        try:
            current = DataLakeExporter._read_state(db)
            db.execute(text("""
                UPDATE datalake_export_state
                SET status = :status,
                    last_run_at = now(),
                    last_error = :last_error,
                    rows_exported = :rows_exported,
                    watermark_normalized_at = :watermark_normalized_at,
                    watermark_id = :watermark_id,
                    partition_count = :partition_count,
                    partition_coverage = :partition_coverage
                WHERE id = 1
            """), {
                "status": status,
                "last_error": error,
                "rows_exported": current["rows_exported"] if rows_exported is None else rows_exported,
                "watermark_normalized_at": current["normalized_at"] if watermark is None else watermark["normalized_at"],
                "watermark_id": current["event_id"] if watermark is None else watermark["event_id"],
                "partition_count": current["partition_count"] if partition_count is None else partition_count,
                "partition_coverage": json.dumps(
                    current["partition_coverage"] if partition_coverage is None else partition_coverage
                ),
            })
            db.commit()
            return DataLakeExporter.read_status()
        finally:
            db.close()
