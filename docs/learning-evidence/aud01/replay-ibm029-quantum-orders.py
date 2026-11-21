"""Simulate modular phase estimation and verify the recovered order before splitting."""
import argparse
import cmath
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
from math import gcd, lcm, pi
import os
import random
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("package", type=Path)
parser.add_argument("output", type=Path)
args = parser.parse_args()
worker = args.package.resolve() / "quantum-worker.exe"
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
inventory = json.loads(Path(__file__).with_name("ibm029-inventory.json").read_bytes())


@lru_cache(maxsize=512)
def run(expression, approximate=False):
    command = [worker, "--json"] + (["--approx"] if approximate else [])
    proc = subprocess.run(command, input=("quantum:"+expression).encode(), env=env,
                          capture_output=True, timeout=120, check=True)
    return json.loads(proc.stdout)


def numeric(text):
    plain = text.replace(" ∕ ","/").replace("−","-")
    if "i" in plain:
        value = complex(plain.replace(" ","").replace("i","j"))
        assert abs(value.imag)<1e-14, text
        return value.real
    return float(Fraction(plain))


def integer(expression):
    value = run(expression)
    assert not value["approximate"]
    return int(value["copy_text"])


def distribution(a, n, width, approximate):
    targets = list(range(width,width+(n-1).bit_length()))
    operations = []

    def apply(gate,wires):
        operations.append(f"apply({gate},s_0,[{','.join(map(str,wires))}])")

    for wire in range(width):
        apply("H",[wire])
    for wire in range(width):
        multiplier = pow(a,2**(width-1-wire),n)
        if multiplier != 1:
            apply(f"controlled(modmul({multiplier},{n}))",[wire]+targets)
    apply(f"fourier({2**width})~",range(width))
    # Combined basis label 1 initializes the controls to zero and the target to one.
    state = f"sequence([{','.join(operations)}],basis(1,{2**(width+len(targets))}),s_0)"
    expression = f"probs({state},[{','.join(map(str,range(width)))}])"
    result = run(expression,approximate)
    assert result["rows"]==2**width and result["columns"]==1
    return expression, [cell[0] for cell in result["cells"]]


def reference(a,n,width):
    size = 2**width
    orbit = [pow(a,x,n) for x in range(size)]
    return [sum(abs(sum(cmath.exp(-2j*pi*x*y/size) for x,target in enumerate(orbit) if target==t))**2
                for t in set(orbit))/size**2 for y in range(size)]


def factor_from_order(a,n,r):
    if r%2 or integer(f"{a}^{r} pmod ({n})")!=1:
        return []
    d = integer(f"integergcd(({a}^{r//2} pmod ({n}))-1,{n})")
    return [d,n//d] if 1<d<n else []


cases = []
for a,n,width in [(2,15,3),(4,15,3),(14,15,3),(2,21,4)]:
    # For period six the off-grid measurement probabilities involve algebraic
    # numbers. Evaluate the simulator numerically and retain all sixteen cells.
    approximate = n==21
    expression,cells = distribution(a,n,width,approximate)
    expected = reference(a,n,width)
    probabilities = [numeric(c) for c in cells]
    assert all(abs(p-e)<1e-12 for p,e in zip(probabilities,expected)) and abs(sum(probabilities)-1)<1e-12
    true_order = next(r for r in range(1,n) if pow(a,r,n)==1)
    outcomes = []
    for y,p in enumerate(probabilities):
        if p<=1e-12:
            continue
        outcome = dict(y=y,probability=cells[y])
        if y:
            fractions = f"recoverphase({y}/{2**width},{n})"
            if integer(f"cardinality({fractions})"):
                candidate = integer(f"denominator(qsumset(x,{fractions},x))")
                verified = integer(f"{a}^{candidate} pmod ({n})")==1
                assert verified == (candidate%true_order==0)
                factors = factor_from_order(a,n,candidate)
                if factors:
                    assert factors[0]*factors[1]==n and min(factors)>1
                outcome.update(denominator=candidate,passes_modular_check=verified,factors=factors)
        outcomes.append(outcome)
    cases.append(dict(a=a,N=n,control_qubits=width,approximate=approximate,
                      circuit=expression,probabilities=cells,outcomes=outcomes))
    if not approximate:
        assert all(abs(p-(1/true_order if (y*true_order)%(2**width)==0 else 0))<1e-12
                   for y,p in enumerate(probabilities))
        assert bool(any(out.get("factors") for out in outcomes)) == (a!=14)
    else:
        assert next(o for o in outcomes if o["y"]==3)["denominator"]==16
        assert not any(o.get("passes_modular_check") for o in outcomes)

# Semiclassical inverse Fourier measurement reuses a single control. After
# k low bits have been measured, projecting the next control onto bit b acts
# on the target by (I + exp(-2πi*(low + b*2^k)/2^(k+1))*U^(2^(m-1-k)))/2.
# Its squared norm on the unnormalized branch state is a joint probability.
width = 10
size = 2**width
target_modulus = 21
orbit = [pow(2,x,target_modulus) for x in range(size)]
classes = [[x for x,t in enumerate(orbit) if t==target] for target in sorted(set(orbit))]
fourier_distribution = [sum(abs(sum(cmath.exp(-2j*pi*x*y/size) for x in positions))**2
                            for positions in classes)/size**2 for y in range(size)]
rng = random.Random(29)
shots = []
candidate = 1
for shot in range(3):
    low = 0
    mass = 1.0
    path = []
    for k in range(width):
        stride = 2**k
        multiplier = pow(2,2**(width-1-k),target_modulus)
        def projected_step(bit):
            phase = f"exp(-2*pi*i*{low+bit*stride}/{2*stride})"
            return f"(s_0+({phase})*(modmul({multiplier},21)*s_0))/2"
        zero = projected_step(0)
        expression = f"norm(sequence([{','.join(path+[zero])}],basis(1,32),s_0))^2"
        pzero = numeric(run(expression,True)["copy_text"])
        assert abs(pzero-sum(fourier_distribution[low::2*stride])) < 1e-12
        assert abs(mass-sum(fourier_distribution[low::stride])) < 1e-12
        bit = int(rng.random() >= pzero/mass)
        path.append(projected_step(bit) if bit else zero)
        low += bit*stride
        mass = mass-pzero if bit else pzero
    assert abs(mass-fourier_distribution[low]) < 1e-12
    measurement = dict(y=low, probability=mass)
    if low:
        fractions = f"recoverphase({low}/{size},21)"
        if integer(f"cardinality({fractions})"):
            denominator = integer(f"denominator(qsumset(x,{fractions},x))")
            candidate = lcm(candidate,denominator)
            measurement["denominator"] = denominator
    verified = integer(f"2^{candidate} pmod (21)")==1
    measurement.update(combined_candidate=candidate, passes_modular_check=verified)
    shots.append(measurement)
    if verified:
        break
assert [s["y"] for s in shots]==[341,340,854]
assert [s.get("denominator") for s in shots]==[3,None,6]
assert candidate==6 and verified
assert all(integer(f"2^{candidate//prime} pmod (21)")!=1 for prime in (2,3))
factors = factor_from_order(2,21,candidate)
assert factors==[7,3]
report = dict(source=inventory["source"],worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
              circuits=cases, semiclassical=dict(a=2,N=21,phase_bits=width,seed=29,shots=shots,factors=factors))
args.output.write_bytes((json.dumps(report,ensure_ascii=False,indent=2)+"\n").encode())
