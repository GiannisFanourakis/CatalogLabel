from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


def default_cache_path() -> Path:
    base = Path(os.environ.get("APPDATA", ".")) / "LabelApp"
    base.mkdir(parents=True, exist_ok=True)
    return base / "cache.json"


@dataclass
class CacheDB:
    # keys are field identifiers, values are a list of recent strings
    values: Dict[str, List[str]] = field(default_factory=dict)


def load_cache(path: Path | None = None) -> CacheDB:
    path = path or default_cache_path()
    if not path.exists():
        return CacheDB()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict) and isinstance(data.get("values"), dict):
            return CacheDB(values={k: list(v) for k, v in data["values"].items()})
    except Exception:
        pass
    return CacheDB()


def save_cache(db: CacheDB, path: Path | None = None) -> None:
    path = path or default_cache_path()
    payload = {"values": db.values}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def remember(db: CacheDB, field: str, text: str, limit: int = 50) -> None:
    t = " ".join((text or "").strip().split())
    if not t:
        return
    lst = db.values.setdefault(field, [])
    # de-dupe case-insensitively, keep newest
    lowered = [x.lower() for x in lst]
    if t.lower() in lowered:
        idx = lowered.index(t.lower())
        lst.pop(idx)
    lst.insert(0, t)
    del lst[limit:]


def suggest(db: CacheDB, field: str, prefix: str, limit: int = 12) -> List[str]:
    p = (prefix or "").strip().lower()
    items = db.values.get(field, [])
    if not p:
        return items[:limit]

    starts = [x for x in items if x.lower().startswith(p)]
    contains = [x for x in items if (p in x.lower()) and not x.lower().startswith(p)]
    out = starts + contains
    return out[:limit]
