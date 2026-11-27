"""Replay the probability, query-count and adaptive-search examples on slides 20 and 27–29."""
import argparse
from fractions import Fraction
from functools import lru_cache
import hashlib
import json
import math
import os
from pathlib import Path
import random
import subprocess

if not __debug__:
    raise RuntimeError("This replay requires assertions enabled.")

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("slides", type=Path)
parser.add_argument("worker", type=Path)
args = parser.parse_args()
digest = hashlib.sha256(args.slides.read_bytes()).hexdigest()
assert digest == "02be18ffcd56ac5b9d4bd43a69180ac1330f285fc8dfc30ed5559142d04091c1"
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))


@lru_cache(maxsize=None)
def number(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            env=env, capture_output=True, check=True, timeout=30)
    value = json.loads(result.stdout)
    assert not value["approximate"], expression
    return Fraction(value["copy_text"].replace(" ∕ ", "/").replace("−", "-"))


def column(entries):
    return "[" + ";".join(map(str, entries)) + "]"


word_checks = 0
for mask in range(1, 15):
    selected = [(mask >> i) & 1 for i in range(4)]
    marked = sum(selected)
    a = column([1 - bit for bit in selected]) + f"/sqrt({4-marked})"
    b = column(selected) + f"/sqrt({marked})"
    for alpha, beta, beta_squared in (("3*i/5", "4/5", Fraction(16, 25)),
                                     ("(1+i)/2", "(1-i)/2", Fraction(1, 2))):
        state = f"(({alpha})*{a}+({beta})*{b})"
        probabilities = [number(f"abs(element({state},{i+1},1))^2") for i in range(4)]
        for bit, probability in zip(selected, probabilities):
            expected = beta_squared / marked if bit else (1 - beta_squared) / (4 - marked)
            assert probability == expected
            word_checks += 1
        assert sum(probabilities) == 1
        assert sum(p for bit, p in zip(selected, probabilities) if bit) == beta_squared


bound_checks = 0
for width in range(1, 7):
    size = 2**width
    for marked in range(1, size + 1):
        theta = f"asin(sqrt({marked}/{size}))"
        iterations = number(f"floor(pi/(4*{theta}))")
        assert iterations.denominator == 1
        assert 0 <= iterations <= math.pi/4 * math.sqrt(size / marked)
        # Starting amplitudes scaled by sqrt(N). Each iterate phases the
        # marked class, then reflects both classes about their common mean.
        a = b = Fraction(1)
        for _ in range(int(iterations)):
            mean = ((size - marked)*a - marked*b) / size
            a, b = 2*mean - a, 2*mean + b
        success = marked * b*b / size
        assert success >= max(Fraction(marked, size), 1 - Fraction(marked, size))
        bound_checks += 1


@lru_cache(maxsize=None)
def measurement_weights(mask, iterations):
    # The query phases each marked input; diffusion signs the diagonal of
    # the all-ones matrix, then divides by two in this four-word example.
    signs = [1 - 2*((mask >> i) & 1) for i in range(4)]
    matrix = "[" + ";".join(",".join(str(signs[j] * (-1 if i == j else 1))
                                      for j in range(4)) for i in range(4)) + "]/2"
    state = f"(({matrix})^{iterations})*[1;1;1;1]/2"
    probabilities = [number(f"abs(element(({state}),{i+1},1))^2") for i in range(4)]
    assert sum(probabilities) == 1
    denominator = math.lcm(*(p.denominator for p in probabilities))
    return [int(p * denominator) for p in probabilities]


def adaptive_search(mask, trials, rng):
    # The lecture leaves termination after unsuccessful trials unspecified.
    # Use a finite test budget and distinguish exhaustion from proof of absence.
    limit = 1
    trace = []
    for _ in range(trials):
        iterations = rng.randint(1, limit)
        weights = measurement_weights(mask, iterations)
        ticket = rng.randrange(sum(weights))
        cumulative = 0
        for word, weight in enumerate(weights):
            cumulative += weight
            if ticket < cumulative:
                break
        trace.append([limit, iterations, word])
        if mask & (1 << word):
            return word, trace
        limit = int(number(f"ceil(5*{limit}/4)"))
    return None, trace


traces = []
for mask in range(16):
    word, trace = adaptive_search(mask, 8, random.Random(200 + mask))
    for i, (limit, iterations, measured) in enumerate(trace):
        assert limit == (1 if i == 0 else (5*trace[i-1][0] + 3)//4)
        assert 1 <= iterations <= limit
        assert bool(mask & (1 << measured)) == (word is not None and i == len(trace)-1)
    if word is None:
        assert len(trace) == 8
    if mask == 0:
        assert word is None
    if mask == 15:
        assert len(trace) == 1 and word is not None
    traces.append(dict(marked_mask=mask, verified_word=word, trials=trace))
assert all(t["verified_word"] is not None for t in traces[1:])
assert sum(len(t["trials"]) > 1 for t in traces[1:]) == 9
print(json.dumps(dict(slides_sha256=digest, worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                      per_word_checks=word_checks, bound_cases=bound_checks, adaptive_traces=traces), indent=2))
