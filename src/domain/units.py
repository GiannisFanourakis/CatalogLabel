from __future__ import annotations

# PDF points: 72 points per inch
# 1 inch = 2.54 cm
def cm_to_pt(cm: float) -> float:
    return float(cm) * 72.0 / 2.54

