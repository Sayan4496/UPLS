from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from core.database import engine
from api.upload import router as upload_router
from api.events import router as events_router
from api.analytics import router as analytics_router
from api.parser_lab import router as parser_lab_router
from api.logs import router as logs_router
from api.export import router as export_router


app = FastAPI(
    title="Universal Log Pre-processing Framework",
    description="A framework for parsing and normalizing heterogeneous network device logs",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    return {
        "message": "Universal Log Pre-processing Framework API is running"
    }


@app.get("/health")
def health_check():

    try:

        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))

            required_columns = {
                row[0]
                for row in connection.execute(text(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'normalized_events'
                    """
                ))
            }

            expected_columns = {
                "raw_event_id",
                "upload_id",
                "event_hash",
                "parsed_log",
                "normalized_log",
                "universal_event",
                "parser_used",
                "parser_version",
                "normalization_version",
                "source_format",
                "parser_confidence",
                "fallback_used",
                "parser_metadata",
                "quality_metrics",
                "processing_history",
                "processing_time",
                "processing_timestamp"
            }

            missing_columns = sorted(
                expected_columns - required_columns
            )

            if missing_columns:
                return {
                    "status": "unhealthy",
                    "database": "connected",
                    "schema": "outdated",
                    "missing_columns": missing_columns
                }

        return {
            "status": "healthy",
            "database": "connected",
            "schema": "ready"
        }

    except Exception:

        return {
            "status": "unhealthy",
            "database": "disconnected"
        }


# Register API router
app.include_router(upload_router)
app.include_router(events_router)
app.include_router(analytics_router)
app.include_router(parser_lab_router)
app.include_router(logs_router)
app.include_router(export_router)