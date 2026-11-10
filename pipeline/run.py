"""Orchestrator and CLI entry point:  python -m pipeline.run"""

import logging
import sys

import pandas as pd
from sqlalchemy import create_engine, text

from pipeline import config, extract, load, transform, validate
from pipeline.logging_setup import setup_logging

log = logging.getLogger("pipeline")

START_RUN = text(
    "INSERT INTO pipeline_runs (started_at, status) VALUES (now(), 'running') RETURNING run_id"
)
FINISH_RUN = text(
    "UPDATE pipeline_runs SET finished_at = now(), status = :status, "
    "rows_extracted = :extracted, rows_loaded = :loaded, error = :error "
    "WHERE run_id = :run_id"
)


def fetch(settings: config.Settings) -> pd.DataFrame:
    if settings.source_type == "api":
        return extract.fetch_api(settings.source_url, settings.page_size)
    if settings.source_type == "csv":
        return extract.fetch_csv(settings.source_url)
    raise ValueError(f"unknown SOURCE_TYPE {settings.source_type!r}; expected 'api' or 'csv'")


def main() -> int:
    setup_logging()
    settings = config.get_settings()
    engine = create_engine(settings.database_url)

    with engine.begin() as conn:
        run_id = conn.execute(START_RUN).scalar_one()
    log.info("run %d started (source_type=%s)", run_id, settings.source_type)

    rows_extracted, rows_loaded = 0, 0
    try:
        raw = fetch(settings)
        rows_extracted = len(raw)
        extract.save_raw(raw, settings.raw_dir)
        df = transform.transform(raw)
        validate.validate(df)
        rows_loaded = load.load(df, engine)
        status, error = "success", None
        log.info("extracted %d rows, loaded %d", rows_extracted, rows_loaded)
    except Exception as exc:
        status, error = "failed", f"{type(exc).__name__}: {exc}"[:1000]
        log.exception("pipeline failed")

    # Record the outcome either way, then let the exit code fail the job.
    with engine.begin() as conn:
        conn.execute(
            FINISH_RUN,
            {
                "status": status,
                "extracted": rows_extracted,
                "loaded": rows_loaded,
                "error": error,
                "run_id": run_id,
            },
        )
    engine.dispose()
    return 0 if status == "success" else 1  # non-zero exit = red X in Actions


if __name__ == "__main__":
    sys.exit(main())
