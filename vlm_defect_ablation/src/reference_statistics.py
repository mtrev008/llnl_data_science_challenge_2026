from __future__ import annotations
import numpy as np

def robust_reference(rows: list[dict]) -> dict:
    values=np.asarray([r["value"] for r in rows if "value" in r],dtype=float)
    if not len(values): return {"count":0,"median":None,"mad":None}
    median=float(np.median(values)); return {"count":int(len(values)),"median":median,"mad":float(np.median(np.abs(values-median)))}
