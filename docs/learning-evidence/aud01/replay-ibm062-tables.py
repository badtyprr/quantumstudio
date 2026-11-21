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
