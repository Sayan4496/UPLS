import os

from dotenv import load_dotenv


load_dotenv()


DATA_LAKE_ENABLED = os.getenv("DATA_LAKE_ENABLED", "false").strip().lower() in {
	"1",
	"true",
	"yes",
	"on",
}
DATA_LAKE_EXPORT_INTERVAL_SECONDS = int(
	os.getenv("DATA_LAKE_EXPORT_INTERVAL_SECONDS", "300")
)
DATA_LAKE_BATCH_SIZE = int(os.getenv("DATA_LAKE_BATCH_SIZE", "1000"))
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "http://minio:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ROOT_USER", "")
MINIO_SECRET_KEY = os.getenv("MINIO_ROOT_PASSWORD", "")
MINIO_BUCKET = os.getenv("MINIO_BUCKET", "ulpf-datalake")
