from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import json
import base64
import os

@dataclass
class VLMResponse:
    text: str; model: str; usage: dict[str,Any] | None; cost: float | None; raw_response: dict[str,Any] | None

class VLMClient:
    def generate(self, system_prompt: str, user_prompt: str, images: list[Path], response_schema: dict[str,Any] | None=None, seed: int|None=None) -> VLMResponse: raise NotImplementedError

class MockVLMClient(VLMClient):
    def generate(self, system_prompt, user_prompt, images, response_schema=None, seed=None):
        context=json.loads(user_prompt); c=context["condition"]; z=context["center_slice"]
        if "Agent 2" in system_prompt:
            code=("import json, numpy as np\nfrom pathlib import Path\nfrom PIL import Image\nroot=Path('.')\nstack=np.load(root/'inputs'/'stack.npy')\nresult={'condition':CONDITION,'center_slice':CENTER,'detections':[],'counts':{'missing':0,'broken':0,'thin':0,'bent':0,'apparently_intact':0,'uncertain':0},'implemented_instructions':['adaptive percentile foreground measurement'],'partially_implemented_instructions':[],'unsupported_instructions':[],'agent2_assumptions':['mock deterministic code'],'uncertain_candidates':[],'errors':[]}\n(root/'measurements').mkdir(exist_ok=True); (root/'intermediate').mkdir(exist_ok=True); (root/'overlays').mkdir(exist_ok=True)\nnp.save(root/'intermediate'/'foreground.npy',stack > np.percentile(stack,70))\na=stack[3]; lo,hi=np.percentile(a,(1,99)); Image.fromarray(np.clip((a-lo)*255/max(hi-lo,1),0,255).astype('uint8')).save(root/'overlays'/'center_overlay.png')\n(root/'measurements'/'agent2_output.json').write_text(json.dumps(result))\n")
            return VLMResponse(json.dumps({"code":code}),"mock-vlm",{"total_tokens":1},0.0,{})
        out={"condition":c,"center_slice":z,"observations":[{"observation_id":"obs_001","description":"Measure foreground continuity across seven ordered slices.","evidence_slices":[z-1,z,z+1],"observation_type":"direct","confidence":0.5}],"assumptions":[{"assumption_id":"assumption_001","description":"Intensity supports adaptive foreground estimation.","required_for_method":True}],"defect_definitions":{x:{"visual_indicators":[],"measurable_tests":["adaptive component measurement"],"confounding_cases":[]} for x in ("missing","broken","thin","bent")},"algorithm":{"preprocessing":["robust percentile normalization"],"candidate_detection":["components"],"feature_measurement":["occupancy"],"unsupervised_reference_estimation":["median"],"classification_logic":["report uncertain evidence"],"uncertainty_handling":["insufficient local evidence"]},"required_inputs_for_code":["stack.npy"],"expected_outputs":["candidate JSON"],"paper_citations":[],"limitations":["seven slices are local evidence"],"implementation_instructions":["Use adaptive percentile measurement and save structured output."]}
        return VLMResponse(json.dumps(out),"mock-vlm",{"total_tokens":1},0.0,{})

class HuggingFaceVLMClient(VLMClient):
    """Fresh stateless Hugging Face request; the token remains in HF_TOKEN."""
    def __init__(self, model: str, temperature: float, max_tokens: int, timeout: int):
        self.model, self.temperature, self.max_tokens, self.timeout = model, temperature, max_tokens, timeout
    def generate(self, system_prompt, user_prompt, images, response_schema=None, seed=None):
        from huggingface_hub import InferenceClient, get_token
        token = os.environ.get("HF_TOKEN") or get_token()
        if not token: raise RuntimeError("HF_TOKEN is required for provider: huggingface")
        content = [{"type":"text","text":user_prompt}]
        for image in images:
            content.append({"type":"image_url","image_url":{"url":"data:image/png;base64," + base64.b64encode(image.read_bytes()).decode("ascii")}})
        response = InferenceClient(model=self.model, token=token, timeout=self.timeout).chat_completion(messages=[{"role":"system","content":system_prompt},{"role":"user","content":content}], max_tokens=self.max_tokens, temperature=self.temperature)
        usage = getattr(response, "usage", None)
        parsed_usage = {k:getattr(usage,k) for k in ("prompt_tokens","completion_tokens","total_tokens") if getattr(usage,k,None) is not None} if usage else None
        return VLMResponse(response.choices[0].message.content, self.model, parsed_usage, None, {"provider":"huggingface"})

def make_client(config: dict) -> VLMClient:
    if config["vlm"]["provider"] == "mock": return MockVLMClient()
    if config["vlm"]["provider"] == "huggingface":
        settings=config["vlm"]
        return HuggingFaceVLMClient(settings["model"],float(settings.get("temperature",0.2)),int(settings.get("max_tokens",6000)),int(settings.get("timeout_seconds",180)))
    raise RuntimeError("unsupported provider; use mock or huggingface")
