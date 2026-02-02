from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Tuple

from openpyxl import load_workbook

from src.services.rules.rules_types import (
    RulesWorkbook, RulesProfile, MappingRow, DefaultChildRow
)


def _norm(s: Any) -> str:
    if s is None:
        return ""
    return " ".join(str(s).strip().split())


def _to_int(x: Any, default: int = 0) -> int:
    try:
        return int(str(x).strip())
    except Exception:
        return default


def _read_table(ws) -> Tuple[List[str], List[List[Any]]]:
    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return [], []
    headers = [(_norm(c)).lower() for c in (rows[0] or [])]
    data = [list(r) for r in rows[1:] if any((_norm(v) for v in (r or [])))]
    return headers, data


def _idx_map(headers: List[str]) -> Dict[str, int]:
    return {h: i for i, h in enumerate(headers) if h}


def _get(row: List[Any], idx: Dict[str, int], name: str) -> Any:
    j = idx.get(name.lower())
    if j is None or j >= len(row):
        return None
    return row[j]


def _parse_profiles_format(wb) -> RulesWorkbook:
    out = RulesWorkbook()

    # ---- Profiles ----
    if "Profiles" not in wb.sheetnames:
        raise ValueError("rules.xlsx is missing required sheet: Profiles")

    ws = wb["Profiles"]
    headers, data = _read_table(ws)
    idx = _idx_map(headers)

    for r in data:
        pid = _norm(_get(r, idx, "profile_id"))
        if not pid:
            continue

        pname = _norm(_get(r, idx, "profile_name")) or pid
        level_count = _to_int(_get(r, idx, "level_count"), 2)

        level_labels: Dict[int, str] = {}
        for lv in range(1, 7):
            lab = _norm(_get(r, idx, f"level{lv}_label"))
            if lv <= level_count:
                level_labels[lv] = lab or f"Level {lv}"

        delim = _norm(_get(r, idx, "code_delimiter")) or "."
        if len(delim) != 1:
            delim = "."

        prof = RulesProfile(
            profile_id=pid,
            profile_name=pname,
            level_count=level_count,
            level_labels=level_labels,
            code_delimiter=delim,
            code_regex=_norm(_get(r, idx, "code_regex")),
            notes=_norm(_get(r, idx, "notes")),
        )
        out.profiles[pid] = prof

    # ---- LevelMappings ----
    if "LevelMappings" in wb.sheetnames:
        ws = wb["LevelMappings"]
        headers, data = _read_table(ws)
        idx = _idx_map(headers)

        for r in data:
            pid = _norm(_get(r, idx, "profile_id"))
            if not pid:
                continue
            level = _to_int(_get(r, idx, "level"), 0)
            code = _norm(_get(r, idx, "code"))
            name = _norm(_get(r, idx, "name"))
            locked = str(_norm(_get(r, idx, "locked") or "TRUE")).strip().lower() not in ("0", "false", "no")

            if level <= 0 or not code:
                continue

            mr = MappingRow(profile_id=pid, level=level, code=code, name=name, locked=locked)
            out.mappings[(pid, level, code.strip().lower())] = mr

    # ---- DefaultChildren ----
    if "DefaultChildren" in wb.sheetnames:
        ws = wb["DefaultChildren"]
        headers, data = _read_table(ws)
        idx = _idx_map(headers)

        for r in data:
            pid = _norm(_get(r, idx, "profile_id"))
            if not pid:
                continue
            parent_level = _to_int(_get(r, idx, "parent_level"), 0)
            child_level = _to_int(_get(r, idx, "child_level"), 0)
            parent_code = _norm(_get(r, idx, "parent_code"))
            child_code = _norm(_get(r, idx, "child_code"))
            child_name = _norm(_get(r, idx, "child_name"))
            if not (parent_level and child_level and parent_code and child_code):
                continue

            dc = DefaultChildRow(
                profile_id=pid,
                parent_level=parent_level,
                parent_code=parent_code,
                child_level=child_level,
                child_code=child_code,
                child_name=child_name,
            )
            key = (pid, parent_level, parent_code.strip().lower(), child_level)
            out.default_children.setdefault(key, []).append(dc)

    # ---- Settings ----
    if "Settings" in wb.sheetnames:
        ws = wb["Settings"]
        headers, data = _read_table(ws)
        idx = _idx_map(headers)
        for r in data:
            k = _norm(_get(r, idx, "key"))
            v = _norm(_get(r, idx, "value"))
            if k:
                out.settings[k] = v

    return out


def _parse_simple_authority_format(wb) -> RulesWorkbook:
    """
    Supports the 'human' workbook:
      - Profile sheet: Field | Value
      - Level 1 sheet: Code | Name
      - Level 2 sheet: Parent code | Code (suffix) | Name
      - Optional Level 3/4: same parent+suffix structure
    """
    out = RulesWorkbook()

    if "Profile" not in wb.sheetnames or "Level 1" not in wb.sheetnames:
        raise ValueError("Simple authority workbook must contain sheets: Profile and Level 1")

    # ---- Profile ----
    ws = wb["Profile"]
    headers, data = _read_table(ws)

    # Expect simple key/value in first two columns, tolerate header row
    kv: Dict[str, str] = {}
    for r in data:
        k = _norm(r[0] if len(r) > 0 else "")
        v = _norm(r[1] if len(r) > 1 else "")
        if k:
            kv[k.lower()] = v

    institution = kv.get("institution", "")
    discipline = kv.get("discipline", "")
    delim = kv.get("code delimiter", ".") or "."
    if len(delim) != 1:
        delim = "."

    level_count = _to_int(kv.get("number of levels", 2), 2)
    level_count = max(2, min(level_count, 6))

    pad_l1 = _to_int(kv.get("pad level 1 codes to", 2), 2)
    pad_l1 = max(1, min(pad_l1, 6))

    level_labels: Dict[int, str] = {}
    for lv in range(1, level_count + 1):
        nm = kv.get(f"level {lv} name", "") or kv.get(f"level {lv} label", "")
        level_labels[lv] = nm or f"Level {lv}"

    # One default profile
    pid = "default"
    pname = (discipline or "Authority Profile").strip() or "Authority Profile"
    out.profiles[pid] = RulesProfile(
        profile_id=pid,
        profile_name=pname,
        level_count=level_count,
        level_labels=level_labels,
        code_delimiter=delim,
        code_regex="",
        notes="",
    )

    # Store institution/discipline as settings so UI can show them
    if institution:
        out.settings["institution"] = institution
    if discipline:
        out.settings["discipline"] = discipline
    out.settings["pad_level1"] = str(pad_l1)

    # Helper: normalize L1 codes (padding)
    def norm_l1(code: str) -> str:
        c = (code or "").strip()
        if c.isdigit():
            return str(int(c)).zfill(pad_l1)
        return c

    # ---- Level 1 mappings ----
    ws = wb["Level 1"]
    headers, data = _read_table(ws)
    idx = _idx_map(headers)

    # Fallback if headers missing: assume first 2 columns
    code_key = "code" if "code" in idx else headers[0] if headers else "code"
    name_key = "name" if "name" in idx else headers[1] if len(headers) > 1 else "name"

    for r in data:
        code = _norm(_get(r, idx, code_key) if idx else (r[0] if len(r) > 0 else ""))
        name = _norm(_get(r, idx, name_key) if idx else (r[1] if len(r) > 1 else ""))
        if not code:
            continue
        code = norm_l1(code)
        mr = MappingRow(profile_id=pid, level=1, code=code, name=name, locked=True)
        out.mappings[(pid, 1, code.lower())] = mr

    # ---- Level 2..N mappings ----
    for lv in range(2, level_count + 1):
        sheet = f"Level {lv}"
        if sheet not in wb.sheetnames:
            continue

        ws = wb[sheet]
        headers, data = _read_table(ws)
        idx = _idx_map(headers)

        # Expected columns
        # parent code | code (suffix) | name
        for r in data:
            parent = _norm(_get(r, idx, "parent code") if idx else (r[0] if len(r) > 0 else ""))
            suffix = _norm(_get(r, idx, "code (suffix)") if idx and "code (suffix)" in idx else (_get(r, idx, "code") if idx else (r[1] if len(r) > 1 else "")))
            name = _norm(_get(r, idx, "name") if idx else (r[2] if len(r) > 2 else ""))

            if not parent or not suffix:
                continue

            # Parent for level 2 is L1, so normalize padding
            if lv == 2:
                parent = norm_l1(parent)

            # Build full code: parent + delimiter + suffix (unless suffix already contains delimiter)
            full = suffix if (delim in suffix) else f"{parent}{delim}{str(int(suffix)) if suffix.isdigit() else suffix}"

            mr = MappingRow(profile_id=pid, level=lv, code=full, name=name, locked=True)
            out.mappings[(pid, lv, full.lower())] = mr

    return out


def load_rules_xlsx(path: str | Path) -> RulesWorkbook:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Rules file not found: {path}")

    wb = load_workbook(path, data_only=True)

    # If it looks like the old rules.xlsx format, parse that.
    if "Profiles" in wb.sheetnames:
        return _parse_profiles_format(wb)

    # Otherwise try the simple authority workbook format.
    return _parse_simple_authority_format(wb)
