import json
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from core.database import SessionLocal
from ingestion.processing_service import ProcessingService
from models.upload import Upload


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
async def ingest_log(payload: LogIngestRequest):
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

        processing_service = ProcessingService()

        result = processing_service.process(
            db=db,
            upload=upload,
            raw_content=raw_content
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
