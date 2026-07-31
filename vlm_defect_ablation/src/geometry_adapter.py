from __future__ import annotations
import json
from pathlib import Path
from typing import Any

def normalize_geometry(path: str | Path, registered_to_tiff: bool = False, voxel_spacing: dict | None = None) -> dict[str, Any]:
    raw = json.loads(Path(path).read_text()); junction_raw = raw.get("junctions") if isinstance(raw.get("junctions"), list) else []
    junctions = []
    for item in junction_raw:
        pos = item.get("position") or item.get("coordinates") or [None, None, None]
        junctions.append({"junction_id": item.get("id", item.get("junction_id")), "x": pos[0] if len(pos)>0 else None, "y": pos[1] if len(pos)>1 else None, "z": pos[2] if len(pos)>2 else None})
    lookup = {x["junction_id"]: x for x in junctions}; struts=[]
    for item in raw.get("struts", []) if isinstance(raw.get("struts"), list) else []:
        a,b=item.get("junction0", item.get("endpoint_a_id")),item.get("junction1", item.get("endpoint_b_id")); ja,jb=lookup.get(a),lookup.get(b)
        struts.append({"strut_id": item.get("id", item.get("strut_id")), "junction_ids": [a,b], "endpoint_a": [ja[k] for k in ("x","y","z")] if ja else None, "endpoint_b": [jb[k] for k in ("x","y","z")] if jb else None})
    return {"metadata":{"coordinate_order":"xyz","units":raw.get("units", "unknown"),"registered_to_tiff":bool(registered_to_tiff),"voxel_spacing":voxel_spacing or {}},"junctions":junctions,"struts":struts}

def relevant_geometry(normalized: dict, indices: tuple[int, ...]) -> dict:
    if not normalized["metadata"]["registered_to_tiff"]: return normalized
    lo,hi=min(indices),max(indices); keep=[]
    for s in normalized["struts"]:
        zs=[p[2] for p in (s["endpoint_a"],s["endpoint_b"]) if p and p[2] is not None]
        if not zs or min(zs) <= hi and max(zs) >= lo: keep.append(s)
    return {**normalized,"struts":keep,"geometry_filtering_method":"endpoint z-range intersection"}
