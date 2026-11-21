"""Check Grover reflection identities after assigning explicit gates and states."""
from argparse import ArgumentParser
from fractions import Fraction
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import subprocess

parser = ArgumentParser()
parser.add_argument("worker",type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm033-inventory.json").read_bytes())


def diagonal(entries):
    return "["+";".join(",".join(str(x) if j==i else "0" for j in range(len(entries)))
                            for i,x in enumerate(entries))+"]"


def vector(entries,bra=False):
    column = "["+("," if bra else ";").join(str(x) for x in entries)+"]"
    return f"({column}/sqrt({sum(entries)}))"


def instantiate(literal,n,marked,wrong_oracle=False):
    size = 2**n
    masks = {"u":[1]*size, "0^n":[int(i==0) for i in range(size)],
             "A_0":[int(i not in marked) for i in range(size)],
             "A_1":[int(i in marked) for i in range(size)]}
    # Derive the iterate independently by reflecting about the uniform state.
    entries = []
    for i in range(size):
        entries.append(",".join(str(Fraction(2-size*int(i==j),size) * (-1 if j in marked else 1)) for j in range(size)))
    gate = "["+";".join(entries)+"]"
    oracle = diagonal([-1 if (i in marked) != wrong_oracle else 1 for i in range(size)])
    expr = literal.replace(r"Z_{\mathrm{OR}}","("+diagonal([1]+[-1]*(size-1))+")")
    expr = expr.replace(r"H^{\otimes n}",f"(tensorpow(H,{n}))").replace(r"\mathbb{I}",f"(identity({size}))")
    expr = expr.replace("Z_f","("+oracle+")").replace("G","("+gate+")")
    for label,mask in masks.items():
        expr = re.sub(r"\\vert\s*"+re.escape(label)+r"\s*\\rangle",lambda _:vector(mask),expr)
        expr = re.sub(r"\\langle\s*"+re.escape(label)+r"\s*\\vert",lambda _:vector(mask,True),expr)
        expr = re.sub(r"\\vert\s*"+re.escape(label)+r"\s*\\vert",f"({sum(mask)})",expr)
    return expr.replace("N",str(size))


results = []
for index in (56,64,67,111):
    row = inventory["rows"][index-1]
    cases = []
    for n,marked in [(2,{1}), (2,{1,3}), (3,{0,3,6})]:
        for wrong in ((False,True) if index in (64,67) else (False,)):
            expr = instantiate(row["literal"],n,marked,wrong)
            p = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,env=env,check=True,timeout=60)
            result = json.loads(p.stdout)
            assert result["copy_text"] == str(int(not wrong)) and not result["approximate"], (index,n,wrong,result["copy_text"][:160])
            cases.append(dict(qubits=n,marked=sorted(marked),inverted_oracle=wrong,equality=int(not wrong)))
    results.append(dict(id=row["id"],cases=cases))
print(json.dumps(dict(source_sha256=inventory["source_sha256"],worker_sha256=sha256(worker.read_bytes()).hexdigest(),
                      finite_identities=results),indent=2))
