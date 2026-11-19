"""Check IBM-027's definition of the unit circle and its exact membership tests."""
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
    p = subprocess.run([worker, "--json"], input=("quantum:" + body).encode(),
                       capture_output=True, timeout=30)
    assert p.returncode == 0, (body, p.returncode, p.stderr.decode())
    return json.loads(p.stdout)


def copied(body):
    return evaluate(body)["copy_text"]


circle = source["M062"].strip("$")
builder = source["M061"].strip("$").split("=", 1)[1].strip()
assert copied(source["M061"]) == "1"
assert copied("T") == copied("matrix(2,2,[1,0,0,(1+i)/sqrt(2)])")
assert copied(r"\mathbb{T}=\mathbb{C}") == "0"
assert copied(r"\mathbb{T}!=\mathbb{C}") == "1"
controls = [("one", "1", "1"), ("imaginary", "-i", "1"), ("rational", "(3+4i)/5", "1"),
            ("origin", "0", "0"), ("outside", "1+i", "0"), ("inside", "i/2", "0"),
            ("gate", "T", "0")]
inputs = [[row["id"], row["literal"]] for row in rows]
inputs.extend([[f"{name}-{answer}", f"({value}) ∈ {circle}"] for name, value, answer in controls])
for original in (circle, builder):
    record = evaluate(original)
    for domain in dict.fromkeys((original, record["copy_text"], record["display_text"])):
        assert copied(domain) == copied(circle)
        pending = copied(f"z ∈ {domain}")
        for _, value, answer in controls:
            assert copied(f"({value}) ∈ {domain}") == answer
            assert copied(f"replace(({pending}),z,({value}))") == answer
for domain in (r"\{z\in\mathbb{C}:1=|z|\}", r"\{w\in\mathbb{C}:|w|=1\}"):
    assert copied(domain) == copied(circle)
radius_two = r"\{z\in\mathbb{C}:|z|=2\}"
assert copied(f"2i ∈ {radius_two}") == "1"
assert copied(f"i ∈ {radius_two}") == "0"
free = copied(r"i ∈ \{z\in\mathbb{C}:|w|=1\}")
assert copied(f"replace(({free}),w,0)") == "0"
assert copied(f"replace(({free}),w,i)") == "1"
if args.gui_inputs:
    args.gui_inputs.write_text(json.dumps(inputs, ensure_ascii=False), encoding="utf-8")
print("Verified the unit-circle definition, ordinary T gate and seven membership controls.")
