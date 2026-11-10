"""Settings: read environment variables into a frozen Settings dataclass."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()  # no-op in Actions; reads .env locally


@dataclass(frozen=True)
class Settings:
    database_url: str
    source_url: str  # API endpoint, or path/URL to a CSV
    source_type: str = "api"  # "api" | "csv"
    page_size: int = 500
    raw_dir: str = "data"  # where the raw snapshot of each extract is saved


def _required(name: str) -> str:
    """Fail loudly if a variable is missing or blank.

    Blank matters as much as missing: an unset GitHub Actions secret or
    variable arrives as an empty string, not as an absent one.
    """
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"required environment variable {name} is not set")
    return value


def get_settings() -> Settings:
    return Settings(
        database_url=_required("DATABASE_URL"),
        source_url=_required("SOURCE_URL"),
        source_type=os.getenv("SOURCE_TYPE", "api").strip().lower(),
        page_size=int(os.getenv("PAGE_SIZE", "500")),
        raw_dir=os.getenv("RAW_DIR", "data"),
    )
