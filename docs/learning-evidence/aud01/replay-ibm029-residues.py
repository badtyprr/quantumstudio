"""Replay Shor's residue sets and membership predicates against independently enumerated sets."""
import argparse
from functools import lru_cache
import hashlib
import json
from math import gcd
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("windows_directory", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
worker = (args.package / "quantum-worker.exe").resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())
rows = [r for r in inventory["rows"] if r"\mathbb{Z}" in r["literal"] and
        int(r["id"][-3:]) not in (37,61,176,178,180)]
inputs = [[r["id"], r["literal"], "0"] for r in rows]
directory = args.windows_directory
if not args.report:
    directory.mkdir(parents=True, exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs, ensure_ascii=False).encode())
    raise SystemExit()
records = json.loads((directory/"records.json").read_bytes())
suite = json.loads((directory/"result.json").read_bytes())
assert suite["clipboardRestored"] and suite["passed"] and suite["calls"] == len(records) == len(inputs)
assert json.loads((directory/"inputs.json").read_bytes()) == inputs


@lru_cache(maxsize=4096)
def run(text):
    return subprocess.run([worker, "--json"], input=("quantum:"+text).encode(), env=env,
                          timeout=30, capture_output=True)


def exact(text):
    proc = run(text)
    assert proc.returncode == 0, (text, proc.stderr)
    result = json.loads(proc.stdout)
    assert not result["approximate"]
    return result["copy_text"]


report = []
for row, gui in zip(rows, records):
    key = row["id"]
    assert gui["id"] == key and gui["restored_same"] and gui["label"] == gui["reentry_label"] == "EXACT RESULT"
    saved = json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Expression"] == row["literal"]
    forms = {k: gui[k] for k in ("display", "copy", "second_copy")}
    n = int(key[-3:])
    cases = []
    for modulus in (1,2,6,7,21):
        binds = [("N",modulus)] if "_N" in row["literal"] else []
        if not binds:
            if n in (4,5,6,33,43):
                cases = [([],None,1)]
                break
            fixed = {14:7,20:7,21:6,46:21,139:21}[n]
            if modulus != fixed:
                continue
        units = r"\ast" in row["literal"]
        if n in (3,27):
            cases.append((binds,None,1))
        elif r"\in" in row["literal"]:
            name = "b" if n == 79 else "a"
            for candidate in sorted({-1,0,1,2,modulus-1,modulus,modulus+1}):
                member = 0 <= candidate < modulus and (not units or gcd(candidate,modulus)==1)
                cases.append((binds+[(name,candidate)],None,int(member)))
        else:
            members = [i for i in range(modulus) if not units or gcd(i,modulus)==1]
            for elements, truth in [(members,1), (members+[modulus],0)]:
                cases.append((binds,r"\{"+",".join(map(str,elements))+r"\}",truth))
    assert cases, key
    for form in forms.values():
        for bindings, reference, expected in cases:
            text = form
            for label, value in bindings:
                text = f"replace(({text}),{label},{value})"
            if reference is not None:
                text = f"(({text}) = ({reference}))"
            assert exact(text) == str(expected), (key, form, bindings, reference, expected)
    report.append(dict(id=key, forms=forms, cases=cases))

# Deliberately alter the published unit-group definitions.
controls = {}
for number, original, changed in [(27, "= 1", "= 2"), (33, "5", "3"), (43, "19,20", "19")]:
    literal = inventory["rows"][number-1]["literal"]
    assert literal.count(original) == 1
    altered = literal.replace(original,changed)
    result = exact(altered)
    if number == 27:
        result = exact(f"replace(({result}),N,6)")
    assert result == "0", (number,result)
    controls[f"M{number:03d}"] = dict(input=altered, modulus=6 if number == 27 else None, expected=0)

# Large moduli must allow point membership without allocating every residue.
for candidate in (0,1,3,10**30-1,10**30):
    for name in ("residues", "invertible_residues"):
        ok = candidate < 10**30 and (name=="residues" or gcd(candidate,10**30)==1)
        assert exact(f"{candidate} ∈ {name}(10^30)") == str(int(ok))
for invalid in ("0","-2","1/2"):
    assert run(f"residues({invalid})").returncode == 2
result = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              rows=report, rejected_definitions=controls, large_modulus="10^30", invalid_moduli=["0","-2","1/2"])
args.report.write_bytes((json.dumps(result,ensure_ascii=False,indent=2)+"\n").encode())
