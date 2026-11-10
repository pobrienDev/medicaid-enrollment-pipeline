"""Integration tests for the orchestrator: the whole pipeline, end to end.

These run main() against the fixture CSV and a real Postgres. No network.
"""

import pandas as pd
import pytest
from sqlalchemy import text

from pipeline.run import main


@pytest.fixture
def run_env(engine, monkeypatch, tmp_path, fixture_path):
    """Point the pipeline at the test database and the fixture CSV."""
    monkeypatch.setenv("DATABASE_URL", engine.url.render_as_string(hide_password=False))
    monkeypatch.setenv("SOURCE_URL", str(fixture_path))
    monkeypatch.setenv("SOURCE_TYPE", "csv")
    monkeypatch.setenv("RAW_DIR", str(tmp_path / "raw"))
    return engine


def last_run(engine):
    with engine.connect() as conn:
        return conn.execute(
            text(
                "SELECT status, rows_extracted, rows_loaded, error, finished_at "
                "FROM pipeline_runs ORDER BY run_id DESC LIMIT 1"
            )
        ).one()


def enrollment_count(engine) -> int:
    with engine.connect() as conn:
        return conn.execute(text("SELECT count(*) FROM enrollment")).scalar()


def test_successful_run_loads_data_and_records_it(run_env, tmp_path):
    assert main() == 0

    run = last_run(run_env)
    assert run.status == "success"
    assert run.rows_extracted == 20
    assert run.rows_loaded == 13
    assert run.error is None
    assert run.finished_at is not None
    assert enrollment_count(run_env) == 13
    assert len(list((tmp_path / "raw").glob("enrollment_raw_*.csv"))) == 1


def test_running_twice_does_not_duplicate(run_env):
    assert main() == 0
    assert main() == 0

    assert enrollment_count(run_env) == 13
    with run_env.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM pipeline_runs")).scalar() == 2


def test_failed_extract_is_recorded_and_exits_non_zero(run_env, monkeypatch, tmp_path):
    monkeypatch.setenv("SOURCE_URL", str(tmp_path / "does_not_exist.csv"))

    assert main() == 1

    run = last_run(run_env)
    assert run.status == "failed"
    assert "FileNotFoundError" in run.error
    assert run.finished_at is not None
    assert enrollment_count(run_env) == 0


def test_validation_failure_writes_nothing(run_env, monkeypatch, tmp_path, fixture_path):
    bad = pd.read_csv(fixture_path)
    bad.loc[0, "State Abbreviation"] = "Alaska"
    bad_path = tmp_path / "bad.csv"
    bad.to_csv(bad_path, index=False)
    monkeypatch.setenv("SOURCE_URL", str(bad_path))

    assert main() == 1

    run = last_run(run_env)
    assert run.status == "failed"
    assert "bad state codes" in run.error
    assert run.rows_extracted == 20
    assert run.rows_loaded == 0
    assert enrollment_count(run_env) == 0


def test_unknown_source_type_fails_cleanly(run_env, monkeypatch):
    monkeypatch.setenv("SOURCE_TYPE", "ftp")

    assert main() == 1
    assert "unknown SOURCE_TYPE" in last_run(run_env).error


def test_missing_required_setting_fails_before_touching_the_database(run_env, monkeypatch):
    monkeypatch.setenv("SOURCE_URL", "")

    with pytest.raises(RuntimeError, match="SOURCE_URL"):
        main()

    with run_env.connect() as conn:
        assert conn.execute(text("SELECT count(*) FROM pipeline_runs")).scalar() == 0
