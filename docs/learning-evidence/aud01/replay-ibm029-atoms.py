"""Audit each standalone scalar and integer occurrence in the complete Shor Windows replay."""
import argparse
from collections import defaultdict
from functools import lru_cache
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess

parser=argparse.ArgumentParser()
parser.add_argument("package",type=Path)
parser.add_argument("windows",type=Path)
parser.add_argument("output",type=Path)
args=parser.parse_args()
here=Path(__file__).parent
inventory=json.loads((here/"ibm029-inventory.json").read_bytes())
suite=json.loads((here/"ibm029-windows-unit-copy.json").read_bytes())
worker=args.package.resolve()/"quantum-worker.exe"
records_path=args.windows/"records.json"
assert sha256(worker.read_bytes()).hexdigest()==suite["worker_sha256"]
assert sha256(records_path.read_bytes()).hexdigest()==suite["records_sha256"]
records=json.loads(records_path.read_bytes())
assert len(records)==len(inventory["rows"])==438
greek={r"\theta":"θ",r"\varepsilon":"ε",r"\alpha":"α"}
variables={"N","a","r","b","n","k","m","u","v","s","t",*greek}
checked=defaultdict(list)
mismatches=[]


@lru_cache(maxsize=512)
def copied(text):
    proc=subprocess.run([worker,"--json"],input=("quantum:"+text).encode(),capture_output=True,
                        env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")),timeout=30,check=True)
    result=json.loads(proc.stdout)
    assert not result["approximate"]
    return result["copy_text"]


for row,gui in zip(inventory["rows"],records):
    assert gui["id"]==row["id"]+"-original"
    match=re.fullmatch(r"\$([0-9]+|[a-zA-Z]|\\[a-zA-Z]+)\$",row["literal"])
    if not match:
        continue
    token=match[1]
    assert gui["label"]==gui["reentry_label"]=="EXACT RESULT" and gui["restored_same"]
    for output in {gui["copy"],gui["second_copy"]}:
        if token.isdecimal():
            assert copied(output)==str(int(token))
        elif token=="c":
            assert copied(f"({output})/c")=="1" and "qphysicalunit" in output
        else:
            assert token in variables,token
            name=greek.get(token,token)
            symbol=name if name=="n" else f'"{name}"'
            values=("1/8","3/16") if token in greek else ("2","7")
            for value in values:
                assert copied(f"(replace(({output}),{symbol},({value})))=({value})")=="1", (row["id"],output)
    if token=="c":
        mismatches.append(dict(id=row["id"],expected="integer cofactor c",actual=gui["display"]))
    else:
        checked[token].append(row["id"])
report=dict(source=inventory["source"],notebook_sha256=inventory["source_sha256"],worker_sha256=suite["worker_sha256"],
            windows_records_sha256=suite["records_sha256"],checked=checked,meaning_mismatches=mismatches)
args.output.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())
print(sum(map(len,checked.values())),"matching source meanings;",len(mismatches),"mismatch")
