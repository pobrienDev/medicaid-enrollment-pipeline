"""Unit tests for transform.

To prove:
- column mapping
- date parsing
- commas in numbers are handled
- duplicates on (state_code, report_month) are dropped
- state codes are uppercased
- when a state-month has a preliminary and an updated row, the updated one wins
- reporting_period parses whether it arrives as a string (API) or an int (CSV)

The fixture has cases for these: AK 201309 (updated only, null Medicaid/CHIP
counts), P/U pairs with different totals, and 202607 rows (preliminary only).
"""
