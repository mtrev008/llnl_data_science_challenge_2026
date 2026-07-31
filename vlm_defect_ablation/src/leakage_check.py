from __future__ import annotations
import json

FORBIDDEN={"images_only":("strut_id","junction","geometry","segmentation","paper","voxel_spacing","expected path"),"images_segmentation":("strut_id","junction","geometry","paper","expected path"),"images_geometry":("segmentation","paper"),"images_segmentation_geometry":("paper",),"images_paper":("strut_id","junction","geometry","segmentation","expected path"),"full_context":()}

def check_leakage(condition: str, context: dict, files: list, prior_output_root=None) -> list[str]:
    text=json.dumps(context).lower(); violations=[]
    for token in FORBIDDEN[condition]:
        if token in text: violations.append(f"prohibited context token: {token}")
    for path in files:
        name=getattr(path,"name",str(path)).lower()
        if any(x in name for x in ("missing","broken","thin","bent","defect")): violations.append(f"non-neutral filename: {name}")
    return violations
