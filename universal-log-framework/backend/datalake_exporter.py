import logging

from core.database import ensure_database_schema
from datalake.exporter import DataLakeExporter


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)


if __name__ == "__main__":
    ensure_database_schema()
    DataLakeExporter().run_forever()
