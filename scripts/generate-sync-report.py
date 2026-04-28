#!/usr/bin/env python3
# Thin wrapper — see update-main-sync.py
import subprocess
import sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent
script = ROOT / "update-main-sync.py"
args = [sys.executable, str(script), "report", *sys.argv[1:]]
raise SystemExit(subprocess.call(args))
