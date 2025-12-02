from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Optional


class ResponseCache:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or Path(".cache/llm")
        self.root.mkdir(parents=True, exist_ok=True)

    def _key_path(self, key: str) -> Path:
        return self.root / f"{key}.json"

    def make_key(self, payload: Dict[str, Any]) -> str:
        normalized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def get(self, payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        key = self.make_key(payload)
        path = self._key_path(key)
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def set(self, payload: Dict[str, Any], response: Dict[str, Any]) -> None:
        key = self.make_key(payload)
        path = self._key_path(key)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(response, handle, ensure_ascii=False, indent=2)
