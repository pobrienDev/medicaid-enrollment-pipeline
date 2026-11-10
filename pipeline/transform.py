"""Transform: pure function, raw DataFrame in, clean DataFrame out. No I/O.

To write (plan section 6, transform.py):
- COLUMN_MAP: source column name -> our name (fill in from the real dataset)
- COUNT_COLS: total_enrollment, medicaid_enrollment, chip_enrollment
- transform(raw): normalise headers, rename and select, strip/uppercase state_code,
  parse report_month, strip commas and cast counts to Int64,
  drop duplicates on (state_code, report_month)

Source quirks to handle (checked against the live dataset, Nov 2026):
- Most state-months have two rows: preliminary (preliminary_or_updated = "P",
  final_report = "N") then updated ("U", "Y"), often with different totals.
  keep="last" only picks the updated row because of source row order; choosing
  on final_report is explicit. The newest month has a preliminary row only.
- The API returns every value as a string or null; the CSV gives
  reporting_period as an integer. Counts have no commas in either.
"""
