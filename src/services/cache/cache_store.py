from __future__ import annotations

import json
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List


APP_FOLDER = "CatalogLabel"
LEGACY_APP_FOLDER = "LabelApp"
CACHE_FILENAME = "cache.json"


def _appdata_dir() -> Path:
    # Prefer Windows APPDATA; fall back to current directory if missing (portable/dev).
    return Path(os.environ.get("APPDATA", "."))


def legacy_cache_path() -> Path:
    base = _appdata_dir() / LEGACY_APP_FOLDER
    return base / CACHE_FILENAME


def default_cache_path() -> Path:
    base = _appdata_dir() / APP_FOLDER
    base.mkdir(parents=True, exist_ok=True)
    return base / CACHE_FILENAME


def _migrate_legacy_cache_if_needed(new_path: Path) -> None:
    """
    One-time migration:
      - If new cache does not exist but old does, copy it.
      - Never overwrites an existing new cache.
    """
    try:
        old_path = legacy_cache_path()
        if new_path.exists():
            return
        if not old_path.exists():
            return

        new_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(old_path, new_path)
    except Exception:
        # Migration should never break startup.
        return


@dataclass
class CacheDB:
    # keys are field identifiers, values are a list of recent strings
    values: Dict[str, List[str]] = field(default_factory=dict)


def load_cache(path: Path | None = None) -> CacheDB:
    path = path or default_cache_path()
    _migrate_legacy_cache_if_needed(path)

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
    _migrate_legacy_cache_if_needed(path)

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

