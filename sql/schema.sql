CREATE TABLE IF NOT EXISTS enrollment (
    state_code          CHAR(2)     NOT NULL,
    report_month        DATE        NOT NULL,
    total_enrollment    INTEGER     CHECK (total_enrollment >= 0),
    medicaid_enrollment INTEGER     CHECK (medicaid_enrollment >= 0),
    chip_enrollment     INTEGER     CHECK (chip_enrollment >= 0),
    loaded_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (state_code, report_month)   -- natural key = upsert target
);

CREATE TABLE IF NOT EXISTS pipeline_runs (
    run_id         BIGSERIAL PRIMARY KEY,
    started_at     TIMESTAMPTZ NOT NULL,
    finished_at    TIMESTAMPTZ,
    status         TEXT NOT NULL CHECK (status IN ('running', 'success', 'failed')),
    rows_extracted INTEGER,
    rows_loaded    INTEGER,
    error          TEXT
);

CREATE INDEX IF NOT EXISTS idx_enrollment_month ON enrollment (report_month);
