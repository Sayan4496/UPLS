from datetime import datetime, timezone
import time
from typing import List

from fastapi import APIRouter, BackgroundTasks, UploadFile, File, HTTPException, Request

from core.database import SessionLocal

from models.upload import Upload
from models.processing_job import ProcessingJob

from ingestion.validator import validate_file
from ingestion.file_handler import read_uploaded_file

from ingestion.processing_service import ProcessingService
from ulpf_queue.producer import KafkaProducer, is_queue_enabled
from storage.object_store import object_key_for_upload, upload_fileobj
from starlette.concurrency import run_in_threadpool


router = APIRouter(
    prefix="/upload",
    tags=["Upload"]
)


def _process_upload_content(db, filename, content):
    validate_file(filename)

    file_type = filename.split(".")[-1].upper()

    upload = Upload(
        filename=filename,
        file_type=file_type
    )

    db.add(upload)
    db.commit()
    db.refresh(upload)

    processing_service = ProcessingService()
    result = processing_service.process(
        db=db,
        upload=upload,
        raw_content=content
    )

    return {
        "upload_id": str(upload.id),
        "filename": upload.filename,
        "file_type": upload.file_type,
        "processing_result": result
    }


async def _process_single_upload(db, file: UploadFile, producer: KafkaProducer | None = None):
    started_counter = time.perf_counter()
    queue_mode = producer is not None and is_queue_enabled()
    job = ProcessingJob(
        total_files=1,
        status="queued" if queue_mode else "processing",
        started_at=None if queue_mode else datetime.now(timezone.utc),
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    try:
        if queue_mode:
            validate_file(file.filename)
            upload = Upload(filename=file.filename, file_type=file.filename.split(".")[-1].upper())
            db.add(upload)
            db.commit()
            db.refresh(upload)
            object_key = object_key_for_upload(upload.id, file.filename)
            await file.seek(0)
            await run_in_threadpool(upload_fileobj, file.file, object_key)
            message = await producer.publish(
                upload=upload,
                source_metadata={"filename": file.filename, "file_type": upload.file_type},
                job_id=str(job.id),
                object_key=object_key,
                filename=file.filename,
                file_format=upload.file_type,
            )
            job.message_id = message["message_id"]
            job.details = [{"file": file.filename, "status": "QUEUED", "object_key": object_key}]
            db.commit()
            return {
                "upload_id": str(upload.id),
                "filename": upload.filename,
                "file_type": upload.file_type,
                "processing_result": None,
                "job": _job_payload(job),
            }

        content = await read_uploaded_file(file)
        result = _process_upload_content(db, file.filename, content)
        elapsed = time.perf_counter() - started_counter
        parsed_records = result["processing_result"].get("parsed_events", 0)
        job.details = [_file_detail(file.filename, result, elapsed)]
        job.processing_time = elapsed
        job.total_records = parsed_records
        job.processed_records = parsed_records
        job.processed_files = 1
        job.status = "done"
        job.completed_at = datetime.now(timezone.utc)
        db.commit()

        return {
            **result,
            "job": _job_payload(job)
        }
    except Exception as error:
        db.rollback()
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job.id).first()
        job.status = "failed"
        job.failed_files = 1
        job.error_message = str(error)
        job.completed_at = datetime.now(timezone.utc)
        db.commit()
        raise


def _job_payload(job):
    total_files = max(job.total_files, 1)
    progress = round((job.processed_files / total_files) * 100)

    return {
        "job_id": str(job.id),
        "status": job.status,
        "message_id": job.message_id,
        "queue_offset": job.queue_offset,
        "files": job.total_files,
        "processed": job.processed_files,
        "failed": job.failed_files,
        "remaining": max(job.total_files - job.processed_files - job.failed_files, 0),
        "records": job.total_records,
        "processed_records": job.processed_records,
        "failed_records": job.failed_records,
        "progress_percent": progress,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "error_message": job.error_message,
        "processing_time": job.processing_time or 0,
        "details": job.details or []
    }


def _file_detail(filename, result, elapsed, error=None):
    if error:
        return {
            "file": filename,
            "format": filename.rsplit(".", 1)[-1].upper() if "." in filename else "UNKNOWN",
            "records": 0,
            "success": 0,
            "failed": 0,
            "status": "FAILED",
            "parser": None,
            "parser_version": None,
            "quality_score": 0,
            "skipped_line_count": getattr(error, "skipped_line_count", 0),
            "parse_errors": getattr(error, "parse_errors", []),
            "processing_time": round(elapsed, 3),
            "error": str(error)
        }

    processing_result = result["processing_result"]
    metrics = processing_result.get("quality_metrics", {})
    records = processing_result.get("parsed_events", 0)
    failed = metrics.get("failed", 0)
    return {
        "file": filename,
        "format": processing_result.get("format"),
        "records": records,
        "success": max(records - failed, 0),
        "failed": failed,
        "status": "PARTIAL" if failed else "COMPLETE",
        "parser": f"{processing_result.get('format', 'unknown').lower()}_parser",
        "parser_version": "1.0.0",
        "quality_score": metrics.get("schema_completeness", 0),
        "skipped_line_count": metrics.get("skipped_line_count", 0),
        "parse_errors": metrics.get("parse_errors", []),
        "processing_time": round(elapsed, 3),
        "error": None
    }


async def _run_batch_job(job_id, file_payloads, producer: KafkaProducer | None = None):
    db = SessionLocal()
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()

    if job is None:
        db.close()
        return

    try:
        queue_mode = producer is not None and is_queue_enabled()
        job.status = "queued" if queue_mode else "processing"
        job.started_at = None if queue_mode else datetime.now(timezone.utc)
        db.commit()

        for filename, content in file_payloads:
            file_started = time.perf_counter()
            try:
                if queue_mode:
                    validate_file(filename)
                    upload = Upload(filename=filename, file_type=filename.split(".")[-1].upper())
                    db.add(upload)
                    db.commit()
                    db.refresh(upload)
                    await producer.publish(
                        upload=upload,
                        raw_content=content,
                        source_metadata={"filename": filename, "file_type": upload.file_type},
                        job_id=str(job.id),
                    )
                    job.details = list(job.details or []) + [{"file": filename, "status": "QUEUED", "processing_time": 0}]
                    db.commit()
                    continue

                result = _process_upload_content(db, filename, content)
                processing_result = result["processing_result"]
                elapsed = time.perf_counter() - file_started
                job.details = list(job.details or []) + [_file_detail(filename, result, elapsed)]
                job.processed_files += 1
                job.processed_records += processing_result.get("parsed_events", 0)
                job.total_records += processing_result.get("parsed_events", 0)
                job.processing_time += elapsed
            except Exception as error:
                elapsed = time.perf_counter() - file_started
                db.rollback()
                job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
                job.details = list(job.details or []) + [_file_detail(filename, None, elapsed, error)]
                job.failed_files += 1
                job.error_message = str(error)
                job.processing_time += elapsed

            db.commit()

        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if not queue_mode:
            job.status = "failed" if job.failed_files else "done"
            job.completed_at = datetime.now(timezone.utc)
        db.commit()

    except Exception as error:
        db.rollback()
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job:
            job.status = "failed"
            job.error_message = str(error)
            job.completed_at = datetime.now(timezone.utc)
            db.commit()
    finally:
        db.close()


@router.post("/")
async def upload_file(request: Request, file: UploadFile = File(...)):
    db = SessionLocal()

    try:
        result = await _process_single_upload(
            db,
            file,
            getattr(request.app.state, "kafka_producer", None),
        )

        return {
            "message": "File processed successfully",
            **result
        }

    except ValueError as e:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

    finally:
        db.close()


@router.post("/batch", status_code=202)
async def upload_batch(
    request: Request,
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...)
):
    if not files:
        raise HTTPException(
            status_code=400,
            detail="No files provided."
        )

    file_payloads = []
    job = None

    try:
        for file in files:
            if file.filename is None or not file.filename.strip():
                raise HTTPException(
                    status_code=400,
                    detail="One or more files are missing a filename."
                )

            validate_file(file.filename)
            if is_queue_enabled() and getattr(request.app.state, "kafka_producer", None) is not None:
                file_payloads.append((file.filename, file))
            else:
                file_payloads.append((file.filename, await read_uploaded_file(file)))

        db = SessionLocal()
        job = ProcessingJob(total_files=len(file_payloads))
        db.add(job)
        db.commit()
        db.refresh(job)
        job_response = _job_payload(job)
        db.close()

        producer = getattr(request.app.state, "kafka_producer", None)
        if producer is not None and is_queue_enabled():
            for filename, upload_file in file_payloads:
                upload = Upload(filename=filename, file_type=filename.split(".")[-1].upper())
                db = SessionLocal()
                try:
                    db.add(upload)
                    db.commit()
                    db.refresh(upload)
                finally:
                    db.close()
                object_key = object_key_for_upload(upload.id, filename)
                await upload_file.seek(0)
                await run_in_threadpool(upload_fileobj, upload_file.file, object_key)
                message = await producer.publish(
                    upload=upload,
                    source_metadata={"filename": filename, "file_type": upload.file_type},
                    job_id=str(job.id),
                    object_key=object_key,
                    filename=filename,
                    file_format=upload.file_type,
                )
                db = SessionLocal()
                try:
                    job = db.query(ProcessingJob).filter(ProcessingJob.id == job.id).one()
                    job.message_id = message["message_id"]
                    job.details = list(job.details or []) + [{"file": filename, "status": "QUEUED", "object_key": object_key}]
                    db.commit()
                finally:
                    db.close()
        else:
            background_tasks.add_task(_run_batch_job, job.id, file_payloads, producer)

        return {
            "message": "Batch processing job created",
            **job_response,
            "status_url": f"/upload/jobs/{job.id}"
        }

    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )

    except HTTPException:
        raise

    except Exception as e:
        if job is not None:
            failure_db = SessionLocal()
            try:
                failed_job = failure_db.query(ProcessingJob).filter(ProcessingJob.id == job.id).first()
                if failed_job is not None:
                    failed_job.status = "failed"
                    failed_job.failed_files = max(failed_job.failed_files, 1)
                    failed_job.error_message = str(e)
                    failed_job.completed_at = datetime.now(timezone.utc)
                    failure_db.commit()
            finally:
                failure_db.close()
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@router.get("/jobs/{job_id}")
def get_processing_job(job_id: str):
    db = SessionLocal()
    try:
        job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
        if job is None:
            raise HTTPException(status_code=404, detail="Processing job not found.")
        return _job_payload(job)
    finally:
        db.close()


@router.get("/jobs")
def list_processing_jobs(limit: int = 50):
    db = SessionLocal()
    try:
        jobs = (
            db.query(ProcessingJob)
            .order_by(ProcessingJob.created_at.desc())
            .limit(min(max(limit, 1), 100))
            .all()
        )
        return {"jobs": [_job_payload(job) for job in jobs]}
    finally:
        db.close()
