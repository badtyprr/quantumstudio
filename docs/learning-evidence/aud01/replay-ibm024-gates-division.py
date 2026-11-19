"""Verify IBM-024 gate literals and the defining integer-division relations."""
from functools import lru_cache
import json
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
baseline = json.loads(Path(__file__).with_name("ibm024-cost-baseline.json").read_bytes())
source = {row["id"][-4:]: row["literal"] for row in baseline["rows"]}


def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, timeout=15, check=True)
    value = json.loads(result.stdout)
    assert not value["approximate"]
    return value["copy_text"]


@lru_cache(maxsize=None)
def forms(number):
    literal = source[number]
    return literal.strip("$").strip(), evaluate(literal)


def check(number, assignments, expected):
    for body in forms(number):
        probe = f"({body})"
        for name, value in assignments.items():
            probe = f"replace({probe},{name},{value})"
        assert evaluate(probe) == str(int(expected)), (number, assignments, expected)


matrices = {"X": "[0,1;1,0]", "Y": "[0,-i;i,0]", "Z": "[1,0;0,-1]",
            "H": "[1,1;1,-1]/sqrt(2)", "S": "[1,0;0,i]", "T": "[1,0;0,(1+i)/sqrt(2)]",
            r"S^{\dagger}": "[1,0;0,-i]", r"T^{\dagger}": "[1,0;0,(1-i)/sqrt(2)]",
            r"\vert 0\rangle": "[1;0]"}
for n in [*range(15, 21), *range(22, 32)]:
    text, copy = forms(f"M{n:03d}")
    for gate in (text, copy):
        assert evaluate(f"({gate})=({matrices[text]})") == "1", (text, gate)

# M104 uses an absolute divisor. M105 must allow positive or negative
# quotients while preserving 0 <= r < |M| in all sign combinations.
for dividend, divisor in ((23, 7), (-23, 7), (23, -7), (-23, -7), (21, 7)):
    remainder = dividend % abs(divisor)
    quotient = (dividend - remainder) // divisor
    for candidate in (remainder, abs(divisor), -1):
        check("M104", {"M": divisor, "r": candidate}, 0 <= candidate < abs(divisor))
    for candidate in (remainder, remainder + 1):
        check("M105", {"N": dividend, "M": divisor, "q": quotient, "r": candidate},
              dividend == quotient * divisor + candidate)

for base, exponent, modulus in ((3, 5, 7), (2, 0, 1), (0, 3, 11)):
    power = base**exponent
    quotient, remainder = divmod(power, modulus)
    for candidate in (remainder, modulus):
        check("M128", {"r": candidate, "M": modulus}, 0 <= candidate < modulus)
        check("M129", {"N": base, "K": exponent, "q": quotient, "M": modulus, "r": candidate},
              power == quotient * modulus + candidate)

print("Verified 16 gate and state literals and four integer-division relations in original and copied notation.")
