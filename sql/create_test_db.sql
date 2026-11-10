-- Local only: a second database for the integration tests, so they never
-- truncate the data loaded by real pipeline runs. Docker Compose runs this
-- the first time the database volume is created.
CREATE DATABASE enrollment_test;
