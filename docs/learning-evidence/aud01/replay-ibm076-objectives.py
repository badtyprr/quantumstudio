"""Compare the lesson objectives against independent enumeration of all assignments."""
from pathlib import Path
import itertools
import json
import os
import subprocess
import sys

worker=Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,check=True)
    return json.loads(p.stdout)["copy_text"]

def matrix(rows):
    return "matrix(%d,%d,[%s])"%(len(rows),len(rows[0]),",".join(str(x) for row in rows for x in row))

source=json.loads(Path(__file__).with_name("ibm076-inventory.json").read_bytes())["rows"]
maximize,minimize,qubo=[run(source[i-1]["literal"]) for i in (1,8,9)]
for width,edges in [(2,[(0,1)]),(3,[(0,1),(1,2),(2,0)]),(4,[(0,1),(1,2),(2,3),(3,0)]),(3,[(0,0),(1,2),(1,2)])]:
    assignments=list(itertools.product(range(2),repeat=width))
    cost=max(sum(x[u]!=x[v] for u,v in edges) for x in assignments)
    for obj,sign in ((maximize,1),(minimize,-1)):
        expr=obj.replace("'E'",matrix(edges)).replace('n)',f'{width})')
        assert run(f"({expr})==({sign*cost})")=="1",(edges,expr)
for q in [((-1,2),(0,-3)),((1,0),(0,1)),((2,-1,0),(3,-2,1),(0,2,-1))]:
    width=len(q)
    optimum=min(sum(q[i][j]*x[i]*x[j] for i in range(width) for j in range(width))
                for x in itertools.product(range(2),repeat=width))
    expr=qubo.replace("'Q'",matrix(q)).replace('n)',f'{width})')
    assert run(f"({expr})==({optimum})")=="1",(q,expr)
assert run("qmaxcut(vector(),3)")=="0" and run("qbinaryminimum(vector(),0)")=="0"
print("Verified MaxCut, its negation, asymmetric quadratic matrices, and empty inputs.")
