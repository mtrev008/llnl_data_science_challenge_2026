from pathlib import Path
import json, time
from .manifest import save_json

SYSTEM="You are Agent 2. Return JSON with exactly one standalone Python script in code. Implement only permitted inputs, no network, shell, destructive operations, or external files."
def run_agent2(client, context, instructions, images: list[Path], run: Path, seed=None):
    payload={"context":context,"agent1_instructions":instructions,"output_directory":"."}; prompts=run/"prompts"; (prompts/"agent2_system.txt").write_text(SYSTEM); (prompts/"agent2_user.json").write_text(json.dumps(payload,indent=2))
    start=time.monotonic(); response=client.generate(SYSTEM,json.dumps(context),images,seed=seed); (run/"agent2").mkdir(exist_ok=True); (run/"agent2"/"raw_response.txt").write_text(response.text)
    try: code=json.loads(response.text)["code"]
    except Exception as e: return None,[f"invalid Agent 2 response: {e}"],{"runtime_seconds":time.monotonic()-start}
    path=run/"generated_code"/"detector.py"; path.parent.mkdir(exist_ok=True); path.write_text("CONDITION="+repr(context["condition"])+"\nCENTER="+repr(context["center_slice"])+"\n"+code)
    return path,[],{"model":response.model,"usage":response.usage,"cost":response.cost,"runtime_seconds":time.monotonic()-start}
