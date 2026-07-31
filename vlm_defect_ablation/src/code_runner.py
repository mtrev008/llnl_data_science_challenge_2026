from __future__ import annotations
from pathlib import Path
import os, subprocess, sys

def execute_code(script: Path, run: Path, timeout_seconds: int) -> dict:
    env={"PATH":os.environ.get("PATH", ""),"PYTHONNOUSERSITE":"1","PYTHONPATH":"","HOME":str(run),"MPLCONFIGDIR":str(run/".mpl")}
    try:
        done=subprocess.run([sys.executable,"-I",str(script.relative_to(run))],cwd=run,env=env,text=True,capture_output=True,timeout=timeout_seconds)
        return {"success":done.returncode==0,"returncode":done.returncode,"stdout":done.stdout,"stderr":done.stderr,"timeout":False}
    except subprocess.TimeoutExpired as e: return {"success":False,"timeout":True,"stdout":e.stdout or "","stderr":e.stderr or ""}
