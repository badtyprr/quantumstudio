"""Compare the four register-labelled teleportation formulas with an independent circuit trace."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("inventory", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
rows = json.loads(args.inventory.read_bytes())["rows"]


def evaluate(expr):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expr).encode(), capture_output=True, env=env, timeout=30)
    assert run.returncode == 0, run.stderr.decode()
    result = json.loads(run.stdout)
    assert not result["approximate"]
    return result["copy_text"]


def column(cells):
    return "[" + ";".join(cells) + "]"


for dimension in (2, 3):
    before = ["0"] * (2*dimension)
    bell, controlled, measured = (["0"] * (8*dimension) for _ in range(3))
    for q in (0, 1):
        r = dimension-1 if q == 0 else 0
        phase = "1" if q == 0 else "i"
        before[q*dimension+r] = phase + "/sqrt(2)"
        for b in (0, 1):
            bell[((b*2+b)*2+q)*dimension+r] = phase + "/2"
            a = b ^ q
            controlled[((b*dimension+r)*2+a)*2+q] = phase + "/2"
            for output in (0, 1):
                sign = "-" if q and output else ""
                measured[((b*dimension+r)*2+a)*2+output] = sign + phase + "/(2*sqrt(2))"
    for number, expected in [(128,before), (139,bell), (140,controlled), (141,measured)]:
        expr = evaluate(rows[number-1]["literal"])
        bindings = [('qnamedket("γ_0")', column(["0"]*(dimension-1)+["1"])),
                    ('qnamedket("γ_1")', column(["1"]+["0"]*(dimension-1))),
                    ('"α"', "1/sqrt(2)"), ('"β"', "i/sqrt(2)")]
        for name, value in bindings:
            expr = f"replace(({expr}),{name},{value})"
        if number == 128:
            assert evaluate(f"({expr})=={column(expected)}") == "1"
        else:
            state = f'qketstate("pi_{number-139}")'
            assert evaluate(f"replace(({expr}),{state},{column(expected)})") == "1"
            assert evaluate(f"replace(({expr}),{state},-{column(expected)})") == "0"
print("Verified labelled register order before and after both teleportation gates with two reference-system dimensions.")
