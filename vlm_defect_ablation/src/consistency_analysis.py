from __future__ import annotations

def bbox_iou(a: dict, b: dict) -> float:
    x0,y0=max(a["x_min"],b["x_min"]),max(a["y_min"],b["y_min"]); x1,y1=min(a["x_max"],b["x_max"]),min(a["y_max"],b["y_max"])
    inter=max(0,x1-x0)*max(0,y1-y0); aa=max(0,a["x_max"]-a["x_min"])*max(0,a["y_max"]-a["y_min"]); bb=max(0,b["x_max"]-b["x_min"])*max(0,b["y_max"]-b["y_min"])
    return inter/(aa+bb-inter) if aa+bb-inter else 0.0

def compare_detections(left: list[dict], right: list[dict]) -> dict:
    pairs=[(a,b,bbox_iou(a["bounding_box"],b["bounding_box"])) for a in left for b in right]
    matched=[p for p in pairs if p[2]>0]; return {"left_candidates":len(left),"right_candidates":len(right),"overlapping_pairs":len(matched),"mean_iou":sum(p[2] for p in matched)/len(matched) if matched else 0.0,"category_agreement":sum(a["label"]==b["label"] for a,b,_ in matched)/len(matched) if matched else 0.0}
