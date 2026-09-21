import json

import pytest
from sqlalchemy.exc import OperationalError

from api.upload import _job_payload
from models.processing_job import ProcessingJob
from ulpf_queue.consumer import KafkaConsumerWorker


class RawMessage:
    topic = "raw-logs-ingested"
    partition = 0
    offset = 7

    def __init__(self, payload):
        self.value = payload


class Consumer:
    def __init__(self, message=None):
        self.message = message

    async def getone(self):
        return self.message

    async def commit(self, *_args, **_kwargs):
        return None


class FailingProducer:
    async def send_and_wait(self, *_args, **_kwargs):
        raise RuntimeError("broker unavailable")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "payload",
    [
        b"not-json",
        json.dumps({"message_id": "bad", "upload_id": "bad"}).encode(),
        json.dumps({}).encode(),
    ],
)
async def test_poison_messages_route_to_dlq_without_raising(monkeypatch, payload):
    worker = KafkaConsumerWorker()
    worker.consumer = Consumer(RawMessage(payload))
    routed = []

    async def route(message, error):
        routed.append((message, error))

    monkeypatch.setattr(worker, "_handle_poison_message", route)
    await worker._consume_one_safely()

    assert len(routed) == 1
    assert isinstance(routed[0][1], ValueError)


@pytest.mark.asyncio
async def test_retryable_database_error_is_not_sent_to_dlq(monkeypatch):
    worker = KafkaConsumerWorker()
    worker.consumer = Consumer(RawMessage(b"{}"))
    routed = []

    async def process(_message):
        raise OperationalError("query", {}, RuntimeError("database unavailable"))

    async def route(message, error):
        routed.append((message, error))

    monkeypatch.setattr(worker, "_process_message", process)
    monkeypatch.setattr(worker, "_handle_poison_message", route)
    monkeypatch.setattr("ulpf_queue.consumer.asyncio.sleep", _no_sleep)
    await worker._consume_one_safely()

    assert routed == []


@pytest.mark.asyncio
async def test_dlq_publish_failure_does_not_propagate(monkeypatch):
    worker = KafkaConsumerWorker()
    worker.consumer = Consumer()
    worker.dlq_producer = FailingProducer()
    monkeypatch.setattr("ulpf_queue.consumer.asyncio.sleep", _no_sleep)

    await worker._handle_poison_message(RawMessage(b"bad"), ValueError("bad payload"))


def _no_sleep(_delay):
    async def done():
        return None

    return done()


def test_job_status_and_batch_shape_match_frontend_contract():
    job = ProcessingJob(
        total_files=2,
        processed_files=0,
        failed_files=0,
        total_records=0,
        processed_records=0,
        failed_records=0,
        processing_time=0,
        status="queued",
    )
    payload = _job_payload(job)
    assert payload["status"] == payload["status"].lower()
    assert {
        "job_id", "status", "files", "processed", "failed", "remaining", "records",
        "processed_records", "failed_records", "progress_percent", "started_at",
        "completed_at", "error_message", "processing_time", "details",
    } <= payload.keys()
