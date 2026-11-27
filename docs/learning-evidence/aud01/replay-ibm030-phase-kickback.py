"""Verify the forward phase-kickback circuit drawn on IBM-030 slide 4."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("slides", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
slides_hash = hashlib.sha256(args.slides.read_bytes()).hexdigest()
assert slides_hash == "02be18ffcd56ac5b9d4bd43a69180ac1330f285fc8dfc30ed5559142d04091c1"
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
checks = 0
for mask in range(16):
    # The query maps |a,x> to |a xor f(x),x>. Compare the full output,
    # including the ancilla, with (-1)^f(x) |-> tensor |x>.
    targets = [j ^ (((mask >> (j % 4)) & 1) << 2) for j in range(8)]
    elements = [str(int(i == targets[j])) for i in range(8) for j in range(8)]
    query = "matrix(8,8,[" + ",".join(elements) + "])"
    for x in range(4):
        state = f"(([1;-1]/sqrt(2)) @ basis({x},4))"
        sign = 1 - 2 * ((mask >> x) & 1)
        for phase, expected in ((sign, "1"), (-sign, "0")):
            expression = f"quantum:({query}*{state})=(({phase})*{state})"
            result = subprocess.run([worker, "--json"], input=expression.encode(), env=env,
                                    capture_output=True, check=True, timeout=30)
            answer = json.loads(result.stdout)
            assert not answer["approximate"] and answer["copy_text"] == expected, (mask, x, phase)
            checks += 1
print(json.dumps(dict(slides_sha256=slides_hash, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                      boolean_functions=16, input_words=4, exact_comparisons=checks), indent=2))
