import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field

from core.database import SessionLocal
from ingestion.processing_service import ProcessingService
from models.upload import Upload
from models.processing_job import ProcessingJob
from ulpf_queue.producer import KafkaProducer, is_queue_enabled


def _job_payload(job):
    total_files = max(job.total_files, 1)
    return {
        "job_id": str(job.id), "status": job.status, "message_id": job.message_id,
        "queue_offset": job.queue_offset, "files": job.total_files,
        "processed": job.processed_files, "failed": job.failed_files,
        "remaining": max(job.total_files - job.processed_files - job.failed_files, 0),
        "records": job.total_records, "processed_records": job.processed_records,
        "failed_records": job.failed_records,
        "progress_percent": round((job.processed_files / total_files) * 100),
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message, "processing_time": job.processing_time or 0,
        "details": job.details or [],
    }


router = APIRouter(
    prefix="/api/v1/logs",
    tags=["Logs"]
)


class LogIngestRequest(BaseModel):
    timestamp: str | None = None
    source: str | None = None
    message: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="allow")


@router.post("/ingest")
async def ingest_log(request: Request, payload: LogIngestRequest):
    db = SessionLocal()

    try:
        ingest_payload = payload.model_dump(exclude_none=True)

        if not ingest_payload.get("timestamp"):
            ingest_payload["timestamp"] = (
                datetime.now(timezone.utc)
                .replace(microsecond=0)
                .isoformat()
                .replace("+00:00", "Z")
            )

        if ingest_payload.get("source"):
            ingest_payload["device_type"] = ingest_payload["source"]
            ingest_payload["vendor"] = ingest_payload["source"]

        raw_content = json.dumps(ingest_payload, default=str)

        timestamp_suffix = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S%f")
        upload = Upload(
            filename=f"realtime-log-{timestamp_suffix}.json",
            file_type="JSON"
        )

        db.add(upload)
        db.commit()
        db.refresh(upload)

        producer: KafkaProducer | None = getattr(request.app.state, "kafka_producer", None)
        if producer is not None and is_queue_enabled():
            job = ProcessingJob(total_files=1, status="queued")
            db.add(job)
            db.commit()
            db.refresh(job)
            message = await producer.publish(
                upload=upload, raw_content=raw_content,
                source_metadata={"source": payload.source, "ingestion_type": "rest"},
                job_id=str(job.id),
            )
            job.message_id = message["message_id"]
            db.commit()
            return {
                "message": "Log accepted for processing", "upload_id": str(upload.id),
                "source": payload.source, "processing_result": None, "job": _job_payload(job),
            }

        processing_service = ProcessingService()

        result = processing_service.process(
            db=db,
            upload=upload,
            raw_content=raw_content
        )

        if producer is not None:
            await producer.publish(
                upload=upload,
                raw_content=raw_content,
                source_metadata={
                    "source": payload.source,
                    "ingestion_type": "rest",
                },
            )

        return {
            "message": "Log ingested successfully",
            "upload_id": str(upload.id),
            "source": payload.source,
            "processing_result": result
        }

    except HTTPException:
        raise

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()
