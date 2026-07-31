from __future__ import annotations
import ast
from pathlib import Path

BANNED_IMPORTS={"subprocess","socket","requests","urllib","http","ftplib","shutil","multiprocessing"}
BANNED_CALLS={"eval","exec","compile","__import__","system","popen","rmtree","remove","unlink","rmdir","chdir"}

def inspect_code(path: Path) -> list[str]:
    source=path.read_text(); issues=[]
    if ".." in source: issues.append("parent-directory traversal is forbidden")
    try: tree=ast.parse(source)
    except SyntaxError as e: return [f"syntax error: {e}"]
    for node in ast.walk(tree):
        if isinstance(node,(ast.Import,ast.ImportFrom)):
            for name in node.names:
                if name.name.split(".")[0] in BANNED_IMPORTS: issues.append(f"banned import: {name.name}")
        if isinstance(node,ast.Call):
            fn=node.func.id if isinstance(node.func,ast.Name) else node.func.attr if isinstance(node.func,ast.Attribute) else ""
            if fn in BANNED_CALLS: issues.append(f"banned call: {fn}")
        if isinstance(node,ast.Constant) and isinstance(node.value,str) and (node.value.startswith("/") or "pip install" in node.value.lower()): issues.append("absolute path or installation command")
    return sorted(set(issues))
