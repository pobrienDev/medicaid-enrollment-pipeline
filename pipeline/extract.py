"""Extract: pull raw rows from the source. Does I/O.

To write (plan section 6, extract.py):
- make_session(): requests.Session with urllib3 Retry (backoff on 429/5xx, GET only)
- fetch_api(url, page_size, session=None): limit/offset paging with a timeout,
  raise_for_status, stop on a short page, return a DataFrame
- fetch_csv(path_or_url): CSV fallback
- save a raw copy of what was fetched under data/ (gitignored)
"""
