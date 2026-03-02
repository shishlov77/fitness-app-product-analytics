"""
ETL pipeline: CSV files → PostgreSQL

Usage:
    python etl/etl.py

Env variable (optional):
    DATABASE_URL=postgresql://user:password@host:5432/dbname
"""

import os
import sys
import pandas as pd
from sqlalchemy import create_engine, text
from datetime import datetime

DB_URL = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@localhost:5432/fitness_analytics'
)

DDL = """
CREATE TABLE IF NOT EXISTS installs (
    user_id           INTEGER      PRIMARY KEY,
    install_date      DATE         NOT NULL,
    install_timestamp TIMESTAMP    NOT NULL,
    platform          VARCHAR(10)  NOT NULL,
    country           VARCHAR(5)   NOT NULL,
    channel           VARCHAR(20)  NOT NULL,
    app_version       VARCHAR(10)  NOT NULL,
    is_bot            SMALLINT     NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS onboarding (
    user_id           INTEGER      PRIMARY KEY,
    started_at        TIMESTAMP    NOT NULL,
    completed_at      TIMESTAMP,
    completed         SMALLINT     NOT NULL DEFAULT 0,
    steps_completed   SMALLINT     NOT NULL,
    goal              VARCHAR(30)  NOT NULL,
    FOREIGN KEY (user_id) REFERENCES installs(user_id)
);

CREATE TABLE IF NOT EXISTS events (
    event_id          BIGINT       PRIMARY KEY,
    user_id           INTEGER      NOT NULL,
    event_timestamp   TIMESTAMP    NOT NULL,
    event_type        VARCHAR(30)  NOT NULL,
    platform          VARCHAR(10)  NOT NULL,
    workout_type      VARCHAR(20),
    session_id        BIGINT,
    FOREIGN KEY (user_id) REFERENCES installs(user_id)
);

CREATE INDEX IF NOT EXISTS idx_events_user       ON events(user_id);
CREATE INDEX IF NOT EXISTS idx_events_type_ts    ON events(event_type, event_timestamp);
CREATE INDEX IF NOT EXISTS idx_events_ts         ON events(event_timestamp);
CREATE INDEX IF NOT EXISTS idx_installs_date     ON installs(install_date);
CREATE INDEX IF NOT EXISTS idx_installs_platform ON installs(platform);
CREATE INDEX IF NOT EXISTS idx_installs_channel  ON installs(channel);
"""


def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")


def create_schema(engine):
    with engine.begin() as conn:
        for stmt in DDL.strip().split(';'):
            stmt = stmt.strip()
            if stmt:
                conn.execute(text(stmt + ';'))
    log("Schema created / verified")


def load_table(engine, path, table, parse_dates=None):
    log(f"Loading {path} → {table}...")
    df = pd.read_csv(path, parse_dates=parse_dates)
    df.to_sql(table, engine, if_exists='replace', index=False,
              method='multi', chunksize=5_000)
    count = pd.read_sql(f"SELECT COUNT(*) AS n FROM {table}", engine).iloc[0]['n']
    log(f"  {table}: {count:,} rows")
    return count


def validate(engine):
    log("Validation summary:")
    result = pd.read_sql(text("""
        SELECT
            (SELECT COUNT(*)               FROM installs)  AS installs,
            (SELECT COUNT(*)               FROM onboarding) AS onboarding,
            (SELECT COUNT(*)               FROM events)    AS events,
            (SELECT COUNT(DISTINCT event_type) FROM events) AS event_types,
            (SELECT COUNT(DISTINCT user_id)    FROM installs WHERE is_bot = 0) AS real_users
    """), engine)
    print(result.to_string(index=False))


if __name__ == '__main__':
    data_dir = os.path.join(os.path.dirname(__file__), '..', 'data')

    log("Starting ETL pipeline")
    engine = create_engine(DB_URL)

    create_schema(engine)

    load_table(engine,
               os.path.join(data_dir, 'installs.csv'),
               'installs',
               parse_dates=['install_date', 'install_timestamp'])

    load_table(engine,
               os.path.join(data_dir, 'onboarding.csv'),
               'onboarding',
               parse_dates=['started_at', 'completed_at'])

    load_table(engine,
               os.path.join(data_dir, 'events.csv'),
               'events',
               parse_dates=['event_timestamp'])

    validate(engine)
    log("ETL pipeline complete")
