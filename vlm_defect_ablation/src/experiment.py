from __future__ import annotations
from pathlib import Path
import json, traceback
import numpy as np
from .tiff_loader import load_volume
from .stack_builder import build_stack, select_centers
from .contact_sheet import create_contact_sheet
from .geometry_adapter import normalize_geometry
from .paper_extractor import extract_paper
from .condition_builder import build_condition
from .manifest import create_manifest, save_json
from .leakage_check import check_leakage
from .paths import run_dir
from .vlm_client import make_client
from .agent1 import run_agent1
from .agent2 import run_agent2
from .code_safety import inspect_code
from .code_runner import execute_code
from .schema_validation import validate
from .reporting import write_summary

ROOT=Path(__file__).resolve().parents[1]
def _counts(instructions, detections, run: Path | None = None, execution: dict | None = None):
    alg=instructions.get("algorithm",{}); observations=instructions.get("observations",[]); counts=detections.get("counts",{}) if detections else {}
    uncertain=counts.get("uncertain",0); total=sum(counts.values())
    return {"number_of_direct_observations":sum(x.get("observation_type")=="direct" for x in observations),"number_of_inferred_observations":sum(x.get("observation_type")=="inferred" for x in observations),"number_of_assumptions":len(instructions.get("assumptions",[])),"number_of_measurable_tests":sum(len(v.get("measurable_tests",[])) for v in instructions.get("defect_definitions",{}).values()),"number_of_preprocessing_steps":len(alg.get("preprocessing",[])),"number_of_features_proposed":len(alg.get("feature_measurement",[])),"number_of_classification_rules":len(alg.get("classification_logic",[])),"number_of_uncertainty_rules":len(alg.get("uncertainty_handling",[])),"number_of_instructions_implemented":len(detections.get("implemented_instructions",[])),"number_of_instructions_partially_implemented":len(detections.get("partially_implemented_instructions",[])),"number_of_unsupported_instructions":len(detections.get("unsupported_instructions",[])),"number_of_agent2_assumptions":len(detections.get("agent2_assumptions",[])),"number_of_uncertain_candidates":len(detections.get("uncertain_candidates",[])),"percentage_uncertain":uncertain/total if total else 0.0,"number_of_intermediate_outputs_generated":len(list((run/"intermediate").glob("*"))) if run else 0,"number_of_runtime_warnings":0,"number_of_execution_errors":0 if execution and execution.get("success") else 1,**{f"detections_{k}":counts.get(k,0) for k in ("missing","broken","thin","bent","apparently_intact","uncertain")}}

def run_experiment(config: dict, centers_override=None, conditions_override=None, force=False) -> list[dict]:
    volume=load_volume(config["data"]["tiff_path"]); output=Path(config["data"]["output_dir"]); client=make_client(config)
    geometry=normalize_geometry(config["data"]["geometry_json_path"],config["geometry"]["registered_to_tiff"],config["volume"].get("voxel_spacing")) if config["data"].get("geometry_json_path") else None
    paper=extract_paper(config["data"]["paper_path"],**config["paper"]) if config["data"].get("paper_path") else None
    rows=[]; conditions=conditions_override or config["experiment"]["conditions"]
    for condition in conditions:
      for center in select_centers(volume.shape[0],config["stacks"],centers_override):
       for attempt in range(1,int(config["experiment"].get("repeats",1))+1):
        run=run_dir(output,condition,center,attempt); completion=run/"execution"/"status.json"; row={"condition":condition,"center_slice":center,"attempt":attempt}
        if completion.exists() and not(force or config["experiment"].get("force")): row["skipped_resume"]=True; rows.append(row); continue
        try:
          stack=build_stack(volume,center); image=run/"inputs"/f"stack_{center:06d}.png"; create_contact_sheet(stack,image,int(config["stacks"].get("contact_sheet_max_dimension",2048)))
          built=build_condition(condition,stack,config,run,geometry,paper)
          if built["skip"]: row.update({"status":"skipped","reason":"; ".join(built["skip"])}); save_json(completion,row); rows.append(row); continue
          images=[image]; built["files"].append(image)
          if "segmentation" in built["context"]:
            masks=np.load(built["context"]["segmentation"]["path"]); mask_stack=type(stack)(stack.center_slice,stack.indices,masks,stack.original_dimensions)
            mask_image=run/"inputs"/f"mask_{center:06d}.png"; create_contact_sheet(mask_stack,mask_image,int(config["stacks"].get("contact_sheet_max_dimension",2048))); images.append(mask_image); built["files"].append(mask_image)
          manifest=create_manifest(condition,center,built["files"],built["context"],attempt); save_json(run/"manifest.json",manifest)
          leaks=check_leakage(condition,built["context"],built["files"])
          if leaks: row.update({"status":"failed","failure":"leakage_check","errors":leaks}); save_json(completion,row); rows.append(row); continue
          a1,errors,meta=run_agent1(client,built["context"],images,ROOT/"schemas"/"agent1_output.schema.json",run,config["stacks"].get("random_seed"))
          row.update({"agent1_request_success":not bool(errors),"agent1_schema_valid":not bool(errors),"token_usage":(meta.get("usage")or{}).get("total_tokens"),"estimated_request_cost":meta.get("cost")})
          if errors: row.update({"status":"failed","failure":"invalid_agent1_json","errors":errors}); save_json(completion,row); rows.append(row); continue
          script,errors,meta2=run_agent2(client,built["context"],a1,images,run,config["stacks"].get("random_seed")); row["agent2_request_success"]=not bool(errors)
          if errors: row.update({"status":"failed","failure":"code_generation","errors":errors}); save_json(completion,row); rows.append(row); continue
          unsafe=inspect_code(script); row["generated_code_safety_status"]="safe" if not unsafe else "rejected"
          if unsafe: row.update({"status":"failed","failure":"unsafe_generated_code","errors":unsafe}); save_json(completion,row); rows.append(row); continue
          execution=execute_code(script,run,int(config["execution"]["timeout_seconds"])); save_json(run/"execution"/"status.json",execution); row["generated_code_execution_success"]=execution["success"]
          result_path=run/"measurements"/"agent2_output.json"; detections=json.loads(result_path.read_text()) if execution["success"] and result_path.exists() else None
          validation=validate(detections,ROOT/"schemas"/"agent2_output.schema.json") if detections is not None else ["missing agent2 output"]
          row.update(_counts(a1,detections or {},run,execution)); row.update({"status":"complete" if not validation else "failed","errors":validation,"runtime_seconds":meta["runtime_seconds"]+meta2["runtime_seconds"]}); save_json(completion,row); rows.append(row)
        except Exception as exc:
          row.update({"status":"failed","failure":"runtime_exception","errors":[str(exc)],"traceback":traceback.format_exc()}); save_json(completion,row); rows.append(row)
    write_summary(rows,output/"summary.csv"); return rows
