"""Check IBM-034's state-action and projected-amplitude identities by direct iteration."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
inventory = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())
gui = []
expected = {}
def run(expr):
    p = subprocess.run([worker, "--json"], input=("quantum:"+expr).encode(), check=True, capture_output=True,
                       timeout=30, env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
    result=json.loads(p.stdout)
    assert not result["approximate"]
    return result["copy_text"]

def ket(size, indices):
    return "["+";".join(str(int(i in indices)) for i in range(size))+f"]/sqrt({len(indices)})"

rules = {}
for number in (9,11):
    row, = [r for r in inventory["rows"] if r["id"].endswith(f"-M{number:03}")]
    key=f"original-{number}"
    rules[number] = run(row["literal"])
    assert run(rules[number])==rules[number]
    gui.append([key,row["literal"],"0"])
    expected[key]=rules[number]

checks=0
for size, marked, angle in [(2,{1},"pi/4"),(4,{0},"pi/6"),(4,{1,3},"pi/4"),
                            (4,{0,2,3},"pi/3"),(8,{1,4},"pi/6")]:
    universe=set(range(size))
    theta=math.asin(math.sqrt(len(marked)/size))
    for variant in ("source","opposite-sign","one-wrong-phase"):
        oracle=marked if variant!="one-wrong-phase" else marked.symmetric_difference({0})
        sign=-1 if variant=="opposite-sign" else 1
        entries=[f"{sign*(2-size*int(i==j))*(-1 if j in oracle else 1)}/{size}"
                 for i in range(size) for j in range(size)]
        gate=f"matrix({size},{size},[{','.join(entries)}])"
        state=[1/math.sqrt(size)]*size
        for turns in range(4):
            target=[math.sin((2*turns+1)*theta)/math.sqrt(len(marked)) if i in marked else
                    math.cos((2*turns+1)*theta)/math.sqrt(size-len(marked)) for i in range(size)]
            full_match=all(abs(a-b)<1e-10 for a,b in zip(state,target))
            overlap=sum(state[i] for i in marked)/math.sqrt(len(marked))
            projected_match=abs(overlap-math.sin((2*turns+1)*theta))<1e-10
            for number, matches in [(9,full_match),(11,projected_match)]:
                names=["G","qketstate('u')",'qnamedket("A_1")',"'t'","'θ'"]
                values=[gate,ket(size,universe),ket(size,marked),str(turns),angle]
                if number==9:
                    names.append('qnamedket("A_0")')
                    values.append(ket(size,universe-marked))
                expr=f"replace(({rules[number]}),vector({','.join(names)}),vector({','.join(values)}))"
                actual=run(expr)
                assert actual==str(int(matches)), (number,size,marked,turns,variant,actual,matches)
                checks+=1
                if size==4 and len(marked)==3 and turns in (1,3):
                    key=f"{number}-{variant}-{turns}"
                    gui.append([key,expr,"0"])
                    expected[key]=actual
            phased=[-value if i in oracle else value for i,value in enumerate(state)]
            mean=sum(phased)/size
            state=[sign*(2*mean-value) for value in phased]
assert checks==120
if len(sys.argv)>2:
    out=Path(sys.argv[2])
    (out/"inputs.json").write_text(json.dumps(gui),encoding="utf8")
    (out/"expected.json").write_text(json.dumps(expected),encoding="utf8")
print(f"Passed {checks} finite state and amplitude checks.")
