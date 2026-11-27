"""Verify computational-cost notation against the pinned IBM-024 inputs."""
from fractions import Fraction
import itertools
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

# For a sum of pure powers, weighted AM-GM proves exactly the cases
# sum(a_i / b_i) <= 1. Above that boundary, set each x_i=t^(L/b_i)
# with L a common multiple of the b_i to obtain an integer counterexample.
for names, degrees in [(("n", "m"), (3, 6)), (("m", "k"), (6, 3)), (("n", "m", "k"), (2, 3, 6))]:
    bound = "+".join(f"{v}^{b}" for v, b in zip(names, degrees))
    for powers in itertools.product(range(4), repeat=len(names)):
        monomial = "*".join(f"{v}^{a}" for v, a in zip(names, powers))
        expected = sum(Fraction(a, b) for a, b in zip(powers, degrees)) <= 1
        probe = f"{monomial}=O({bound})"
        assert evaluate(probe)["copy_text"] == str(int(expected)), probe

for probe, answer in [
    ("n^2=O(n*m)", "0"), ("n*m+n^2=O(n*m)", "0"),
    ("(n+m)^2=O(n^2+m^2)", "1"), ("3*n*m/7=O(n^2+m^2)", "1"),
    ("n^2*m^2!=O(n^3+m^3)", "1"), ("n*m*k=O(n^2*m+m*k^2)", "1"),
    ("n*m*k=O(n^2*m+m*k)", "0"), ("n*m=O(0)", "0"), ("0=O(n*m)", "1"),
    ("n^1000001*m^999999=O(n^2000000+m^2000000)", "1"),
    ("n^1000001*m^1000000=O(n^2000000+m^2000000)", "0"),
]:
    assert evaluate(probe)["copy_text"] == answer, probe
for probe in ("n*m=O(n^2-m^2)", "n*m=O(n^c+m)", "n*m=O(n^2+bitlength(m))"):
    assert "qbigorder(" in evaluate(probe)["copy_text"], probe

# Substitute two-variable costs into the lesson's actual growth definition.
definition = evaluate(spans["M074"])
for body in (spans["M074"].strip("$"), definition["display_text"], definition["copy_text"]):
    for cost, answer in (("n*m", "1"), ("n^2*m", "0")):
        probe = f"replace(replace(({body}),g(n,m),{cost}),h(n,m),n^2+m^2)"
        assert evaluate(probe)["copy_text"] == answer, probe

# The scalar applications in the prose and in the gate-count definition
# keep the same argument lists as the applications inside the Big-O bounds.
for number in ("M032", "M035", "M061", "M062", "M068", "M070", "M071"):
    literal = spans[number]
    original = evaluate(literal)
    application = literal.strip("$").strip()
    assert "qcostcall(" in original["copy_text"]
    for body in (application, original["display_text"], original["copy_text"]):
        assert evaluate(body)["copy_text"] == original["copy_text"]
        assert evaluate(f"replace(({body}),{application},17)")["copy_text"] == "17"
definition = spans["M042"].strip("$").strip().rstrip(".")
record = evaluate(spans["M042"])
for body in (definition, record["display_text"], record["copy_text"]):
    for cost in ("21*n-11", "9*n-5"):
        for supplied in (31, 73):
            probe = f"replace(replace(replace(({body}),t(n),{cost}),size(C_n),{supplied}),n,4)"
            expected = (73 if cost.startswith("21") else 31) == supplied
            assert evaluate(probe)["copy_text"] == str(int(expected)), probe

# Before assigning costs, an application of unknown g or h must retain every
# argument. Supply two possible costs that give opposite answers.
for number, args in [("M063", "n"), ("M074", "n,m")]:
    source_body = spans[number].strip("$").strip()
    result = evaluate(spans[number])
    for body in (source_body, result["display_text"], result["copy_text"]):
        for cost, answer in (("n", "1"), ("n^3", "0")):
            probe = f"replace(replace(({body}),g({args}),{cost}),h({args}),n^2)"
            assert evaluate(probe)["copy_text"] == answer, probe

# Each standalone positivity condition refers to the lesson's free coefficient.
for number in ("M064", "M075", "M160"):
    witness = spans[number].strip("$").strip()
    record = evaluate(spans[number])
    for body in (witness, record["display_text"], record["copy_text"]):
        for c in (-2, 0, 2):
            assert evaluate(f"replace(({body}),c,{c})")["copy_text"] == str(int(c > 0))
for number, args in [("M066", "n"), ("M077", "n,m")]:
    witness = spans[number].strip("$").strip()
    original = evaluate(spans[number])
    bound = evaluate(f"cost({witness})")["copy_text"]
    assert original["copy_text"] == evaluate(original["display_text"])["copy_text"] == bound
    for body in (witness, original["display_text"], bound):
        for a in (5, 6, 7):
            probe = f"replace(replace(replace(({body}),g({args}),{a}),h({args}),3),c,2)"
            assert evaluate(probe)["copy_text"] == str(int(a <= 6)), probe

# Check the lesson's defining equation as entered and after Copy.
definition = spans["M007"].strip("$").strip()
copied_definition = evaluate(spans["M007"])["copy_text"]
assert evaluate(copied_definition)["copy_text"] == copied_definition
for n in (0, 1, 2, 3, 4, 7, 8, 15, 16, 17, 2**64 - 1, 2**64):
    digits = str(max(1, n.bit_length()))
    assert evaluate(spans["M006"].replace("(N)", f"({n})"))["copy_text"] == digits
    for body in (definition, copied_definition):
        assert evaluate(f"replace(({body}),N,{n})")["copy_text"] == "1", (n, body)

# Compare exact values of the growth expressions (not just their spelling).
for number, expected in [("M099", 240), ("M116", 1200)]:
    term = spans[number].strip("$").strip()
    assert term.startswith("O(") and term.endswith(")")
    body = term[2:-1]
    probe = f"cost(replace(({body}),n,16))"
    # At n=16, the binary length is 5 and the binary length of 5 is 3.
    assert evaluate(probe)["copy_text"] == str(expected), probe

# Compare the original multiplication costs without replacing the input size.
short, long = [spans[key].strip("$")[2:-1] for key in ("M099", "M116")]
for left, right, answer in [(short, long, 1), (long, short, 0), (long, long, 1)]:
    assert evaluate(f"{left}=O({right})")["copy_text"] == str(answer)

for cost, bound, answer in [
    ("bitlength(n)^100", "n^(1/2)", 1),
    ("n^(1/2)", "bitlength(n)^100", 0),
    ("bitlength(bitlength(n))^100", "bitlength(n)^(1/2)", 1),
    ("n+bitlength(n)^3", "n", 1),
    ("bitlength(n)", "bitlength(bitlength(n))", 0),
    ("0", "bitlength(n)", 1), ("bitlength(n)", "0", 0),
]:
    assert evaluate(f"{cost}=O({bound})")["copy_text"] == str(answer)
    assert evaluate(f"{cost}!=O({bound})")["copy_text"] == str(1-answer)
for cost, bound in [("bitlength(n)", "bitlength(m)"), ("n", "n-bitlength(n)")]:
    assert "qbigorder(" in evaluate(f"{cost}=O({bound})")["copy_text"]

print("Verified polynomial and bit-length bounds, source costs, formal functions and cost witnesses.")
