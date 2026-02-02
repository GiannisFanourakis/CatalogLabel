from __future__ import annotations

from typing import List, Optional, Tuple

from src.services.rules.rules_types import RulesWorkbook, MappingRow, DefaultChildRow


def lookup_mapping(rules: RulesWorkbook, profile_id: str, level: int, code: str) -> Optional[MappingRow]:
    if not rules or not profile_id:
        return None
    key = (profile_id, level, (code or "").strip().lower())
    return rules.mappings.get(key)


def default_children_for(
    rules: RulesWorkbook,
    profile_id: str,
    parent_level: int,
    parent_code: str,
    child_level: int,
) -> List[DefaultChildRow]:
    if not rules or not profile_id:
        return []
    key = (profile_id, parent_level, (parent_code or "").strip().lower(), child_level)
    return list(rules.default_children.get(key, []))
