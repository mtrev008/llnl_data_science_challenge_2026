from pathlib import Path
import json
from jsonschema import Draft202012Validator

def validate(data: object, schema_path: Path) -> list[str]:
    schema=json.loads(schema_path.read_text()); return [e.message for e in Draft202012Validator(schema).iter_errors(data)]
