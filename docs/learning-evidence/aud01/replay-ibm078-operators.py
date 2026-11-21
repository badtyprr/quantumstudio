"""Verify both printed Jordan-Wigner conventions one wire at a time."""
import json
from pathlib import Path
import os
import subprocess
import sys
worker=Path(sys.argv[1]).resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(expr):
    p=subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),env=env,capture_output=True,check=True)
    return json.loads(p.stdout)["copy_text"]
for width in (1,2,3):
    for site in range(width):
        for create,ladder in [(0,"matrix(2,2,[0,1,0,0])"),(1,"matrix(2,2,[0,0,1,0])")]:
            gates=["(-Z)"]*site+[ladder]+["I"]*(width-site-1)
            matrix=gates[0]
            for gate in gates[1:]:
                matrix=f"qtensor({matrix},{gate})"
            assert run(f"qcompare(qjwimage({width},{site},{create}),{matrix},4)")=="1",(width,site,create)
print("Verified 12 signed Jordan-Wigner matrices across one, two and three wires.")

def source(n,row):
    data=json.loads(Path(__file__).with_name(f"ibm{n:03}-inventory.json").read_bytes())
    return run(data["rows"][row-1]["literal"])
assert source(78,50)=="vector(1,1,1,1)"
for row,selector in [(20,0),(22,1)]:
    equation=source(79,row)
    assert f"qjwimage('N','j',{selector})" in equation
mapping=source(78,29).split(r"\\qcompare")
assert len(mapping)==2 and "qjwimage('N','j',1)" in mapping[0] and "qjwimage('N','j',0)" in mapping[1]

steps=[0,1,0,2,3]
for start,end in ((1,5),(2,4),(3,3)):
    delta=source(78,14).replace('"steps"',"vector(0,1,0,2,3)").replace("'i'",str(start)).replace("'j'",str(end))
    counts=[sum((-1)**k for k in range(start,end+1) if steps[k-1]==axis) for axis in range(4)]
    for axis,count in enumerate(counts):
        assert run(delta.replace("'a'",str(axis)))=="1"
        assert run(f"qwalkdelta(vector(0,1,0,2,3),{axis},{start},{end})==({count})")=="1"
    distance=source(78,21).replace('"steps"',"vector(0,1,0,2,3)").replace("'i'",str(start)).replace("'j'",str(end))
    assert run(distance)=="1"
    assert run(f"qwalkdistance(vector(0,1,0,2,3),{start},{end})")==str(sum(c*c for c in counts))
print("Verified all four signed coordinate counts and squared distances for three segments.")

for width in (1,2,3):
    for site in range(width):
        for source_row,ladder in [(58,"matrix(2,2,[0,0,1,0])"),(60,"matrix(2,2,[0,1,0,0])")]:
            expression=source(78,source_row).replace("'N'",str(width)).replace("'k'",str(site))
            gates=["I"]*site+[ladder]+["I"]*(width-site-1)
            expected=gates[0]
            for gate in gates[1:]:
                expected=f"qtensor({expected},{gate})"
            assert run(f"qcompare({expression},{expected},4)")=="1"
occupation=source(78,44)
correct=occupation.replace('qketstate("empty")',"|0>").replace('qketstate("occupied")',"|1>")
wrong=occupation.replace('qketstate("empty")',"|1>").replace('qketstate("occupied")',"|0>")
assert run(correct)==r"\begin{gathered}1\\1\end{gathered}"
assert run(wrong)==r"\begin{gathered}0\\0\end{gathered}"
print("Verified all indexed ladder actions and both assignments of the occupation labels.")

assert source(78,63)=="matrix(2,2,[0,0,0,1])"
for row in (64,65,66):
    assert source(78,row)=="1"
for width in (1,2,3):
    projector="matrix(2,2,[0,0,0,1])"
    for spectator in range(1,width):
        projector=f"qtensor({projector},I)"
    occupation=f"qmul(qfcreate({width},0),qfdestroy({width},0))"
    assert run(f"qcompare({occupation},{projector},4)")=="1"
print("Verified the mode-zero occupation derivation with up to two spectator wires.")
