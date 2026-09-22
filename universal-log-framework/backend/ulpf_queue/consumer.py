import asyncio
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer
from aiokafka.errors import CommitFailedError
from aiokafka.structs import TopicPartition
from sqlalchemy.exc import DBAPIError, OperationalError

from core.database import SessionLocal
from ingestion.processing_service import ProcessingService
from models.processing_job import ProcessingJob
from models.raw_event import RawEvent
from models.upload import Upload
from storage.object_store import ObjectStoreError, MissingObjectError, download_to_tempfile


logger = logging.getLogger("ulpf-worker")

DEFAULT_BOOTSTRAP_SERVERS = "redpanda:9092"
DEFAULT_INGESTED_TOPIC = "raw-logs-ingested"
DEFAULT_DLQ_TOPIC = "raw-logs-dlq"
DEFAULT_CONSUMER_GROUP = "ulpf-worker"

START_RETRY_ATTEMPTS = 5
START_RETRY_DELAY_SECONDS = 2
DLQ_RETRY_ATTEMPTS = 3
DLQ_RETRY_DELAY_SECONDS = 1

# These failures indicate that the same message should be retried after the
# infrastructure recovers. They must never be converted into poison messages.
RETRYABLE_ERRORS = (
    OperationalError,
    DBAPIError,
    ConnectionError,
    TimeoutError,
)


class PoisonMessageError(ValueError):
    """The message cannot be processed successfully by retrying it."""


class KafkaConsumerWorker:
    def __init__(self):
        self.bootstrap_servers = os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            DEFAULT_BOOTSTRAP_SERVERS,
        )
        self.ingested_topic = os.getenv(
            "KAFKA_INGESTED_TOPIC",
            DEFAULT_INGESTED_TOPIC,
        )
        self.dlq_topic = os.getenv(
            "KAFKA_DLQ_TOPIC",
            DEFAULT_DLQ_TOPIC,
        )
        self.consumer_group = os.getenv(
            "KAFKA_CONSUMER_GROUP",
            DEFAULT_CONSUMER_GROUP,
        )
        self.consumer: AIOKafkaConsumer | None = None
        self.dlq_producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self.consumer = AIOKafkaConsumer(
            self.ingested_topic,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.consumer_group,
            auto_offset_reset="earliest",
            enable_auto_commit=False,
            max_poll_interval_ms=300000,
            max_poll_records=1,
            session_timeout_ms=120000,
            heartbeat_interval_ms=30000,
            client_id=f"{self.consumer_group}-consumer",
        )
        self.dlq_producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id=f"{self.consumer_group}-dlq",
        )
        await self._start_consumer_with_retry()
        await self.dlq_producer.start()

    async def stop(self) -> None:
        try:
            if self.consumer is not None:
                await self.consumer.stop()
        finally:
            if self.dlq_producer is not None:
                await self.dlq_producer.stop()
                self.dlq_producer = None

    async def _start_consumer_with_retry(self) -> None:
        delay = START_RETRY_DELAY_SECONDS
        for attempt in range(1, START_RETRY_ATTEMPTS + 1):
            try:
                await self.consumer.start()
                logger.info(
                    "Kafka consumer started on %s, topic=%s, group=%s",
                    self.bootstrap_servers,
                    self.ingested_topic,
                    self.consumer_group,
                )
                return
            except Exception:
                if attempt == START_RETRY_ATTEMPTS:
                    logger.exception("Kafka consumer startup failed after %s attempts", attempt)
                    raise
                logger.warning(
                    "Kafka consumer startup attempt %s/%s failed; retrying in %ss",
                    attempt,
                    START_RETRY_ATTEMPTS,
                    delay,
                )
                await asyncio.sleep(delay)
                delay *= 2

    async def run_forever(self) -> None:
        await self.start()
        try:
            while True:
                await self._consume_one_safely()
        finally:
            await self.stop()

    async def _consume_one_safely(self) -> None:
        message = None
        try:
            if self.consumer is None:
                raise RuntimeError("Kafka consumer has not been started")
            message = await self.consumer.getone()
            await self._process_message(message)
        except CommitFailedError:
            logger.exception(
                "Kafka offset commit failed after database processing for message %s; "
                "the offset remains uncommitted and the message will be redelivered",
                self._message_identity(message),
            )
            await asyncio.sleep(START_RETRY_DELAY_SECONDS)
        except RETRYABLE_ERRORS:
            logger.exception(
                "Retryable infrastructure failure for message %s; offset remains uncommitted",
                self._message_identity(message),
            )
            await asyncio.sleep(START_RETRY_DELAY_SECONDS)
        except PoisonMessageError as error:
            await self._handle_poison_message(message, error)
        except Exception:
            # A message must never escape the receive-to-next-iteration boundary.
            # Unknown failures are treated as retryable rather than acknowledged.
            logger.exception(
                "Unexpected worker failure for message %s; offset remains uncommitted",
                self._message_identity(message),
            )
            await asyncio.sleep(START_RETRY_DELAY_SECONDS)

    async def _process_message(self, message: Any) -> None:
        payload = self._decode_payload(message.value)
        message_id = self._parse_uuid(payload.get("message_id"), "message_id")
        upload_id = self._parse_uuid(payload.get("upload_id"), "upload_id")
        job_id = payload.get("job_id")
        if job_id is not None:
            job_id = self._parse_uuid(job_id, "job_id")

        db = SessionLocal()
        job = None
        try:
            job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).one_or_none() if job_id else None
            if job is None:
                job = ProcessingJob(total_files=1)
                db.add(job)
            if any(detail.get("message_id") == str(message_id) for detail in (job.details or [])):
                await self.consumer.commit({TopicPartition(message.topic, message.partition): message.offset + 1})
                return
            job.status = "processing"
            job.message_id = str(message_id)
            job.queue_offset = message.offset
            job.started_at = job.started_at or datetime.now(timezone.utc)
            db.commit()
            db.refresh(job)

            upload = db.query(Upload).filter(Upload.id == upload_id).one_or_none()
            if upload is None:
                raise PoisonMessageError(f"Upload not found: {upload_id}")

            raw_content = payload.get("raw_content")
            object_key = payload.get("object_key")
            temp_file = None
            if raw_content is None and object_key:
                try:
                    temp_file = await asyncio.to_thread(download_to_tempfile, object_key)
                    raw_content = temp_file.read().decode("utf-8")
                except MissingObjectError as error:
                    raise PoisonMessageError(str(error)) from error
                except (ObjectStoreError, UnicodeDecodeError) as error:
                    raise ConnectionError(str(error)) from error
                finally:
                    if temp_file is not None:
                        temp_file.close()
            elif raw_content is None:
                raw_event = (
                    db.query(RawEvent).filter(RawEvent.upload_id == upload_id)
                    .order_by(RawEvent.created_at.asc(), RawEvent.id.asc()).first()
                )
                if raw_event is None:
                    raise PoisonMessageError(f"Raw event not found for upload: {upload_id}")
                raw_content = raw_event.raw_content

            result = ProcessingService().process(
                db=db,
                upload=upload,
                raw_content=raw_content,
            )

            processing_result = result.get("quality_metrics", {})
            job.processed_files += 1
            job.total_records += result.get("parsed_events", 0)
            job.processed_records += result.get("normalized_events_created", 0)
            job.failed_records += processing_result.get("failed", 0)
            job.status = "done" if job.processed_files + job.failed_files >= max(job.total_files, 1) else "processing"
            job.completed_at = datetime.now(timezone.utc) if job.status == "done" else None
            job.details = list(job.details or []) + [{
                "message_id": str(message_id), "queue_offset": message.offset,
                "format": result.get("format"), "records": result.get("parsed_events", 0),
                "normalized": result.get("normalized_events_created", 0),
                "failed": processing_result.get("failed", 0),
            }]
            db.commit()
            await self.consumer.commit({
                TopicPartition(message.topic, message.partition): message.offset + 1
            })
        except RETRYABLE_ERRORS:
            db.rollback()
            if job is not None:
                self._mark_job_failed(db, job, "retryable infrastructure failure")
            raise
        except (PoisonMessageError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            db.rollback()
            if job is not None:
                self._mark_job_dead_letter(db, job, "poison message")
            raise
        finally:
            db.close()

    async def _handle_poison_message(self, message: Any, error: Exception) -> None:
        if message is None or self.dlq_producer is None:
            logger.error("Poison message has no DLQ route: %s", error)
            return

        dlq_payload = {
            "error": str(error),
            "failed_at": datetime.now(timezone.utc).isoformat(),
            "source_topic": message.topic,
            "source_partition": message.partition,
            "source_offset": message.offset,
            "raw_message": self._safe_bytes(message.value),
        }

        delay = DLQ_RETRY_DELAY_SECONDS
        for attempt in range(1, DLQ_RETRY_ATTEMPTS + 1):
            try:
                await self.dlq_producer.send_and_wait(
                    self.dlq_topic,
                    value=json.dumps(dlq_payload).encode("utf-8"),
                )
                await self.consumer.commit({
                    TopicPartition(message.topic, message.partition): message.offset + 1
                })
                logger.warning(
                    "Poison message sent to DLQ and acknowledged: topic=%s partition=%s offset=%s",
                    message.topic,
                    message.partition,
                    message.offset,
                )
                return
            except Exception:
                logger.exception("DLQ attempt %s/%s failed", attempt, DLQ_RETRY_ATTEMPTS)
                if attempt < DLQ_RETRY_ATTEMPTS:
                    await asyncio.sleep(delay)
                    delay *= 2

        logger.error(
            "Unable to publish poison message to DLQ after %s attempts; source offset remains uncommitted",
            DLQ_RETRY_ATTEMPTS,
        )

    @staticmethod
    def _decode_payload(raw_value: bytes) -> dict[str, Any]:
        try:
            decoded = raw_value.decode("utf-8")
            payload = json.loads(decoded)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise PoisonMessageError(f"Invalid JSON message: {error}") from error

        if not isinstance(payload, dict):
            raise PoisonMessageError("Message payload must be a JSON object")
        return payload

    @staticmethod
    def _parse_uuid(value: Any, field_name: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(value))
        except (ValueError, AttributeError, TypeError) as error:
            raise PoisonMessageError(f"Invalid {field_name}: {value}") from error

    @staticmethod
    def _safe_bytes(value: Any) -> str:
        if isinstance(value, bytes):
            return value.decode("utf-8", errors="replace")
        return str(value)

    @staticmethod
    def _message_identity(message: Any) -> str:
        if message is None:
            return "unknown"
        return f"{message.topic}/{message.partition}/{message.offset}"

    @staticmethod
    def _mark_job_failed(db, job: ProcessingJob, reason: str) -> None:
        try:
            job.status = "failed"
            job.failed_files = 1
            job.error_message = reason
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Unable to record worker job failure")

    @staticmethod
    def _mark_job_dead_letter(db, job: ProcessingJob, reason: str) -> None:
        try:
            job.status = "dead_letter"
            job.failed_files = 1
            job.error_message = reason
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()
            logger.exception("Unable to record dead-letter job state")
