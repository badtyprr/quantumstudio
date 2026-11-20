"""Compatibility entry point for the pinned phase-estimation procedure replay."""
from pathlib import Path
import runpy
import sys

sys.argv.extend(["--lesson", "IBM028"])
runpy.run_path(str(Path(__file__).with_name("replay-phase-estimation-inventory.py")), run_name="__main__")
