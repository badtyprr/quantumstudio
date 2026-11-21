"""Replay original scalar factors and Grover iteration-limit variables."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
base = Path(__file__).parent
cases, outputs = [], {}
def evaluate(expr, mode="scalars:"):
    p = subprocess.run([worker, "--json"], input=("quantum:"+mode+expr).encode(), capture_output=True,
                       check=True, timeout=30, env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
    value = json.loads(p.stdout)
    assert not value["approximate"]
    return value["copy_text"]

def check(name, expr, expected=None, mode="scalars:"):
    out = evaluate(expr, mode)
    if expected is not None: assert out == expected, (name, out, expected)
    assert evaluate(out, mode) == out, name
    cases.append([name, expr, "6" if mode else "0"])
    outputs[name] = out
    return out

def bind(expr, **values):
    names = ",".join("'"+name+"'" for name in values)
    entries = ",".join(str(value) for value in values.values())
    return f"replace(({expr}),vector({names}),vector({entries}))"

sources={}
for lesson, numbers in [(29,(362,363,369,374,425)),(34,range(132,139))]:
    rows=json.loads((base/f"ibm{lesson:03}-inventory.json").read_bytes())["rows"]
    for number in numbers:
        r, = [r for r in rows if r["id"].endswith(f"-M{number:03}")]
        sources[number]=check(f"ibm{lesson:03}-{number}",r["literal"])

assert sources[369]=="'c'" and sources[425]=="1"
for n in (133,135,136,138): assert sources[n]=="'T'"
for b,c in [(1,3),(2,2),(3,5),(3,1)]:
    check(f"lower-{b}-{c}",bind(sources[362],b=b,c=c),str(int(b>=2 and c>=2)))
    for extra in (0,1):
        check(f"factor-{b}-{c}-{extra}",bind(sources[363],N=b*c+extra,b=b,c=c),str(int(extra==0)))
    check(f"independent-{b}-{c}",bind(sources[374],s=b,j=c),str(int(b>=2 and c>=2)))
for t in (1,2,4):
    check(f"limit-initial-{t}", bind(sources[134],T=t),str(int(t==1)))
    check(f"limit-update-{t}", f"qstepvalue({sources[137]},{t})",str((5*t+3)//4))
for name,expr,expected in [("exponent","bc^2",18),("group","bc(b+1)",18),("function","sqrt(b^2)+c",5)]:
    check(name,bind(evaluate(expr),b=2,c=3),str(expected))
for name, expr, result in [
        ("pi-before", "πb==bπ", "1"), ("pi-factor", "2πT==2*pi*T", "1"),
        ("pi-tex", r"$\pi{}b=\pi b$", "1"), ("trailing-digit", bind(evaluate("bc2"),b=2,c=3), "12")]:
    check(name, expr, result)
for idx, original in enumerate(("bc_1", "bc_{1}")):
    expression=evaluate(original)
    check(f"indexed-{idx}", f"""replace(({expression}),vector('b',"c_1"),vector(2,3))""", "6")
check("speed-default", "c", evaluate("c",""), "")
assert outputs["speed-default"] != sources[369]
check("gate-default", "T*|0>==|0>", "1", "")
check("pauli-default","Z*|1>==(-|1>)","1","")
if len(sys.argv)>2:
    out=Path(sys.argv[2])
    (out/"inputs.json").write_text(json.dumps(cases),encoding="utf8")
    (out/"expected.json").write_text(json.dumps(outputs),encoding="utf8")
print(f"Passed {len(cases)} source and control checks.")
