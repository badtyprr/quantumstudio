"""Replay the original two-span source selection and check the modular statement."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker",type=Path)
parser.add_argument("directory",type=Path)
parser.add_argument("--verify-clipboard",action="store_true")
args=parser.parse_args()
worker=args.worker.resolve()
env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
def run(s,success=True):
    p=subprocess.run([worker,"--json"],input=("quantum:"+s).encode(),env=env,capture_output=True,timeout=30)
    assert (p.returncode==0)==success,(s,p.stderr)
    return json.loads(p.stdout)["copy_text"] if success else None
rows=json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())["rows"]
left,right=rows[50:52]
assert left["end"]+1==right["start"]
source=left["literal"]+" "+right["literal"]
copy=run(source)
assert run(copy)==copy
cases={"source":(source,copy),"true":(r"$2^4\equiv1$ $(\textrm{mod } 5)$","1"),
       "false":(r"$2^4\equiv1$ $\pmod{7}$","0")}
for s,value in cases.values(): assert run(s)==value
for invalid in (left["literal"],right["literal"],left["literal"]+" and "+right["literal"]):
    run(invalid,False)
checks=0
for a in (-2,0,1,2,3,5):
    for r in (0,1,3,6,19):
        for n in (1,5,7,21):
            s=f'replace(replace(replace(({copy}),"a",({a})),"r",{r}),"N",{n})'
            assert run(s)==str(int(pow(a,r,n)==1%n)),(a,r,n)
            checks+=1
(args.directory/"inputs.json").write_text(json.dumps([[k,s,"0"] for k,(s,_) in cases.items()]),"utf8")
if args.verify_clipboard:
    records=json.loads((args.directory/"records.json").read_text("utf-8-sig"))
    assert [r["id"] for r in records]==list(cases)
    assert all(r["restored_same"] and r["copy"]==r["second_copy"]==cases[r["id"]][1] for r in records)
    result=json.loads((args.directory/"result.json").read_text("utf-8-sig"))
    assert result["passed"] and result["clipboardRestored"] and not result["sessionsOnly"]
    print(json.dumps(dict(sources=[left["id"],right["id"]],selection=source,finite_cases=checks,
                          clipboard_sessions=len(records)),indent=2))
