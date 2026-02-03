from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class RulesProfile:
    profile_id: str
    profile_name: str
    level_count: int
    level_labels: Dict[int, str]
    code_delimiter: str = "."          # NEW (default ".")
    code_regex: str = ""               # optional validation
    notes: str = ""


@dataclass(frozen=True)
class MappingRow:
    profile_id: str
    level: int
    code: str
    name: str
    locked: bool = True


@dataclass(frozen=True)
class DefaultChildRow:
    profile_id: str
    parent_level: int
    parent_code: str
    child_level: int
    child_code: str
    child_name: str


@dataclass
class RulesWorkbook:
    profiles: Dict[str, RulesProfile] = field(default_factory=dict)
    # key: (profile_id, level, code_lower) -> MappingRow
    mappings: Dict[Tuple[str, int, str], MappingRow] = field(default_factory=dict)
    # key: (profile_id, parent_level, parent_code_lower, child_level) -> list[DefaultChildRow]
    default_children: Dict[Tuple[str, int, str, int], List[DefaultChildRow]] = field(default_factory=dict)
    settings: Dict[str, str] = field(default_factory=dict)

    def get_profile(self, profile_id: str) -> Optional[RulesProfile]:
        return self.profiles.get(profile_id)

