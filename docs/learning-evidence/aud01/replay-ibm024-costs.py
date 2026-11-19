"""Verify computational-cost notation against the pinned IBM-024 inputs."""
import json
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
source = json.loads(Path(__file__).with_name("ibm024-cost-baseline.json").read_bytes())
spans = {row["id"][-4:]: row["literal"] for row in source["rows"]}


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            check=True, capture_output=True, timeout=15)
    value = json.loads(result.stdout)
    assert not value["approximate"], expression
    return value


def polynomial(degree, numerator):
    if degree == 0:
        return f"{numerator}/3"
    return f"(({numerator}/3)*n^{degree}-93*n^{degree-1}+7)"


# For positive leading coefficients, a positive constant can bound the ratio
# eventually exactly when its numerator degree does not exceed its denominator degree.
for a in range(7):
    for b in range(7):
        probe = f"{polynomial(a, 2)}=O({polynomial(b, 5)})"
        assert evaluate(probe)["copy_text"] == str(int(a <= b)), probe
assert evaluate(spans["M069"])["copy_text"] == "1"

# Before assigning costs, an application of unknown g or h must retain every
# argument. Supply two possible costs that give opposite answers.
for number, args in [("M063", "n"), ("M074", "n,m")]:
    source_body = spans[number].strip("$").strip()
    result = evaluate(spans[number])
    for body in (source_body, result["display_text"], result["copy_text"]):
        for cost, answer in (("n", "1"), ("n^3", "0")):
            probe = f"replace(replace(({body}),g({args}),{cost}),h({args}),n^2)"
            assert evaluate(probe)["copy_text"] == answer, probe

# The lesson declares c to be an arbitrary positive real constant. Supply
# that cost context explicitly for isolated witnesses outside Big-O notation.
for number in ("M064", "M075"):
    witness = spans[number].strip("$").strip()
    for c in (-2, 0, 2):
        assert evaluate(f"cost(replace(({witness}),c,{c}))")["copy_text"] == str(int(c > 0))
for number, args in [("M066", "n"), ("M077", "n,m")]:
    witness = spans[number].strip("$").strip()
    original = evaluate(spans[number])
    bound = evaluate(f"cost({witness})")["copy_text"]
    assert original["copy_text"] == evaluate(original["display_text"])["copy_text"] == bound
    for body in (witness, original["display_text"], bound):
        for a in (5, 6, 7):
            probe = f"replace(replace(replace(({body}),g({args}),{a}),h({args}),3),c,2)"
            assert evaluate(probe)["copy_text"] == str(int(a <= 6)), probe

# Compare exact values of the growth expressions (not just their spelling).
for number, expected in [("M099", 128), ("M116", 512)]:
    term = spans[number].strip("$").strip()
    assert term.startswith("O(") and term.endswith(")")
    body = term[2:-1]
    probe = f"cost(replace(({body}),n,16))"
    # At n=16, lg(n)=4 and lg(lg(n))=2.
    assert evaluate(probe)["copy_text"] == str(expected), probe

print("Verified 49 polynomial degree pairs, the source cubic, formal functions, cost witnesses and binary logarithms.")
