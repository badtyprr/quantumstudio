"""Replay finite order-finding and splitting examples from the Shor notebook panels."""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
import json
from math import gcd
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
worker = args.package.resolve() / "quantum-worker.exe"
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())
assert inventory["worker_sha256"] == hashlib.sha256(worker.read_bytes()).hexdigest()
assert [p["title"] for p in inventory["panels"]][::2] == [
    "Order finding", "Probabilistic algorithm to split an odd, composite integer N that is not a prime power"]


@lru_cache(maxsize=4096)
def integer(text):
    proc = subprocess.run([worker, "--json"], input=("quantum:"+text).encode(), env=env,
                          capture_output=True, check=True, timeout=30)
    value = json.loads(proc.stdout)
    assert not value["approximate"], text
    return int(value["copy_text"])


def check_row(number, bindings, truth):
    row = inventory["rows"][number-1]
    if number in (388, 399):
        # Unquoted c in these two inputs evaluates to the speed of light.
        # Quote the cofactor name, also when substituting its proposed value.
        text = row["literal"].strip("$").replace("c", '"c"', 1)
        bindings = [('"c"' if name == "c" else name, value) for name, value in bindings]
    else:
        text = row["copy"]
    for label, value in bindings:
        text = f"replace(({text}),{label},({value}))"
    assert integer(text) == int(truth), (row["id"], bindings, truth)


cases = []
for n in (15,21,35):
    for a in range(2,n):
        d = integer(rf"\gcd({a},{n})")
        assert d == gcd(a,n)
        check_row(384, [("a",a),("N",n)], True)
        check_row(385, [("a",a),("N",n),("d",d)], True)
        check_row(386, [("d",d)], d > 1)
        case = dict(N=n, a=a)
        if d > 1:
            route = "initial gcd"
        else:
            # Supply the order by finite enumeration for this panel test.
            # Compare every modular power to an independent modular computation.
            for r in range(1,n):
                residue = integer(f"{a}^{r} pmod ({n})")
                assert residue == pow(a,r,n)
                if residue == 1:
                    break
            else:
                raise AssertionError((a,n))
            case["order"] = r
            if r % 2:
                route = "odd order"
            else:
                half_power = integer(f"{a}^{r//2} pmod ({n})")
                x = (half_power-1) % n
                d = integer(rf"\gcd({x},{n})")
                assert d == gcd(pow(a,r//2,n)-1,n)
                check_row(396, [("x",x),("N",n),("d",d)], True)
                check_row(397, [("d",d)], d > 1)
                route = "even order factor" if d > 1 else "trivial gcd"
                case["x"] = x
        case["outcome"] = route
        if d > 1:
            cofactor = integer(f"{n}/{d}")
            assert 1 < d < n and 1 < cofactor < n and d*cofactor == n
            first = route == "initial gcd"
            check_row(387 if first else 398, [("b",d),("d",d)], True)
            check_row(388 if first else 399, [("c",cofactor),("N",n),("d",d)], True)
            case["factors"] = [d,cofactor]
        cases.append(case)
outcomes = Counter(row["outcome"] for row in cases)
assert set(outcomes) == {"initial gcd", "even order factor", "odd order", "trivial gcd"}
report = dict(source=inventory["source"], worker_sha256=inventory["worker_sha256"], cases=cases, outcomes=outcomes,
              adaptations={"M388": '"c" = N/d', "M399": '"c" = N/d'},
              order_method="Finite enumeration of modular powers")
args.output.write_bytes((json.dumps(report, ensure_ascii=False, indent=2)+"\n").encode())
