import os
import json
import uuid
from datetime import datetime, timezone
from typing import Any

from aiokafka import AIOKafkaProducer

from detection.format_detector import FormatDetector


DEFAULT_BOOTSTRAP_SERVERS = "redpanda:9092"
DEFAULT_INGESTED_TOPIC = "raw-logs-ingested"
DEFAULT_DLQ_TOPIC = "raw-logs-dlq"


def is_queue_enabled() -> bool:
    return os.getenv("QUEUE_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


class KafkaProducer:
    def __init__(
        self,
        bootstrap_servers: str | None = None,
        ingested_topic: str | None = None,
        dlq_topic: str | None = None,
    ):
        self.bootstrap_servers = bootstrap_servers or os.getenv(
            "KAFKA_BOOTSTRAP_SERVERS",
            DEFAULT_BOOTSTRAP_SERVERS,
        )
        self.ingested_topic = ingested_topic or os.getenv(
            "KAFKA_INGESTED_TOPIC",
            DEFAULT_INGESTED_TOPIC,
        )
        self.dlq_topic = dlq_topic or os.getenv(
            "KAFKA_DLQ_TOPIC",
            DEFAULT_DLQ_TOPIC,
        )
        self._producer: AIOKafkaProducer | None = None

    async def start(self) -> None:
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            client_id="ulpf-api",
        )
        await self._producer.start()

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
            self._producer = None

    async def publish(
        self,
        upload: Any,
        raw_content: str | None = None,
        source_metadata: dict[str, Any] | None = None,
        job_id: str | None = None,
        object_key: str | None = None,
        filename: str | None = None,
        file_format: str | None = None,
    ) -> dict[str, Any]:
        if self._producer is None:
            raise RuntimeError("Kafka producer has not been started")

        message = {
            "message_id": str(uuid.uuid4()),
            "upload_id": str(upload.id),
            "job_id": job_id,
            "object_key": object_key,
            "filename": filename or getattr(upload, "filename", None),
            "format": file_format or getattr(upload, "file_type", None),
            "source_metadata": source_metadata or {},
            "ingested_at": datetime.now(timezone.utc).isoformat(),
        }

        if raw_content is not None:
            message["raw_content"] = raw_content
            message["format_detection"] = FormatDetector.detect_with_confidence(raw_content)

        await self._producer.send_and_wait(
            self.ingested_topic,
            value=json.dumps(message, default=str).encode("utf-8"),
        )

        return message
