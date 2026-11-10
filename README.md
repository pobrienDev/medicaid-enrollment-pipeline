# Enrollment Data Pipeline

A small, tested data pipeline that pulls public Medicaid & CHIP enrollment data, cleans and validates it with pandas, and upserts it into PostgreSQL on a schedule with GitHub Actions.

<!-- TODO: add the CI badge once the repo is on GitHub:
![CI](https://github.com/OWNER/REPO/actions/workflows/ci.yml/badge.svg)
-->

> Status: scaffold. The modules in `pipeline/` and the tests are stubs that describe what each file will contain.

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
cp .env.example .env                 # then set SOURCE_URL
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

Unit tests need nothing external. The integration tests in `tests/test_load.py` need a running Postgres and `DATABASE_URL` set; without it they are skipped.

## Design decisions

- **Idempotent upsert.** `INSERT ... ON CONFLICT (state_code, report_month) DO UPDATE`, so rerunning a load never duplicates data.
- **Validation gate.** Bad data fails the run before anything touches the main table. Postgres constraints are a second line of defense.
- **Single transaction.** The staging write and the upsert share one transaction, so a crash never leaves half a load.
- **Run audit table.** Every run writes a row to `pipeline_runs` (start, end, status, row counts, error).

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

<!-- TODO: dataset name, link to the dataset page, and license note -->

## Roadmap

- [ ] Second dataset + join (e.g., population for per-capita rates)
- [ ] Incremental loads (only new months)
- [ ] pandera schema; data-freshness check
- [ ] Postgres `COPY` for speed; SQL views for reporting
- [ ] Failure alert to a Teams/Slack webhook; Dockerfile
- [ ] Small chart or dashboard from the loaded table
