"""Compare Shor register widths and precision choices with integer bit lengths."""
import argparse
from decimal import Decimal
from functools import lru_cache
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("directory", type=Path)
parser.add_argument("--report", type=Path)
args = parser.parse_args()
worker = args.package.resolve() / "quantum-worker.exe"
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())
assert inventory["worker_sha256"] == sha256(worker.read_bytes()).hexdigest()
rows = {int(r["id"][-3:]):r for r in inventory["rows"]}
numbers = (83,136,138,147,257,258,379)
inputs = [[rows[i]["id"], rows[i]["literal"], "0"] for i in numbers]
inputs += [[rows[136]["id"]+"-base-two", rows[136]["literal"].replace(r"\log(",r"\log_{2}("), "0"],
           [rows[379]["id"]+"-exponent-limit", r"$\lfloor\log_{2}(N)\rfloor$", "0"]]
directory = args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()

records_path = directory/"records.json"
records = json.loads(records_path.read_bytes())
suite = json.loads((directory/"result.json").read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and len(records) == len(inputs) == suite["calls"]
assert json.loads((directory/"inputs.json").read_bytes()) == inputs
forms = {}
for (key,expression,_),record in zip(inputs,records):
    assert record["id"] == key and record["restored_same"]
    assert record["label"] == record["reentry_label"] == "EXACT RESULT", key
    saved = json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Expression"] == expression and saved["Mode"] == 0 and not saved["Matrices"]
    forms[key] = {record[field] for field in ("copy","second_copy")}


@lru_cache(maxsize=4096)
def copied(expression):
    result = subprocess.run([worker,"--json"], input=("quantum:"+expression).encode(),
                            env=env, capture_output=True, timeout=30)
    assert result.returncode == 0, (expression,result.stderr)
    value = json.loads(result.stdout)
    assert not value["approximate"],expression
    return value["copy_text"]


counts, mismatches = {}, []
def check(i, bindings, expected, variant="", floor=False):
    key = rows[i]["id"]+variant
    for text in forms[key]:
        for name,value in bindings.items():
            symbol = name if name == "n" else f"'{name}'"
            text = f"replace(({text}),{symbol},{value})"
        if floor:
            text = f"floor({text})"
        actual = copied(text)
        assert actual == str(int(expected)), (key,bindings,expected,actual)
    counts[key] = counts.get(key,0)+1


moduli = sorted({21, *(2**k+d for k in (1,2,3,4,5,8,16,32,53) for d in (-1,0,1) if 2**k+d>=2)})
for modulus in moduli:
    width = (modulus-1).bit_length()
    digits = modulus.bit_length()
    natural_width = int(Decimal(modulus-1).ln())+1
    check(83, {"N":modulus},digits)
    check(147, {"N":modulus,"n":width}, 2**width-modulus)
    check(379, {"N":modulus},digits-1,"-exponent-limit")
    check(379, {"N":modulus},int(Decimal(modulus).ln()),floor=True)
    for n in (width,width+1):
        values = {"N":modulus,"n":n}
        check(136, values,n==width==natural_width)
        check(136, values,n==width,"-base-two")
        check(138, values,n==width==5)
    for m in (2*digits-1,2*digits,2*digits+1):
        values = {"N":modulus,"m":m}
        check(257,values,m==2*digits+1)
        check(258,values,m==2*digits)
    if natural_width != width:
        mismatches.append(dict(N=modulus,binary_width=width,natural_log_formula=natural_width))

report = dict(source=inventory["source"],notebook_sha256=inventory["source_sha256"],
              worker_sha256=inventory["worker_sha256"], records_sha256=sha256(records_path.read_bytes()).hexdigest(),
              windows_inputs=inputs,moduli=moduli,checks=counts,original_M136_disagreements=mismatches)
args.report.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print(sum(counts.values()), "reference cases;",len(mismatches),"original register-width disagreements")
