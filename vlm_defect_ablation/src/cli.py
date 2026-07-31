from __future__ import annotations
import argparse, json
from pathlib import Path
from .config import load_config
from .tiff_loader import inspect_tiff, load_volume
from .stack_builder import select_centers, build_stack
from .contact_sheet import create_contact_sheet
from .geometry_adapter import normalize_geometry
from .paper_extractor import extract_paper
from .experiment import run_experiment
from .consistency_analysis import compare_detections
from .stability_analysis import compare_repeats
from .reporting import create_report

def parser():
 p=argparse.ArgumentParser(); p.add_argument("command",choices=["inspect-data","build-stacks","inspect-geometry","extract-paper","run-agent1","run-agent2","run-experiment","analyze-consistency","analyze-stability","create-report"]); p.add_argument("--config",required=True); p.add_argument("--center-slices",nargs="*",type=int); p.add_argument("--conditions",nargs="*"); p.add_argument("--force",action="store_true"); return p
def main(argv=None):
 a=parser().parse_args(argv); c=load_config(a.config)
 if a.command=="inspect-data": print(json.dumps(inspect_tiff(c["data"]["tiff_path"]),indent=2)); return
 if a.command=="build-stacks":
  volume=load_volume(c["data"]["tiff_path"]); centers=select_centers(volume.shape[0],c["stacks"],a.center_slices); print(json.dumps({"centers":centers,"count":len(centers)})); return
 if a.command=="inspect-geometry": print(json.dumps(normalize_geometry(c["data"]["geometry_json_path"],c["geometry"]["registered_to_tiff"]),indent=2)); return
 if a.command=="extract-paper": print(json.dumps(extract_paper(c["data"]["paper_path"],**c["paper"]),indent=2)); return
 if a.command in ("run-agent1","run-agent2","run-experiment"):
  rows=run_experiment(c,a.center_slices,a.conditions,a.force); print(json.dumps(rows,indent=2)); return
 out=Path(c["data"]["output_dir"]); summary=out/"summary.csv"
 if a.command=="create-report": create_report([],out/"report.md"); return
 print(json.dumps({"status":"analysis requires completed structured results","summary":str(summary)}))
if __name__=="__main__": main()
