import tempfile
from pathlib import Path
from typing import BinaryIO

import boto3
from botocore.exceptions import ClientError, EndpointConnectionError

from core.config import (
    MINIO_ACCESS_KEY,
    MINIO_BUCKET,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
)
OBJECT_READ_CHUNK_SIZE = 1024 * 1024


class ObjectStoreError(RuntimeError):
    pass


class MissingObjectError(ObjectStoreError):
    pass


def _client():
    return boto3.client(
        "s3",
        endpoint_url=MINIO_ENDPOINT,
        aws_access_key_id=MINIO_ACCESS_KEY,
        aws_secret_access_key=MINIO_SECRET_KEY,
        region_name="us-east-1",
    )


def ensure_bucket() -> None:
    client = _client()
    try:
        client.head_bucket(Bucket=MINIO_BUCKET)
    except ClientError as error:
        code = str(error.response.get("Error", {}).get("Code", ""))
        status = error.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
        if code in {"404", "NoSuchBucket", "NotFound"} or status == 404:
            client.create_bucket(Bucket=MINIO_BUCKET)
            return
        raise ObjectStoreError(f"Object store bucket check failed: {code or status}") from error
    except EndpointConnectionError as error:
        raise ObjectStoreError("Object store is unreachable") from error


def upload_fileobj(file_obj: BinaryIO, object_key: str) -> None:
    try:
        ensure_bucket()
        file_obj.seek(0)
        _client().upload_fileobj(
            file_obj,
            MINIO_BUCKET,
            object_key,
            ExtraArgs={"ContentType": "text/plain"},
        )
    except ObjectStoreError:
        raise
    except Exception as error:
        raise ObjectStoreError(f"Object upload failed: {error}") from error


def download_to_tempfile(object_key: str):
    temp_file = tempfile.TemporaryFile(mode="w+b")
    try:
        response = _client().get_object(Bucket=MINIO_BUCKET, Key=object_key)
        body = response["Body"]
        for chunk in body.iter_chunks(chunk_size=OBJECT_READ_CHUNK_SIZE):
            if chunk:
                temp_file.write(chunk)
        body.close()
        temp_file.seek(0)
        return temp_file
    except ClientError as error:
        temp_file.close()
        code = str(error.response.get("Error", {}).get("Code", ""))
        if code in {"404", "NoSuchKey", "NoSuchBucket"}:
            raise MissingObjectError(f"Object not found: {object_key}") from error
        raise ObjectStoreError(f"Object download failed: {code or error}") from error
    except Exception as error:
        temp_file.close()
        raise ObjectStoreError(f"Object download failed: {error}") from error


def object_key_for_upload(upload_id, filename: str) -> str:
    suffix = Path(filename or "upload.log").suffix.lower() or ".log"
    return f"uploads/{upload_id}/source{suffix}"