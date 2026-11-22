"""Check numerical examples from the 41-page IBM phase-estimation and factoring deck."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess


def checks():
    for phase, probability in (("0", Fraction(1)), ("1/4", Fraction(1, 2)), ("1/2", Fraction(0))):
        for repetitions in (1, 2):
            p = probability if repetitions == 1 else (2*probability-1)**2
            for sign, expected in (("+", p), ("-", 1-p)):
                amplitude = f"(1{sign}exp(2*pi*i*{repetitions}*({phase})))/2"
                yield "9–10", f"abs({amplitude})^2", str(expected).replace("/", " ∕ ")
    for d in (2, 3, 4, 8):
        for y in range(d):
            terms = [f"exp(2*pi*i*{x*y}/{d})*basis({x},{d})" for x in range(d)]
            column = "(" + "+".join(terms) + f")/sqrt({d})"
            yield "13–20", f"norm(fourier({d})*basis({y},{d})-({column}))", "0"
    for m in range(1, 9):
        gate_count = 1 + sum(2*k - 1 for k in range(2, m+1))
        yield "22", f"{gate_count}=({m})^2", "1"
    for a in range(1, 21):
        if math.gcd(a, 21) != 1:
            continue
        order = next(r for r in range(1, 21) if pow(a, r, 21) == 1)
        for exponent in range(1, order+1):
            yield "29–30", f"({a}^{exponent}) pmod (21)", str(pow(a, exponent, 21))
    for x in range(15):
        yield "31", f"norm(qresiduemultiplier(2,15)*basis({x},15)-basis({(2*x)%15},15))", "0"
    kets = [f"qorbitket(2,15,4,{j})" for j in range(4)]
    for j, ket in enumerate(kets):
        action = f"qresiduemultiplier(2,15)*{ket}"
        yield "33–37", f"norm({action}-i^{j}*{ket})^2", "0"
        yield "36–37 printed", f"norm({action}-i^{j}*{kets[1]})^2", "0" if j == 1 else "2"
    yield "40", "norm((" + "+".join(kets) + ")/2-basis(1,15))", "0"
    # At 23–27 minutes the promised two-bit phases are distinguished by inverse QFT.
    for j in range(4):
        amplitudes = "+".join(f"i^({x*j})*basis({x},4)" for x in range(4))
        yield "23–27 min", f"norm(fourier(4)~*(({amplitudes})/2)-basis({j},4))", "0"
    # At 62–65 minutes a sampled numerator can hide a factor of the order.
    for j in range(1, 6):
        phase = Fraction(j, 6)
        nearest = round(2048*phase)
        expected = str(phase).replace("/", " ∕ ")
        yield "62–65 min", f"recoverphase({nearest}/2048,21)", f"qset(vector({expected}))"
    yield "65 min", "lcm(3,2)", "6"
    # Repeated squaring modulo N implements every controlled power (66–69 min).
    for exponent in (1, 2, 4, 8):
        factor = pow(2, exponent, 15)
        for x in range(15):
            target = (factor*x) % 15
            yield "66–69 min", f"norm(qresiduemultiplier({factor},15)*basis({x},15)-basis({target},15))", "0"
    for n in (15, 21, 35):
        successes = 0
        for a in range(2, n):
            d = math.gcd(a,n)
            if d > 1:
                expr = f"gcd({a},{n})"
            else:
                order = next(r for r in range(1,n) if pow(a,r,n)==1)
                if order % 2:
                    continue
                d = math.gcd(pow(a,order//2,n)-1,n)
                expr = f"gcd({a}^({order//2})-1,{n})"
            yield "41", expr, str(d)
            successes += int(1 < d < n)
        if 2*successes < n-2:
            raise ValueError(f"Factoring bound failed for {n}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker", type=Path)
    parser.add_argument("slides", type=Path)
    args = parser.parse_args()
    if hashlib.sha256(args.slides.read_bytes()).hexdigest() != "a79cc94cc28ebf9efd214364ffb616796fab520abe7a22a9f920659b40ff95ab":
        raise ValueError("The lecture slides differ from the audited PDF")
    worker = args.worker.resolve()
    env = os.environ.copy()
    if (worker.parent / "data").is_dir():
        env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))

    def verify(case):
        page, expr, expected = case
        result = subprocess.run([str(worker), "--json"], input=("quantum:"+expr).encode(),
                                capture_output=True, timeout=45, env=env, check=True)
        value = json.loads(result.stdout)
        if value["approximate"] or value["copy_text"] != expected:
            raise ValueError(f"Page {page}, {expr}: expected {expected}, got {value['copy_text']}")

    examples = list(checks())
    with ThreadPoolExecutor(3) as pool:
        list(pool.map(verify, examples))
    print(f"Verified {len(examples)} lecture calculations.")


if __name__ == "__main__":
    main()
