"""Check the composition examples on pages 25, 26 and 47 of the single-systems slides."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("slides", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
slide_hash = hashlib.sha256(args.slides.read_bytes()).hexdigest()
assert slide_hash == "e3148ab53d2e0fc45a08230dd765e71df131d527f7782aec9ab9fe17120b4392"
worker = args.worker.resolve()
m1, m2, v = "[1,1;0,0]", "[0,1;1,0]", "[3/5;2/5]"
root_not = "[(1+i)/2,(1-i)/2;(1-i)/2,(1+i)/2]"
cases = [
    (25, f"{m2}*({m1}*{v})=({m2}*{m1})*{v}", "1"),
    (26, f"{m2}*{m1}=[0,0;1,1]", "1"),
    (26, f"{m1}*{m2}=[1,1;0,0]", "1"),
    (26, f"{m2}*{m1}={m1}*{m2}", "0"),
    (47, f"H*S*H={root_not}", "1"),
    (47, f"({root_not})^2=X", "1"),
]
checks = []
for page, expression, expected in cases:
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            check=True, capture_output=True, timeout=30,
                            env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
    value = json.loads(result.stdout)
    assert not value["approximate"] and value["copy_text"] == expected, expression
    checks.append(dict(page=page, expression=expression, result=expected))
print(json.dumps(dict(slides_sha256=slide_hash,
                      source="https://ibm.box.com/public/static/95va6f5vqru3mpsv9p5ivwcyxino4rk7.pdf",
                      worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                      checks=checks), indent=2))
