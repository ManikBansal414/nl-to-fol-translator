from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


@lru_cache(maxsize=1)
def load_env_files() -> None:
    """Load .env and .env.local files from the project root once."""
    root = Path(__file__).resolve().parents[2]
    for name in (".env", ".env.local"):
        path = root / name
        if path.exists():
            load_dotenv(path, override=False)
