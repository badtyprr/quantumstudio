"""Verify each classical image, matrix entry and padding label for the printed definitions."""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--verify-clipboard",action="store_true")
args=parser.parse_args()
worker=args.worker.resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr,success=True):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True,timeout=30)
    assert (p.returncode==0)==success,(expr[:150],p.stderr)
    return json.loads(p.stdout)["copy_text"] if success else p.stderr.decode()

rows=json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
operator, function = [rows[i-1]["literal"] for i in (144,153)]
matrix, graph = run(operator), run(function)
assert matrix=="qregistermultiplier('a','N','n')" and graph=="qregistermultipliergraph('a','N','n')"
def bind(expr,a,n,width):
    return f'replace(replace(replace(({expr}),"N",{n}),"n",{width}),"a",{a})'

cases={"M144":(operator,matrix),"M153":(function,graph)}
images=entries=graphs=operators=0
for n,width in ((3,2),(3,4),(5,3),(5,5),(6,4),(7,4),(8,3),(15,4),(21,5),(21,6)):
    dim=2**width
    for a in sorted({0,1,2,n-1}):
        outputs=[a*x%n if x<n else x for x in range(dim)]
        graph_expr=bind(graph,a,n,width)
        graph_text="qset(vector("+",".join(f"qtuple(vector({x},{v}))" for x,v in enumerate(outputs))+"))"
        assert run(graph_expr)==graph_text
        graphs+=1;images+=dim
        if (a,n,width) in ((2,6,4),(2,21,6)):
            cases[f"graph-{a}-{n}-{width}"]=(graph_expr,graph_text)
        matrix_expr=bind(matrix,a,n,width)
        if math.gcd(a,n)!=1:
            run(matrix_expr,False)
            continue
        expected=f"matrix({dim},{dim},["+",".join(str(int(y==v)) for y in range(dim) for v in outputs)+"])"
        actual=run(matrix_expr)
        assert actual==expected or actual==run(expected),(a,n,width)
        operators+=1;entries+=dim**2
        if (a,n,width) in ((2,5,5),(2,21,6)):
            cases[f"operator-{a}-{n}-{width}"]=(matrix_expr,actual)
for x in (0,1,3,5,6,15):
    app=run(f"qfiniteapply({graph},{x})")
    assert run(bind(app,2,6,4))==str(2*x%6 if x<6 else x)
run(bind(f"qfiniteapply({graph},16)",2,6,4),False)
for invalid in ("qregistermultipliergraph(a,9,3)","qregistermultiplier(2,6,n)","qregistermultipliergraph(2,N,7)"):
    run(invalid,False)
for name in ("f_a ( x )","(f_a(x))","f_a((x))"):
    assert run(function.replace("f_a(x)",name))==graph
for invalid in (function.replace("0\\leq","1\\leq"),operator.replace("ax","bx")):
    run(invalid,False)
(args.directory/"inputs.json").write_text(json.dumps([[k,e,"0"] for k,(e,_) in cases.items()]),"utf8")
if args.verify_clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records]==list(cases)
    for r in records:
        assert r["restored_same"] and r["copy"]==r["second_copy"]==cases[r["id"]][1]
    result=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert result["passed"] and result["clipboardRestored"] and not result["sessionsOnly"]
    print(json.dumps(dict(sources=[rows[i-1]["id"] for i in (144,153)],classical_graphs=graphs,
                          classical_images=images,operators=operators,matrix_entries=entries,
                          clipboard_sessions=len(cases)),indent=2))
