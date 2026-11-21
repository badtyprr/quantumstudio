"""Check gate injection and the threshold recurrence using exact worker results."""
import json
import os
from pathlib import Path
import subprocess
import sys

worker=Path(sys.argv[1]).resolve()
directory=Path(sys.argv[2]) if len(sys.argv)>2 else Path(__file__).parent
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def evaluate(expression):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),capture_output=True,env=env,timeout=35)
    assert p.returncode==0,(expression,p.stderr.decode())
    return json.loads(p.stdout)["copy_text"]
def rows(n):
    return json.loads((directory/f"ibm{n}-inventory.json").read_bytes())["rows"]

mapping=rows("067")[41]["copy"]
assert "qnamedket('Ïˆ')" in mapping
for probe in ("|0>","|1>","|+>","|+i>"):
    assert evaluate(mapping.replace("qnamedket('Ïˆ')",probe))=="1"
# The conditional S correction works for every input because S T† = T.
assert evaluate("qcompare(qmul(S,qdag(T)),T,4)")=="1"
print("Verified magic-state injection for both basis inputs and two phase-sensitive superpositions.")

threshold=rows("068")
for row in (25,26,27):
    assert threshold[row-1]["copy"]=="1",(row,threshold[row-1]["copy"])
condition=threshold[23]["copy"]
for probability,expected in [("1/1000","1"),("1/100","0"),("1/20","0")]:
    expr=condition.replace("'C'","100").replace('"p_th"',"(1/100)").replace("'p'",f"({probability})")
    assert evaluate(expr)==expected,(probability,expr)
for level in range(5):
    expr=threshold[28]["copy"].replace("'C'","100").replace("'p'","(1/1000)").replace("'k'",str(level))
    assert evaluate(f"({expr})==(1/(100*10^{2**level}))")=="1"
print("Verified all three probability identities, the strict threshold, and five concatenation levels.")
