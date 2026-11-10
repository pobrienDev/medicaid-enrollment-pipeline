"""Extract: pull raw rows from the source. Does I/O."""

import io
import logging
from datetime import UTC, datetime
from pathlib import Path

import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

TIMEOUT_SECONDS = 30


def make_session() -> requests.Session:
    """A session that retries with exponential backoff on throttling and 5xx."""
    retry = Retry(
        total=3,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
    )
    session = requests.Session()
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def fetch_api(url: str, page_size: int = 500, session=None) -> pd.DataFrame:
    """Page through the API with limit/offset until a short page comes back."""
    session = session or make_session()
    rows, offset = [], 0
    while True:
        resp = session.get(
            url, params={"limit": page_size, "offset": offset}, timeout=TIMEOUT_SECONDS
        )
        resp.raise_for_status()
        batch = resp.json()["results"]
        rows.extend(batch)
        log.info("fetched %d rows (offset=%d)", len(batch), offset)
        if len(batch) < page_size:
            break
        offset += page_size
    return pd.DataFrame(rows)


def fetch_csv(path_or_url: str, session=None) -> pd.DataFrame:
    """CSV fallback. URLs go through the retrying session; local paths are read directly."""
    if path_or_url.lower().startswith(("http://", "https://")):
        session = session or make_session()
        resp = session.get(path_or_url, timeout=TIMEOUT_SECONDS)
        resp.raise_for_status()
        return pd.read_csv(io.BytesIO(resp.content))
    return pd.read_csv(path_or_url)


def save_raw(df: pd.DataFrame, directory: str | Path = "data") -> Path:
    """Save an untouched copy of what was extracted, for debugging and replay."""
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"enrollment_raw_{stamp}.csv"
    df.to_csv(path, index=False)
    log.info("saved raw copy: %s (%d rows)", path, len(df))
    return path
