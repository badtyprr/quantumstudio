"""Verify finite Shor modular predicates, permutations and reversible register updates."""
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
cases = []


def case(key, ids, expression, expected):
    cases.append((key, ids, expression, expected))


def residue(a, n, x):
    return a*x % n if x < n else x


def operation(gate, wires):
    return f"apply({gate},s_0,[{','.join(map(str,wires))}])"


def oracle(a, n, width):
    # Compute f(x) on the first register, XOR its bits into the second, then undo it.
    wires = range(width)
    return ([operation(f"modmul({a},{n})",wires)] +
            [operation("CNOT",[i,i+width]) for i in wires] +
            [operation(f"modmul({pow(a,-1,n)},{n})",wires)])


def sequence(operations, initial, dimension):
    return f"sequence([{','.join(operations)}],basis({initial},{dimension}),s_0)"


case("inverse-mod-seven", [18], "mod(3*5,7)=mod(1,7)", 1)
for n,a,order in ((5,2,4),(7,3,6),(15,2,4),(21,2,6)):
    for r in (order,order-1):
        case(f"order-{n}-{r}", [51,52,427], f"mod({a}^{r},{n})=1", int(pow(a,r,n)==1))
    half = pow(a,order//2,n)
    case(f"neighbors-{n}", [424], f"[mod({a}^({order}/2)-1,{n});mod({a}^({order}/2)+1,{n})]",
         [(half-1)%n,(half+1)%n])
    width = (n-1).bit_length()
    size = 2**width
    for multiplier in sorted({a,pow(a,-1,n)}):
        case(f"permutation-{n}-{multiplier}", [141,144,153], f"modmul({multiplier},{n})",
             {"permutation":[residue(multiplier,n,x) for x in range(size)]})

n,a,width = 5,2,3
size = 2**width
forward = oracle(a,n,width)
swaps = [operation("SWAP",[i,i+width]) for i in range(width)]
inverse = oracle(pow(a,-1,n),n,width)
for x in range(size):
    fx = residue(a,n,x)
    for y in range(size):
        case(f"xor-{x}-{y}", [152,153], sequence(forward,x*size+y,size**2), {"basis": x*size+(y^fx)})
        ix = residue(pow(a,-1,n),n,x)
        case(f"inverse-{x}-{y}", [157], sequence(inverse,x*size+y,size**2), {"basis": x*size+(y^ix)})
    for name,ops,expected in (("compute",forward,x*size+fx),
                              ("swap",forward+swaps,fx*size+x),
                              ("uncompute",forward+swaps+inverse,fx*size)):
        case(f"{name}-{x}", [162], sequence(ops,x*size,size**2), {"basis":expected})

# Replay each scalar and single-register matrix, then representative two-register
# states covering a moved residue and an out-of-domain fixed point.
windows = [c for c in cases if c[0].split("-")[0] not in ("xor","inverse","compute","swap","uncompute")
           or c[0] in ("inverse-mod-seven","xor-3-6","inverse-3-6","compute-3","swap-3","uncompute-3","uncompute-7")]
inputs = [[key,expr,"0"] for key,_,expr,_ in windows]
if not args.report:
    args.directory.mkdir(parents=True,exist_ok=True)
    (args.directory/"inputs.json").write_bytes(json.dumps(inputs).encode())
    raise SystemExit()


def verify(key, text, expected):
    proc = subprocess.run([worker,"--json"],input=("quantum:"+text).encode(),capture_output=True,env=env,timeout=60)
    assert proc.returncode == 0, (key,proc.stderr.decode())
    value = json.loads(proc.stdout)
    assert not value["approximate"], key
    if isinstance(expected,int):
        assert value["copy_text"] == str(expected), key
        return
    # The worker omits cell previews for large matrices. Verify the complete serialization.
    if isinstance(expected,list):
        wanted = [[str(k)] for k in expected]
    elif "basis" in expected:
        wanted = [[str(int(k == expected["basis"]))] for k in range(size**2)]
    else:
        perm = expected["permutation"]
        assert sorted(perm)==list(range(len(perm)))
        wanted = [[str(int(j==dest)) for dest in perm] for j in range(len(perm))]
    rows, cols = len(wanted), len(wanted[0])
    entries = ",".join(k for row in wanted for k in row)
    assert (value["rows"],value["columns"]) == (rows,cols), key
    assert value["copy_text"] == f"matrix({rows},{cols},[{entries}])", key


records_path = args.directory/"records.json"
records = json.loads(records_path.read_bytes())
suite = json.loads((args.directory/"result.json").read_bytes())
assert json.loads((args.directory/"inputs.json").read_bytes()) == inputs
assert suite["passed"] and suite["clipboardRestored"] and len(records)==suite["calls"]==len(inputs)
for (key,_,expr,expected),record in zip(windows,records):
    assert record["id"]==key and record["restored_same"]
    assert record["label"]==record["reentry_label"]=="EXACT RESULT",key
    saved=json.loads((args.directory/(key+".qsession")).read_bytes().decode("utf-8-sig"))
    assert saved["Expression"]==expr and saved["Mode"]==0 and not saved["Matrices"]
    for form in {record["copy"],record["second_copy"]}:
        verify(key,form,expected)
for key,_,expr,expected in cases:
    verify(key,expr,expected)
report = dict(source=inventory["source"], notebook_sha256=inventory["source_sha256"],
              worker_sha256=inventory["worker_sha256"], records_sha256=sha256(records_path.read_bytes()).hexdigest(),
              windows=[c[0] for c in windows], cases=[dict(key=k,source_ids=ids,expected=e) for k,ids,_,e in cases])
args.report.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print(len(cases),"reference cases and",len(windows),"Windows inputs passed")
