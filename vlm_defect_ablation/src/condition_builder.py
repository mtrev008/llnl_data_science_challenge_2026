from __future__ import annotations
from pathlib import Path
import json
import numpy as np
from .stack_builder import SliceStack
from .segmentation_loader import load_masks, auto_segment
from .geometry_adapter import relevant_geometry
from .manifest import save_json

REQUIRES={"images_only":set(),"images_segmentation":{"segmentation"},"images_geometry":{"geometry"},"images_segmentation_geometry":{"segmentation","geometry"},"images_paper":{"paper"},"full_context":{"segmentation","geometry","paper"}}

def build_condition(condition: str, stack: SliceStack, config: dict, run: Path, geometry: dict | None, paper: dict | None) -> dict:
    needed=REQUIRES[condition]; data=config["data"]; unavailable=[]
    for kind,key in (("segmentation","segmentation_path"),("geometry","geometry_json_path"),("paper","paper_path")):
        if kind in needed and not data.get(key) and not (kind == "segmentation" and config["segmentation"].get("on_the_fly")):
            unavailable.append(f"{condition} requires {key}")
    if unavailable: return {"skip": unavailable}
    inputs=run/"inputs"; inputs.mkdir(parents=True,exist_ok=True); stack_path=inputs/"stack.npy"; np.save(stack_path, stack.arrays)
    files=[stack_path]; context={"condition":condition,"slice_indices":list(stack.indices),"center_slice":stack.center_slice,"defects":["missing","broken","thin","bent"],"stack_path":str(stack_path)}
    if "segmentation" in needed:
        masks,meta=(load_masks(data["segmentation_path"], stack.indices), {"method":"provided"}) if data.get("segmentation_path") else auto_segment(stack.arrays)
        p=inputs/"masks.npy"; np.save(p,masks); files.append(p); context["segmentation"]={**meta,"path":str(p),"foreground_fraction":float(masks.mean())}
    if "geometry" in needed:
        selected=relevant_geometry(geometry,stack.indices); p=inputs/"geometry.json"; save_json(p,selected); files.append(p)
        context["geometry"]={"path":str(p),"registered_to_tiff":selected["metadata"]["registered_to_tiff"],"strut_count":len(selected["struts"]),"junction_count":len(selected["junctions"]),"coordinate_order":"xyz"}
    if "paper" in needed:
        p=inputs/"paper_excerpt.txt"; p.write_text(paper["excerpts"],encoding="utf-8"); files.append(p); context["paper"]={"title":paper["title"],"pages":paper["pages"],"path":str(p),"external_methodological_context":True}
    return {"files":files,"context":context,"skip":[]}
