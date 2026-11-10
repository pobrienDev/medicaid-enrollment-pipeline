"""Validate: data-quality gate that runs before anything is written. No I/O.

To write (plan section 6, validate.py):
- ValidationError(Exception)
- validate(df): collect every problem, then raise once with all of them:
  no rows, unparseable dates, state codes that are not two capital letters,
  negative values in any count column
"""
