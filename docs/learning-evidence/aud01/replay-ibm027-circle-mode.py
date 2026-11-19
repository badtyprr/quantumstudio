"""Verify both readings of the original S^1 in IBM-027, including session inputs."""
import argparse
import json
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
parser.add_argument("--gui-inputs", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
rows = json.loads(Path(__file__).with_name("ibm027-inventory.json").read_bytes())["lessons"][1]["rows"]
literal = next(row["literal"] for row in rows if row["id"].endswith("M063"))


def evaluate(body, sets=False):
    prefix = "quantum:sets:" if sets else "quantum:"
    p = subprocess.run([worker, "--json"], input=(prefix + body).encode(), capture_output=True, timeout=30)
    assert p.returncode == 0, (body, p.stderr.decode())
    return json.loads(p.stdout)


gate = evaluate("S")["copy_text"]
circle = evaluate(r"\mathbb{T}")["copy_text"]
inputs = [[row["id"], row["literal"], "2" if row["id"].endswith("M063") else "0"] for row in rows]
inputs.append(["operator-reading", literal, "0"])
for body in (literal, "S¹", r"\(S^{1}\)", "( S ) ^ (1)"):
    for sets, expected in [(False, gate), (True, circle)]:
        result = evaluate(body, sets)
        assert result["copy_text"] == expected
        assert evaluate(result["copy_text"])["copy_text"] == expected
for name, body, expected in [
        ("inside", r"i ∈ S^1", "1"), ("outside", r"0 ∈ S^1", "0"),
        ("same-circle", r"S^1=\mathbb{T}", "1"), ("other-domain", r"S^1=\mathbb{C}", "0"),
        ("gate-power", "S^2|1> = -|1>", "1"), ("explicit-matrix", "matrix(2,2,[1,0,0,i])^1=S", "1")]:
    assert evaluate(body, True)["copy_text"] == expected, body
    inputs.append([f"{name}-{expected}", body, "2"])
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified the original circle name and the phase gate in their respective modes.")
