"""Check the four symbolic matrices in the Grover rotation derivation."""
from argparse import ArgumentParser
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess

parser = ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--windows",type=Path,required=True)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
source = json.loads(Path(__file__).with_name("ibm033-inventory.json").read_bytes())


def evaluate(expression):
    raw = subprocess.run([worker,"--json"],input=("quantum:"+expression).encode(),env=env,
                         capture_output=True,check=True,timeout=60)
    return json.loads(raw.stdout)


indexes = (76,80,81,82)
inputs = [[source["rows"][i-1]["id"],source["rows"][i-1]["literal"],"0"] for i in indexes]
assert json.loads((args.windows/"inputs.json").read_bytes()) == inputs
suite = json.loads((args.windows/"result.json").read_bytes())
raw = (args.windows/"records.json").read_bytes()
records = json.loads(raw)
assert suite["passed"] and suite["clipboardRestored"] and suite["calls"] == len(records) == len(inputs)
results = []
for index,gui in zip(indexes,records):
    row = source["rows"][index-1]
    assert row["id"].endswith(f"M{index:03}") and row["status"] == "diagnostic"
    assert row["id"] == gui["id"] and gui["restored_same"] and gui["label"] == gui["reentry_label"] == "EXACT RESULT"
    saved = json.loads((args.windows/(row["id"]+".qsession")).read_text(encoding="utf-8-sig"))
    assert saved["Expression"] == row["literal"] and saved["Mode"] == 0
    checks = 0
    for marked,theta in [(1,"pi/6"),(2,"pi/4"),(3,"pi/3")]:
        for sign in (1,-1):
            # Build each expected matrix independently as a rotation by an angle.
            angle = f"({sign}*{theta})"
            rotation = f"[cos({angle}),-sin({angle});sin({angle}),cos({angle})]"
            for form in ("copy","second_copy","display"):
                expr = gui[form]
                for variable,value in [('qbars("A_0")',4-marked),('qbars("A_1")',marked),('N',4)]:
                    expr = f"replace(({expr}),{variable},{value})"
                if index in (76,80):
                    expr = f"replace(({expr}),M,({rotation})^2)"
                elif index == 81:
                    expr = f"({expr})=({rotation})"
                else:
                    expr = f'replace(({expr}),"θ",{angle})'
                observed = evaluate(expr)
                assert observed["copy_text"] == str(int(sign==1)), (index,marked,sign,form,observed["copy_text"])
                checks += 1
    results.append(dict(id=row["id"],substitutions=checks,copy=gui["copy"],second_copy=gui["second_copy"],display=gui["display"]))

print(json.dumps(dict(source_sha256=source["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
                      application_sha256=sha256((worker.parent/'QuantumStudio.exe').read_bytes()).hexdigest(),
                      suite=suite,records_sha256=sha256(raw).hexdigest(),cases=results),indent=2,ensure_ascii=False))
