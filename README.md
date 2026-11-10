# Enrollment Data Pipeline

A small, tested data pipeline that pulls public Medicaid & CHIP enrollment data, cleans and validates it with pandas, and upserts it into PostgreSQL on a schedule with GitHub Actions.

[![CI](https://github.com/pobrienDev/medicaid-enrollment-pipeline/actions/workflows/ci.yml/badge.svg)](https://github.com/pobrienDev/medicaid-enrollment-pipeline/actions/workflows/ci.yml)

## Architecture

```mermaid
flowchart LR
    GA["GitHub Actions<br/>cron + manual run"] --> RUN["python -m pipeline.run"]
    SRC["Medicaid API<br/>(CSV fallback)"] --> E["Extract<br/>paginate, retry,<br/>save raw copy"]
    RUN --> E
    E --> T["Transform<br/>clean names, types,<br/>dedupe"]
    T --> V["Validate<br/>schema + rule checks,<br/>fail fast"]
    V --> L["Load<br/>staging → upsert<br/>in one transaction"]
    L --> PG[("PostgreSQL<br/>enrollment · pipeline_runs")]
```

## Quick start

```bash
docker compose up -d                 # local Postgres 16; applies sql/schema.sql on first start
cp .env.example .env                 # defaults point at local Postgres and the CMS API
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pipeline.run
```

## Tests

```bash
pip install -r requirements-dev.txt
ruff check .
pytest --cov=pipeline --cov-report=term-missing
```

Unit tests (`test_extract.py`, `test_transform.py`, `test_validate.py`) need nothing external: HTTP is mocked and the data is a fixture of 20 real source rows.

The integration tests (`test_load.py`, `test_run.py`) run against a real Postgres. They empty the tables they use, so they connect with `TEST_DATABASE_URL` (falling back to `DATABASE_URL`, which is what CI sets) and refuse to run against any database whose name does not end in `_test`. Docker Compose creates `enrollment_test` alongside the main database. Without a test database they are skipped.

## Design decisions

- **Idempotent upsert.** `INSERT ... ON CONFLICT (state_code, report_month) DO UPDATE`, so rerunning a load never duplicates data.
- **Validation gate.** Bad data fails the run before anything touches the main table. Postgres constraints are a second line of defense.
- **Single transaction.** The staging write and the upsert share one transaction, so a crash never leaves half a load.
- **Run audit table.** Every run writes a row to `pipeline_runs` (start, end, status, row counts, error).
- **Raw snapshot.** Each extract is saved untouched under `data/` (gitignored) before it is transformed.

## Sample queries

```sql
-- Latest month, top 5 states by total enrollment
SELECT state_code, total_enrollment
FROM enrollment
WHERE report_month = (SELECT max(report_month) FROM enrollment)
ORDER BY total_enrollment DESC
LIMIT 5;

-- Did the scheduled job work?
SELECT started_at, status, rows_loaded, error
FROM pipeline_runs ORDER BY run_id DESC LIMIT 5;
```

## Data source

[State Medicaid and CHIP Applications, Eligibility Determinations, and Enrollment Data](https://data.medicaid.gov/dataset/6165f45b-ca93-5bb5-9d06-db29c692a360), published by the Centers for Medicare & Medicaid Services on data.medicaid.gov.

- **Coverage:** 50 states plus DC, monthly from September 2013, updated monthly with roughly a three-month lag.
- **Access:** public JSON API with `limit`/`offset` paging, no API key. The same data is available as a CSV download, which the pipeline uses as a fallback.
- **License:** U.S. government work ([usa.gov/government-works](https://www.usa.gov/government-works)).
- **Preliminary vs. updated:** most state-months appear twice, once as a preliminary report and once as an updated final report, often with different totals. The pipeline keeps one row per state and month, preferring the updated report, so a full run extracts about 11,200 rows and loads about 5,700.

## Roadmap

- [ ] Second dataset + join (e.g., population for per-capita rates)
- [ ] Incremental loads (only new months)
- [ ] pandera schema; data-freshness check
- [ ] Postgres `COPY` for speed; SQL views for reporting
- [ ] Failure alert to a Teams/Slack webhook; Dockerfile
- [ ] Small chart or dashboard from the loaded table
