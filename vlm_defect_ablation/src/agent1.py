from pathlib import Path
import json, time
from .schema_validation import validate
from .manifest import save_json

SYSTEM="You are Agent 1. Analyze only supplied context and return JSON instructions, never a final detector label. Use measurable adaptive operations and uncertainty."
def run_agent1(client, context, images: list[Path], schema: Path, run: Path, seed=None):
    prompts=run/"prompts"; prompts.mkdir(exist_ok=True); (prompts/"agent1_system.txt").write_text(SYSTEM); (prompts/"agent1_user.json").write_text(json.dumps(context,indent=2))
    start=time.monotonic(); response=client.generate(SYSTEM,json.dumps(context),images,seed=seed); (run/"agent1").mkdir(exist_ok=True); (run/"agent1"/"raw_response.txt").write_text(response.text)
    try: data=json.loads(response.text); errors=validate(data,schema)
    except Exception as e: data=None; errors=[str(e)]
    if errors:
        repair={"invalid_response":response.text,"validation_errors":errors,"schema":json.loads(schema.read_text())}; repaired=client.generate(SYSTEM+" Repair only valid JSON.",json.dumps(repair),images,seed=seed); (run/"agent1"/"repaired_response.txt").write_text(repaired.text)
        try: data=json.loads(repaired.text); errors=validate(data,schema)
        except Exception as e: errors=[str(e)]
    if not errors: save_json(run/"agent1"/"validated.json",data)
    return data, errors, {"model":response.model,"usage":response.usage,"cost":response.cost,"runtime_seconds":time.monotonic()-start}
