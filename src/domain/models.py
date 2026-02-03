from __future__ import annotations

from dataclasses import dataclass, field
from typing import List


@dataclass
class LevelEntry:
    level: int
    code: str = ""
    name: str = ""


@dataclass
class LabelDocument:
    title: str = "Cabinet Inventory Label"
    cabinet_section: str = ""
    level1: LevelEntry = field(default_factory=lambda: LevelEntry(level=1))
    level2_list: List[LevelEntry] = field(default_factory=list)

