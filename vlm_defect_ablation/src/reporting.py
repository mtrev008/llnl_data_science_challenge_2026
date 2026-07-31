from pathlib import Path
import csv, json

def write_summary(rows: list[dict], output: Path) -> None:
    output.parent.mkdir(parents=True,exist_ok=True)
    fields=sorted({k for row in rows for k in row}) if rows else ["condition","center_slice"]
    with output.open("w",newline="",encoding="utf-8") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)

def create_report(rows: list[dict], output: Path) -> None:
    output.write_text("# VLM defect-ablation report\n\nNo labels were used; candidate agreement is not correctness.\n\n"+json.dumps(rows,indent=2),encoding="utf-8")
