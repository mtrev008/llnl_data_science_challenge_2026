from __future__ import annotations
from .consistency_analysis import compare_detections

def compare_repeats(outputs: list[dict]) -> dict:
    if len(outputs)<2:return {"repeat_count":len(outputs),"stable":None,"pairs":[]}
    pairs=[compare_detections(a.get("detections",[]),b.get("detections",[])) for i,a in enumerate(outputs) for b in outputs[i+1:]]
    return {"repeat_count":len(outputs),"stable":all(p["category_agreement"]>=0.8 for p in pairs),"pairs":pairs}
