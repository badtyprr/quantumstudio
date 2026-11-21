"""Compare the exported binary and Hadamard tables against the CSS code."""

import json
from pathlib import Path
import re
import sys

rows = json.loads(Path(sys.argv[1]).read_bytes())["rows"]

def masks(row):
    return [int(mask) for mask in re.findall(r"qbitlabel\((\d+),\s*7\)", rows[row-1]["copy"])]

def span(generators):
    words = {0}
    for generator in generators:
        words |= {word ^ generator for word in words}
    return words

words = masks(36)
checks = masks(83)
assert len(words) == len(set(words)) == 16
assert span(masks(82)) == set(words)
assert len(checks) == 3 and checks == masks(91)
assert {n for n in range(128) if all((n & v).bit_count() % 2 == 0 for v in checks)} == set(words)
assert min(n.bit_count() for n in words if n) == 3
states = re.findall(r"matrix\(128,1,\[([^\]]+)\]\)", rows[114]["copy"])
assert len(states) == len(words)
for word, state in zip(words, states):
    entries = state.split(",")
    assert len(entries) == 128
    for column, value in enumerate(entries):
        sign = "−" if (word & column).bit_count() % 2 else ""
        assert value.strip() == sign + "1 ∕ (√(2) ⋅ 8)", (word, column, value)
print("Verified 16 codewords, their generator and parity checks, and all 2,048 Hadamard amplitudes.")

if len(sys.argv) > 2:
    import os
    import subprocess
    worker = Path(sys.argv[2]).resolve()
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
    def evaluate(expression):
        result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                                capture_output=True, env=env, check=True, timeout=30)
        return json.loads(result.stdout)["copy_text"]
    def labels(values, width=7):
        return "vector(" + ",".join(f"qbitlabel({v},{width})" for v in values) + ")"
    for expression, expected in [
        ("qwordspan(" + labels(masks(82)) + ")", set(words)),
        ("qwordkernel(" + labels(checks) + ",7)", set(words)),
        ("qwordspan(" + labels([3,3,0], 2) + ")", {0,3}),
        ("qwordkernel(vector(),2)", {0,1,2,3}),
    ]:
        result = evaluate(expression)
        found = re.findall(r"qbitlabel\((\d+),\d+\)", result)
        assert len(found) == len(expected) and set(map(int, found)) == expected, (expression, result)
    for values, expected in [([1,2],"1"), ([1,4],"0"), ([],"1")]:
        left = "qset(vector(" + ",".join(map(str, values)) + "))"
        assert evaluate(f"qsubset({left},qset(vector(1,2,3)))") == expected
    print("Verified binary spans, parity kernels, and positive, negative and empty subset cases.")
