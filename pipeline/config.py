"""Settings: read environment variables into a frozen Settings dataclass.

To write (plan section 6, config.py):
- load_dotenv() at import time (no-op in Actions, reads .env locally)
- Settings(database_url, source_url, source_type="api", page_size=500)
- get_settings(): required vars via os.environ[...] so a missing one fails loudly
"""
