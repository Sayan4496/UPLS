import os
import requests
from sqlalchemy import create_engine, text

path = r"C:\Users\Sayan\Downloads\SIH-26156\UPLS\universal-log-framework\sample_logs\csv\test.csv"
for i in range(2):
    with open(path, 'rb') as f:
        resp = requests.post('http://localhost:8000/upload/', files={'file': (os.path.basename(path), f, 'text/csv')}, timeout=60)
        print('upload', i + 1, resp.status_code, resp.json()['processing_result'])

engine = create_engine('postgresql+psycopg2://postgres:postgres@localhost:5433/ulpf_database')
with engine.connect() as conn:
    raw_rows = conn.execute(text("SELECT id, event_hash, duplicate_of, is_duplicate FROM raw_events ORDER BY created_at DESC LIMIT 10")).fetchall()
    norm_rows = conn.execute(text("SELECT id, event_hash, duplicate_of, is_duplicate FROM normalized_events ORDER BY processing_timestamp DESC LIMIT 10")).fetchall()
    print('RAW_ROWS', raw_rows)
    print('NORM_ROWS', norm_rows)
    print('RAW_DUPLICATES', conn.execute(text("SELECT COUNT(*) FROM raw_events WHERE is_duplicate = TRUE")).scalar())
    print('NORM_DUPLICATES', conn.execute(text("SELECT COUNT(*) FROM normalized_events WHERE is_duplicate = TRUE")).scalar())
