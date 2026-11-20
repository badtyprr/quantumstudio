"""Exercise Shor's perfect-power preprocessing with exact integer reference bounds."""
import argparse
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
assert sha256(worker.read_bytes()).hexdigest() == inventory["worker_sha256"]


def expressions(n):
    root = f"floor(root({n},x))"
    bounds = f",2,floor(log2({n})),1,x,1)"
    return [f"if({n}<4,[],genvector({operand}{bounds})" for operand in (root, f"{root}^x={n}")]


samples = (2,3,4,21,27,63,64,65,81,127)
inputs = [[f"N{n}-{kind}",expr,"0"] for n in samples for kind,expr in enumerate(expressions(n))]
directory = args.directory
if not args.report:
    directory.mkdir(parents=True,exist_ok=True)
    (directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()


def values(key, expr):
    proc = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,
                          timeout=90,capture_output=True)
    assert proc.returncode==0, (key,proc.stderr)
    result = json.loads(proc.stdout)
    assert not result["approximate"], key
    copied = result["copy_text"]
    if copied == "vector()":
        return []
    if copied.isdecimal():
        return [int(copied)]
    assert copied.startswith("vector(") and copied.endswith(")"), (key,copied)
    return [int(entry) for entry in copied[7:-1].split(",")]


def verify(n, roots, flags):
    limit = n.bit_length()-1
    assert len(roots)==len(flags)==limit-1
    hits = []
    for j,(s,flag) in enumerate(zip(roots,flags),2):
        assert s**j <= n < (s+1)**j and s >= 2, (n,s,j)
        assert flag == int(s**j==n), (n,s,j,flag)
        if flag:
            hits.append([s,j])
    assert 2**(limit+1)>n
    return hits


suite = json.loads((directory/"result.json").read_bytes())
records_path = directory/"records.json"
records = json.loads(records_path.read_bytes())
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"]==len(records)==len(inputs)
assert json.loads((directory/"inputs.json").read_bytes())==inputs
for (key,expr,_),record in zip(inputs,records):
    assert record["id"]==key and record["restored_same"] and record["label"]==record["reentry_label"]=="EXACT RESULT"
    session=json.loads((directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert session["Expression"]==expr and session["Mode"]==0 and not session["Matrices"]
    observed = values(key,expr)
    for form in {record["copy"],record["second_copy"]}:
        assert values(key,form)==observed

moduli = sorted(set(range(2,130)) | {p+d for p in (3**5,2**8,11**3,3**20,2**53,5**24) for d in (-1,0,1)})
solutions = {}
for n in moduli:
    roots,flags = (values(n,expr) for expr in expressions(n))
    hits = verify(n,roots,flags)
    if hits:
        solutions[str(n)] = hits

report = dict(source=inventory["source"],notebook_sha256=inventory["source_sha256"],
              worker_sha256=inventory["worker_sha256"],records_sha256=sha256(records_path.read_bytes()).hexdigest(),
              source_ids=[373,374,375,376,377,378,379],windows_inputs=inputs,moduli=moduli,
              exponents_checked=sum(n.bit_length()-2 for n in moduli),solutions=solutions)
args.report.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print(len(moduli),"integers,",report["exponents_checked"],"candidate exponents,",len(solutions),"perfect powers")
