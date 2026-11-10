"""Shared fixtures."""

import os
import pathlib

import pandas as pd
import pytest
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from pipeline.transform import transform

ROOT = pathlib.Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "tests" / "fixtures" / "sample_enrollment.csv"
SCHEMA = ROOT / "sql" / "schema.sql"

load_dotenv(ROOT / ".env")  # picks up TEST_DATABASE_URL locally; no-op in CI


@pytest.fixture
def fixture_path() -> pathlib.Path:
    return FIXTURE


@pytest.fixture
def raw_df() -> pd.DataFrame:
    """20 real rows from the source CSV, untouched."""
    return pd.read_csv(FIXTURE)


@pytest.fixture
def clean_df(raw_df) -> pd.DataFrame:
    return transform(raw_df)


@pytest.fixture
def engine():
    """A real Postgres with the schema applied and the tables emptied.

    Uses TEST_DATABASE_URL, falling back to DATABASE_URL (which is what CI
    sets). Because this fixture truncates tables, it only runs against a
    database whose name ends in _test.
    """
    url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not url:
        pytest.skip("TEST_DATABASE_URL / DATABASE_URL not set: skipping integration test")
    name = make_url(url).database or ""
    if not name.endswith("_test"):
        pytest.skip(f"refusing to truncate {name!r}: integration tests need a *_test database")

    eng = create_engine(url)
    with eng.begin() as conn:
        conn.exec_driver_sql(SCHEMA.read_text())
        conn.execute(text("TRUNCATE enrollment, pipeline_runs RESTART IDENTITY"))
        conn.execute(text("DROP TABLE IF EXISTS staging_enrollment"))
    yield eng
    eng.dispose()
