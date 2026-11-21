"""Check the readout-twirling table, including operators printed in separate math spans."""
import hashlib
import json
import os
import re
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

notebook, worker, output = map(Path, sys.argv[1:])
inventory = json.loads(Path(__file__).with_name("ibm083-inventory.json").read_bytes())
data = notebook.read_bytes()
assert hashlib.sha256(data).hexdigest() == inventory["source_sha256"]
cells = json.loads(data)["cells"]
worker = worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def calculate(expression):
    p = subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),env=env,capture_output=True,check=True)
    return json.loads(p.stdout)["copy_text"]

outcomes = [Fraction(), Fraction()]
seen = set()
factors = []
for cell_number,cell in enumerate(cells):
    if cell["cell_type"]!="markdown":
        continue
    text = "".join(cell["source"])
    for line in re.finditer(r"^\| [IX] \| [01] \| [01] \|.*$",text,re.M):
        gate, initial, sent, error, undo, final, probability = (s.strip() for s in line.group().strip("|").split("|"))
        assert undo == gate and (gate,initial,error) not in seen
        seen.add((gate,initial,error))
        toggled = int(gate=="X")
        assert int(sent) == int(initial)^toggled
        received = int(sent)^int(error!="None")
        if error!="None":
            assert error==rf"${sent} \rightarrow {received}$"
        assert int(final)==received^toggled
        rates = re.fullmatch(r"(\d+)\\% \$\\times\$ (\d+)\\% \$\\times\$ (\d+)% = ([\d.]+)\\%",probability)
        assert rates
        a,b,c,published = (Fraction(s)/100 for s in rates.groups())
        expected_error = Fraction(1 if sent=="0" else 10,100)
        assert a==b==Fraction(1,2) and c==(expected_error if error!="None" else 1-expected_error)
        assert a*b*c==published
        assert calculate(f"({a})*({b})*({c})==({published})")=="1"
        outcomes[int(final)] += published
        ids = [r["id"] for r in inventory["rows"] if r["cell"]==cell_number and line.start()<=r["start"]<line.end()
               and r["literal"]==r"$\times$"]
        assert len(ids)==2
        factors.append(dict(spans=ids,gate=gate,initial=int(initial),received=received,final=int(final),probability=str(published)))
assert len(seen)==8 and outcomes==[Fraction(1,2)]*2
report = dict(source_sha256=inventory["source_sha256"],worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              rows=factors,reported_probabilities=list(map(str,outcomes)),z_expectation=str(outcomes[0]-outcomes[1]))
output.write_bytes((json.dumps(report,indent=2)+"\n").encode())
print("Verified 8 readout branches, 16 embedded multiplication signs and zero net Z bias.")
