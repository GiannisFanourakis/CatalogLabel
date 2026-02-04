from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass
class RulesWorkbookError(Exception):
    message: str
    expected_sheets: List[str]
    found_sheets: List[str]

    def __str__(self) -> str:
        exp = ", ".join(self.expected_sheets) if self.expected_sheets else "(none)"
        found = ", ".join(self.found_sheets) if self.found_sheets else "(none)"
        return f"{self.message}\n\nExpected sheets: {exp}\nFound sheets: {found}"
