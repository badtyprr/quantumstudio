"""Check two- and three-register partial traces in IBM-005 against independent reductions."""
from fractions import Fraction
import argparse
import hashlib
import json
from pathlib import Path
import os
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("source_root", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
manifest = json.loads(Path(__file__).with_name("deferred-named-trace.json").read_bytes())
lesson = next(entry for entry in manifest["lessons"] if entry["lesson"] == "IBM-005")
notebook = (args.source_root / lesson["source"]).read_bytes()
if hashlib.sha256(notebook).hexdigest() != lesson["source_sha256"]:
    raise ValueError("Use the pinned IBM-005 notebook at " + manifest["revision"])
cells = json.loads(notebook)["cells"]
worker = args.worker.resolve()
env = os.environ.copy()
if (worker.parent / "data").is_dir():
    env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))

def copied(expression):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                         env=env, timeout=30, check=True, capture_output=True)
    return json.loads(run.stdout)["copy_text"]

def verify(expression, expected):
    actual = copied(expression)
    if actual != expected:
        raise ValueError((expression, expected, actual))

def source_at(start):
    row = next(item for item in lesson["occurrences"] if item["start"] == start)
    text = "".join(cells[row["cell"]]["source"])[start:row["end"]]
    if hashlib.sha256(text.encode()).hexdigest() != row["literal_sha256"]:
        raise ValueError(f"Source literal changed at {start}")
    return text

# Off-diagonal entries distinguish extracting blocks from summing the wrong rows.
# Density matrix of the normalized pure state (1, 2, 3, 4) / sqrt(30).
matrix = "([1,2,3,4;2,4,6,8;3,6,9,12;4,8,12,16]/30)"
aligned_two = source_at(13816).split(r"\begin{aligned}")[1].split(r"\end{aligned}")[0].split(r"\\[2mm]")
if len(aligned_two) != 2:
    raise ValueError("Expected two named marginals in the two-register derivation")
for idx, (start, identity, domain, expected) in enumerate([
        (12921, "I_A", "Γ", "matrix(2,2,[1 ∕ 6,11 ∕ 30,11 ∕ 30,5 ∕ 6])"),
        (13259, "I_B", "Σ", "matrix(2,2,[1 ∕ 3,7 ∕ 15,7 ∕ 15,2 ∕ 3])")]):
    definition = source_at(start).strip().removeprefix("$$").removesuffix("$$").strip().removesuffix(".")
    name, trace, contraction = aligned_two[idx].split("=")
    verify(f'replace(({name.replace("&", "")}),"ρ_{identity[-1]}",{expected})', expected)
    for left, right in (definition.split("="), (trace, contraction)):
        mapped = f"subsystems({matrix},[A,B],[2,2])"
        verify(f"replace(({left}),ρ,{mapped})", expected)
        for product in (right, copied(right)):
            bound = f'replace(replace(replace(({product}),ρ,{matrix}),"{identity}",I),{domain},qset(vector(0,1)))'
            verify(bound, expected)

# The pure state with amplitudes (1,...,8) / sqrt(204) has coherences across
# all three registers. Compute each retained entry by summing matching axes.

def density_entry(r, c):
    return (r + 1) * (c + 1)

def fraction_text(value):
    return str(value).replace("/", " ∕ ")

matrix = "([" + ";".join(",".join(str(density_entry(r, c)) for c in range(8)) for r in range(8)) + "]/204)"
mapped = f"subsystems({matrix},[A,B,C],[2,2,2])"
aligned = source_at(14832).split(r"\begin{aligned}")[1].split(r"\end{aligned}")[0]
lines = aligned.split(r"\\[2mm]")
if len(lines) != 2:
    raise ValueError("Expected two reductions in the three-register derivation")
for line, size in zip(lines, (4, 2)):
    _, left, right = line.split("=")
    # Retain A,C in the first line and just C in the second.
    def basis(remaining, traced):
        if size == 4:
            return (remaining // 2) * 4 + 2 * traced + remaining % 2
        return traced * 2 + remaining

    entries = [Fraction(sum(density_entry(basis(r, t), basis(c, t)) for t in range(8 // size)), 204)
               for r in range(size) for c in range(size)]
    expected = f"matrix({size},{size},[" + ",".join(map(fraction_text, entries)) + "])"
    for trace in (left, copied(left)):
        verify(f"replace(({trace}),ρ,{mapped})", expected)
    for product in (right, copied(right)):
        body = f'replace(replace(replace(({product}),ρ,{matrix}),"I_A",I),"I_C",I)'
        verify(f"replace(replace({body},Γ,qset(vector(0,1))),Σ,qset(vector(0,1)))", expected)
# The lesson mixes |00> and |1+> with equal weights. Supply both the
# joint state and the proposed marginal to exercise each complete equality.
mixture = "([2,0,0,0;0,0,0,0;0,0,1,1;0,0,1,1]/4)"
for start, axis, marginal in [(16764, "A", "(I/2)"), (17185, "B", "([3,1;1,1]/4)")]:
    formula = source_at(start).strip().strip("$").strip()
    for form in (formula, copied(formula)):
        joint = f"replace(({form}),ρ,subsystems({mixture},[A,B],[2,2]))"
        for proposal, expected in [(marginal, "1"), ("X", "0")]:
            verify(f'replace(({joint}),"ρ_{axis}",{proposal})', expected)
print("All four trace definitions and both worked marginal equations passed.")
