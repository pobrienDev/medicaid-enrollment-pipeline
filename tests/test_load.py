"""Integration tests for load, against a real Postgres (needs DATABASE_URL).

To prove:
- rows land in enrollment
- running the load twice gives the same row count (idempotency)
- updated values overwrite the old ones
"""
