from __future__ import annotations

import re


_SUFFIX_RE = re.compile(r"^\s*(\d{1,3})\s*$")  # 1..999 suffix


def expand_child_code(parent_code: str, child_code: str, delimiter: str = ".") -> str:
    p = (parent_code or "").strip()
    c = (child_code or "").strip()

    if not c:
        return c
    if not p:
        return c

    # if already contains delimiter, assume it's a full code
    if delimiter and delimiter in c:
        return c

    m = _SUFFIX_RE.match(c)
    if not m:
        return c

    suffix = str(int(m.group(1)))  # "06" -> "6"
    return f"{p}{delimiter}{suffix}"
