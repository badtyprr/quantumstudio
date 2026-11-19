"""Replay IBM-025's source matrix and garbage-free oracle equation."""
import json
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
source = json.loads(Path(__file__).with_name("ibm025-reversible-inputs.json").read_bytes())
records = {}

def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, timeout=20)
    assert result.returncode == 0, (expression, result.stderr)
    return json.loads(result.stdout)

for row in source["rows"]:
    records[row["id"][-4:]] = evaluate(row["literal"])

toffoli = records["M001"]["copy_text"]
# IBM orders the two low bits as controls and the high bit as target.
for column in range(8):
    target = column ^ (4 if column & 3 == 3 else 0)
    assert evaluate(f"{toffoli}*basis({column},8)=basis({target},8)")["copy_text"] == "1"

row = next(row for row in source["rows"] if row["id"].endswith("M062"))
original = row["literal"].strip("$").strip()
copied = records["M062"]["copy_text"]
displayed = records["M062"]["display_text"]
assert evaluate(copied)["copy_text"] == evaluate(displayed)["copy_text"] == copied
# Enumerate all four one-bit Boolean functions, all basis inputs, and
# two implementations. A faulty implementation always flips one extra bit.
for table in ((0, 0), (0, 1), (1, 0), (1, 1)):
    pairs = [f"qtuple(vector(bitstring({x},1),bitstring({value},1)))"
             for x, value in enumerate(table)]
    graph = "qset(vector(" + ",".join(pairs) + "))"
    for faulty in (False, True):
        entries = [str(int(i == (j ^ (4 * table[j & 1]) ^ (2 if faulty else 0))))
                   for i in range(8) for j in range(8)]
        operator = "matrix(8,8,[" + ",".join(entries) + "])"
        for x in (0, 1):
            for y in (0, 1):
                for body in (original, displayed, copied):
                    bindings = [("f", graph), ("x", f"bitstring({x},1)"),
                                ("y", f"bitstring({y},1)"), ("k", "1"), ("Q", operator)]
                    for name, value in bindings:
                        body = f"replace(({body}),{name},{value})"
                    assert evaluate(body)["copy_text"] == str(int(not faulty)), (table, faulty, x, y)
assert evaluate('replace(|y # 01>,y,bitstring(3,2))')["copy_text"] == "matrix(4,1,[0,0,1,0])"
print("Verified 91 source inputs, eight Toffoli columns and 96 oracle substitutions.")
