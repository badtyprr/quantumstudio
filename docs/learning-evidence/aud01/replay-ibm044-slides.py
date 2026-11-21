"""Check numeric and circuit examples from the pinned Quantum Circuits lecture slides."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("slides", type=Path)
parser.add_argument("report", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
digest = hashlib.sha256(args.slides.read_bytes()).hexdigest()
assert digest == "d57bb4350afb674084faea28488bee651cd6e56d702365c195499838df115521"
checks = []


def check(pages, equation):
    run = subprocess.run([worker, "--json"], input=("quantum:" + equation).encode(), capture_output=True,
                         check=True, timeout=30, env=dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data")))
    result = json.loads(run.stdout)
    assert not result["approximate"] and result["copy_text"] == "1", (pages, equation, result["copy_text"])
    checks.append(dict(pages=pages, equation=equation))


check([2], "(1 and not 0) or ((not 1) and 0)")
check([3], "(x*x+y)*(y+1)==x^2*y+x^2+y^2+y")
check([4], "T*H*S*H*|0>==[(1+i)/2;1/sqrt(2)]")
check([5, 6, 7], "probs(SWAP*CNOT*SWAP*(I@H)*|00>)==[1/2;0;0;1/2]")
check([13, 14], "|->~*[1/2;sqrt(3)/2]==(1-sqrt(3))/(2*sqrt(2))")
check([15], "[sqrt(3)/2;-1/2]~*[1/2;sqrt(3)/2]==0")
check([10, 11, 12, 17], "[i;1]~*[1;0]==-i")
check([16], "[i;1]~*[i;1]==2")
check([18], "<0|*(i*|0>+|1>)==i")
check([19], "(i*|0>+|1>)~*|0>==-i")
check([20], "abs(<0|+>)<=1")
check([21, 22], "<+|->==0")
check([23], "<0|+>==1/sqrt(2)")
check([24, 25, 26, 27], "H~*H==I")
check([28, 29, 30, 31], "(|+><+|)*(|+><+|)==|+><+|")
check([32, 33, 34, 35, 36], "probs(|+>)==[1/2;1/2]")
# With the ancilla last in the lesson order, controlled SWAP exchanges the
# two data wires. Measuring that ancilla distinguishes their swap parity.
reverse = "((SWAP@I)*(I@SWAP)*(SWAP@I))"
test = f"(I@I@H)*{reverse}*CSWAP*{reverse}*(I@I@H)"
for sign, ancilla in [("+", "0"), ("-", "1")]:
    pair = f"((|01>{sign}|10>)/sqrt(2))"
    check([37], f"{test}*({pair}@|0>)=={pair}@|{ancilla}>")
check([38, 39, 40, 41], "probs(i*|->)==probs(|->)")
check([42], "probs(H*|->)==[0;1]")
check([43, 44, 45, 46], "CNOT*(|+>@|0>)!=(|+>@|+>)")
check([47, 48, 49, 50], "probs(H*|+>)==[1;0]")
report = dict(slides="https://ibm.box.com/public/static/zsd4694uko51kzcohdvbp6ncgl9u9ys3.pdf",
              slide_sha256=digest, reviewed_pages=50, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              checks=checks, circuit_gate_examples_on_pages_8_and_9="ibm045-figures.json",
              video="https://www.youtube.com/watch?v=30U2DTfIrOU", duration_seconds=3651,
              video_evidence="The public player lists twelve chapter starts. The English caption endpoints returned empty responses.",
              chapter_starts_seconds=[0, 66, 148, 445, 1107, 1455, 1955, 2182, 2627, 2893, 3217, 3599])
args.report.write_bytes((json.dumps(report, ensure_ascii=False, indent=2) + "\n").encode())
print(f"Verified {len(checks)} slide examples, including both swap-test ancilla outcomes.")
