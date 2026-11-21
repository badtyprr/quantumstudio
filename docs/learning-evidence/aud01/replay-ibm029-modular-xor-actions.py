"""Replay the printed modular register operations against integer permutation tables."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
if not __debug__:
    raise RuntimeError("Assertions must be enabled.")
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))

def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:"+expression).encode(),
                            env=env, capture_output=True, check=True, timeout=30)
    return json.loads(result.stdout)["copy_text"]

def ket(index, dimension):
    if dimension >= 1024:
        return f"qbasis({index},{dimension})"
    entries = ["0"] * dimension
    entries[index] = "1"
    return f"matrix({dimension},1,[" + ",".join(entries) + "])"

def action(left, right):
    return f"qstateaction({left},{right})"

rows = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
forms = [evaluate("modpowers:" + rows[i-1]["literal"]) for i in (152,157,162)]
counts = [0,0,0]
for n, modulus, a in ((3,5,2),(4,15,2),(5,21,2),(6,61,3)):
    d = 1 << n
    images = [a*x % modulus if x < modulus else x for x in range(d)]
    inverse = [images.index(x) for x in range(d)]
    xs = range(d) if n <= 5 else (0,1,modulus-1,modulus,d-1)
    for x in xs:
        fx = images[x]
        for op, mapping in enumerate((images,inverse)):
            for y in (range(d) if n == 3 else (x,)):
                expr = forms[op]
                for key,value in (("a",a),("N",modulus),("n",n),("x",x),("y",y)):
                    expr = f'replace(({expr}),"{key}",{value})'
                basis = lambda hi,lo: ket(d*hi+lo,d*d)
                assert evaluate(expr) == action(basis(x,y),basis(x,y^mapping[x])), (op,n,x,y)
                counts[op] += 1
        expr = forms[2]
        for key,value in (("x",x),("n",n),("N",modulus),("a",a)):
            expr = f'replace(({expr}),"{key}",{value})'
        states = [ket(i,d*d) for i in (x*d,x*d+fx,fx*d+x,fx*d)]
        expected = "vector("+",".join(action(u,v) for u,v in zip(states,states[1:]))+",1)"
        assert evaluate(expr) == expected, (n,x)
        if x in (0,1): assert evaluate(expected) == expected
        counts[2] += 1
print(json.dumps(dict(source_spans=[152,157,162],forward_actions=counts[0],
                      inverse_actions=counts[1],three_step_traces=counts[2]), indent=2))
