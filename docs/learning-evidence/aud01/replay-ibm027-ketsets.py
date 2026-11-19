"""Verify IBM-027's indexed and explicit sets of eigenstates."""
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
source = {row["id"][-4:]: row["literal"] for row in rows}


def evaluate(body):
    result = subprocess.run([worker, "--json"], input=("quantum:" + body).encode(),
                            capture_output=True, timeout=30)
    assert result.returncode == 0, (body, result.stderr.decode())
    return json.loads(result.stdout)


def copied(body):
    return evaluate(body)["copy_text"]


def bind(body, assignments):
    for key, value in assignments:
        body = f"replace(({body}),{key},{value})"
    return body


inputs = [[r["id"], r["literal"]] for r in rows]
fixed = source["M037"].strip("$")
for key in ("M014", "M022", "M037"):
    record = evaluate(source[key])
    original = source[key].strip("$")
    for body in (original, record["display_text"], record["copy_text"]):
        assert copied(body) == record["copy_text"]
        assignments = [("ψ_1", "|+i>"), ("ψ_2", "|-i>")]
        if key != "M037":
            assignments.append(("N", "2"))
            assert copied(bind(body, [("N", "2")])) == copied(fixed)
        for order in (assignments, assignments[::-1]):
            concrete = bind(body, order)
            for probe, answer in [("|+i>", "1"), ("|-i>", "1"), ("|0>", "0")]:
                assert copied(f"qmember({probe},{concrete})") == answer
            for comparison, answer in [(r"\{|-i>,|+i>\}", "1"), (r"\{|0>,|1>\}", "0")]:
                assert copied(f"({concrete})=({comparison})") == answer
family = copied(source["M014"])
partial = evaluate(bind(family, [("ψ_1", "|+>")]))
for body in (partial["display_text"], partial["copy_text"]):
    assert copied(bind(body, [("N", "1")]) + r"=\{|+>\}") == "1"
for name, body, answer in [
        ("duplicate", bind(family, [("N", "2"), ("ψ_1", "|0>"), ("ψ_2", "|0>")]) + r"=\{|0>\}", "1"),
        ("empty", f"qmember(|0>,{bind(family, [('N', '0')])})", "0"),
        ("dimensions", r"|0> ∈ \{basis(0,3)\}", "0"),
        ("amplitudes", r"|+i> ∈ \{|-i>\}", "0"),
        ("phase", r"|0> ∈ \{-|0>\}", "0")]:
    assert copied(body) == answer
    inputs.append([f"{name}-{answer}", body])
for body in (r"\{|0>,|0>\}", r"\{basis(0,1)\}"):
    record = evaluate(body)
    assert copied(record["display_text"]) == record["copy_text"]
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified three lesson sets, membership, equality, duplicates and singleton states.")
