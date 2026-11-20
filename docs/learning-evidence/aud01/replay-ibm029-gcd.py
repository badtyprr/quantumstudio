"""Check the integer GCD formulas from the pinned Shor notebook in their Windows forms."""
import argparse
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("windows_directory", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
worker = args.package.resolve() / "quantum-worker.exe"
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())
rows = [r for r in inventory["rows"] if r"\gcd" in r["literal"]]
records_path = args.windows_directory / "records.json"
records = json.loads(records_path.read_bytes())
suite = json.loads((args.windows_directory / "result.json").read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"] == len(records) == len(rows) == 9


@lru_cache(maxsize=2048)
def evaluate(text):
    return subprocess.run([worker, "--json"], input=("quantum:" + text).encode(), env=env,
                          timeout=30, capture_output=True)


def copied(text):
    result = evaluate(text)
    assert result.returncode == 0, (text, result.stderr)
    response = json.loads(result.stdout)
    assert not response["approximate"], text
    return response["copy_text"]


cases = {}
windows = {}
for source, row in zip(rows, records):
    key = source["id"]
    assert key == row["id"] and row["restored_same"] and row["label"] == row["reentry_label"] == "EXACT RESULT"
    saved = json.loads((args.windows_directory / (key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Expression"] == source["literal"] and saved["Mode"] == 0
    windows[key] = {field: row[field] for field in ("display", "copy", "second_copy")}

    def verify(bindings, expected):
        for text in windows[key].values():
            for name, value in bindings:
                text = f"replace(({text}),{name},({value}))"
            actual = copied(text)
            assert actual == str(expected), (key, bindings, expected, actual)
        cases.setdefault(key, []).append(dict(bindings=bindings, expected=expected))

    number = int(key[-3:])
    if number == 27:
        for modulus in (1,2,6,7,21):
            verify([("N",modulus)], 1)
    elif number == 34:
        verify([], 1)
    elif number == 406:
        for a, order, modulus in [(2,4,15), (4,2,15), (2,6,21), (14,2,15), (8,4,15)]:
            verify([("a",a), ("r",order), ("N",modulus)], int(math.gcd(a**(order//2)-1,modulus) == 1))
    else:
        left, right = ("u","v") if number == 281 else ("x" if number == 396 else "a", "N")
        for a, n in [(0,0), (0,15), (-6,15), (5,6), (3,15), (14,21), (11,35)]:
            d = math.gcd(a,n)
            bindings = [(left,a), (right,n)]
            if number in (385,396):
                for proposed in (d,d+1):
                    verify(bindings + [("d",proposed)], int(proposed == d))
            else:
                verify(bindings, int(d == 1))

for value in ("1/2", "i", "[1;2]"):
    result = evaluate(f"integergcd({value},6)")
    assert result.returncode == 2 and b"exact integers" in result.stderr, (value, result.stderr)
assert len(cases) == 9
report = dict(source=inventory["source"], notebook_sha256=inventory["source_sha256"],
              worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              windows_records_sha256=hashlib.sha256(records_path.read_bytes()).hexdigest(),
              windows=windows, cases=cases, invalid_operands=["1/2", "i", "[1;2]"])
args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2)+"\n").encode())
