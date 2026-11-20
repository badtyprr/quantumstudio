"""Verify the lesson's single-control phase kickback equations on three eigenstates."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("output", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
inventory = json.loads(Path(__file__).with_name("ibm028-inventory.json").read_bytes())


def evaluate(expression):
    process = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                             capture_output=True, timeout=30)
    assert process.returncode == 0, (expression, process.stderr.decode())
    return json.loads(process.stdout)


report, inputs = [], []
for number, stage in [(14, 0), (15, 1), (17, 2), (21, 2), (22, 3)]:
    row = inventory["rows"][number - 1]
    result = evaluate(row["literal"])
    samples = []
    for gate, target, theta, kicked, wrong in [
            ("S", "|1>", "1/4", "|+i>", "|00>"),
            ("X", "|->", "1/2", "|->", "|11>"),
            ("Z", "|0>", "0", "|+>", "|11>")]:
        # The target stays in its eigenstate. The control starts at zero,
        # receives H, acquires the eigenphase, then receives a final H.
        control = ["|0>", "|+>", kicked, "(H" + kicked + ")"][stage]
        expected = f"{target} @ {control}"
        for form, text in [("display", result["display_text"]), ("copy", result["copy_text"])]:
            for state, truth in [(expected, "1"), (wrong, "0")]:
                expression = text
                bindings = [("ψ", target), (f"pi_{stage}", state)]
                if number == 17:
                    bindings.insert(1, ("U", gate))
                if number in (21, 22):
                    bindings.insert(1, ("θ", theta))
                for name, value in bindings:
                    expression = f"replace(({expression}),{name},({value}))"
                actual = evaluate(expression)["copy_text"]
                assert actual == truth, (row["id"], gate, form, expression, actual)
                if form == "display" and (number == 17 or gate == "S"):
                    inputs.append([f"{row['id']}-{gate}-{truth}", expression, "0"])
        samples.append(dict(gate=gate, target=target, phase=theta, expected_state=expected,
                            rejected_state=wrong))
    report.append(dict(id=row["id"], literal=row["literal"], display=result["display_text"],
                       copy=result["copy_text"], samples=samples))

evidence = dict(source=inventory["source"], worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                forms=["display", "copy"], rows=report)
args.output.write_bytes((json.dumps(evidence, indent=2, ensure_ascii=False) + "\n").encode())
if args.gui_inputs:
    args.gui_inputs.write_bytes(json.dumps(inputs, ensure_ascii=False).encode())
