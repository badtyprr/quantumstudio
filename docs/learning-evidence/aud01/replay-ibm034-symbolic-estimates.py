"""Check Grover estimates independently, including exact prefix constraints."""
import json
import math
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
source = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())
rows = {r["id"][-3:]:r for r in source["rows"]}
cases = []
expected = {}


def check(name, expression, truth=None):
    p = subprocess.run([worker, "--json"], input=("quantum:"+expression).encode(), capture_output=True,
                       check=True, timeout=30, env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data")))
    result = json.loads(p.stdout)["copy_text"]
    if truth is None:
        assert result.startswith("qestimate("), (name, result)
    else:
        assert result == str(int(truth)), (name, result, truth)
    cases.append([name, expression, "0"])
    expected[name] = result
    return result


rule = {n:check("source-"+n,rows[n]["literal"]) for n in ("026","028","040")}
for n in rule:
    assert check("copy-"+n,rule[n]) == rule[n]
for t in (0,1,4,13):
    theta = f"pi/{4*t+2}"
    for shift in (-1,0,1):
        for n in ("026","028"):
            actual = f"""replace(({rule[n]}),vector('t','θ'),vector({t+shift},{theta}))"""
            residual = abs(shift) * (2*math.pi/(4*t+2) if n=="026" else 1)
            for tolerance in (0,1,4):
                check(f"{n}-{t}-{shift}-{tolerance}",f"qestimatewithin({actual},{tolerance})",residual<=tolerance)
for size,theta in [(1,"pi/2"),(2,"pi/4"),(4,"pi/6"),(16,"qasin(1/4)")]:
    residual = math.asin(1/math.sqrt(size))-1/math.sqrt(size)
    for delta in (0,1):
        actual = f"""replace(({rule["040"]}),vector('N','θ'),vector({size},{theta}+{delta}))"""
        for tolerance in (0,0.01,0.1,1):
            # The theta equality before the approximation must hold exactly.
            check(f"040-{size}-{delta}-{tolerance}", f"qestimatewithin({actual},{tolerance})",
                  delta==0 and residual<=tolerance)
for tolerance,truth in [("49/100",False),("1/2",True),("51/100",True),("pi/4",True)]:
    check("boundary-"+str(len(cases)),f"qestimatewithin(1≈(3/2),{tolerance})",truth)
if len(sys.argv)>2:
    out=Path(sys.argv[2])
    (out/"inputs.json").write_text(json.dumps(cases),encoding="utf8")
    (out/"expected.json").write_text(json.dumps(expected),encoding="utf8")
print(f"Passed {len(cases)} checks of the three source formulas and their bounds.")
