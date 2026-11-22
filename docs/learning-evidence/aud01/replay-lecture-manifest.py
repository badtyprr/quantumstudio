"""Replay the equations in a lecture manifest against the specified calculator and PDF."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
for name in ("manifest", "slides", "worker", "report"):
    parser.add_argument(name, type=Path)
args = parser.parse_args()
manifest = json.loads(args.manifest.read_bytes())
digest = hashlib.sha256(args.slides.read_bytes()).hexdigest()
if digest != manifest["slides"]["sha256"]:
    raise ValueError("The supplied slide deck differs from the audited edition")
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
records = []
for check in manifest["checks"]:
    result = subprocess.run([worker, "--json"], input=("quantum:" + check["equation"]).encode(),
                            capture_output=True, env=env, timeout=30)
    exact = False
    if result.returncode:
        actual = result.stderr.decode(errors="replace").strip()
    else:
        response = json.loads(result.stdout)
        actual = response["copy_text"]
        exact = response["approximate"] is False
    records.append(dict(check, actual=actual, exact=exact, passed=exact and actual == check["expected"]))
report = dict(slides_sha256=digest, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(), checks=records)
args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf8")
failures = [r["label"] for r in records if not r["passed"]]
if failures:
    raise SystemExit("Unresolved checks: " + ", ".join(failures))
print(f"{len(records)} checks passed")
