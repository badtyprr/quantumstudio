"""Check printed Grover bounds against the full amplitude vector and independent trials."""
import argparse
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess


def search_probability(size, marked, iterations):
    # Amplitudes in units of 1/sqrt(size) allow exact rational arithmetic.
    state = [Fraction(1)] * size
    for _ in range(iterations):
        phased = [-a if i < marked else a for i, a in enumerate(state)]
        mean = sum(phased) / size
        state = [2 * mean - a for a in phased]
    assert sum(a*a for a in state) == size
    return sum((a*a for a in state[:marked]), Fraction(0)) / size


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker", type=Path)
    worker = parser.parse_args().worker.resolve()
    env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
    inventory = json.loads(Path(__file__).with_name("ibm034-inventory.json").read_bytes())

    def evaluate(expression, approximate=False):
        command = [worker, "--json"]
        if approximate:
            command.append("--approx")
        result = subprocess.run(command, input=("quantum:" + expression).encode(),
                                check=True, capture_output=True, env=env, timeout=30)
        return json.loads(result.stdout)["copy_text"]

    copies = {}
    checks = {}
    for index in (60, 69, 73, 74, 76, 97, 106):
        row = inventory["rows"][index-1]
        copies[index] = evaluate(row["literal"])
        assert evaluate(copies[index]) == copies[index], row["id"]
        checks[index] = 0

    def check(index, bindings, expected):
        expression = copies[index]
        for name, value in bindings:
            expression = f"replace(({expression}),{name},{value})"
        actual = evaluate(expression)
        assert Fraction(actual.replace(" ∕ ", "/").replace("−", "-")) == expected, (
            index, bindings, expected, actual)
        checks[index] += 1

    simulations = []
    # Each iteration count is floor(pi/(4*asin(sqrt(marked/size)))).
    for size, marked, iterations in [(2,1,1), (4,1,1), (8,1,2), (16,1,3),
                                     (16,4,1), (8,4,1), (16,12,0), (8,8,0)]:
        probability = search_probability(size, marked, iterations)
        simulations.append(dict(size=size, marked=marked, iterations=iterations,
                                probability=str(probability)))
        fraction = Fraction(marked, size)
        bounds = [(97, 1-fraction), (106, fraction)]
        if marked == 1:
            bounds.extend([(60, Fraction(1,2)), (74, 1-fraction)])
            for trials in (1, 2, 5):
                failure = (1-probability)**trials
                conservative = Fraction(1,2)**trials
                sharper = Fraction(1,size)**trials
                assert failure <= sharper <= conservative
                check(69, [("'m'", trials)], conservative)
                check(73, [("'m'", trials)], 1-conservative)
                check(76, [("'N'", size), ("'m'", trials)], 1-sharper)
        for index, threshold in bounds:
            call = "qprobabilitycall('N',1)" if index in (60,74) else "qprobabilitycall('N','s')"
            assert probability >= threshold
            for value in dict.fromkeys([probability, threshold, threshold-Fraction(1,64)]):
                if value < 0:
                    continue
                check(index, [(call, value), ("'N'", size), ("'s'", marked)], value >= threshold)
    schedule = inventory["rows"][119]
    assert schedule["id"].endswith("-M120")
    membership = evaluate(schedule["literal"])
    assert evaluate(membership) == membership
    randomized = []
    for size, upper in [(2, 1), (4, 1), (8, 2), (16, 3), (32, 4)]:
        bound = f"replace(({membership}),'N',{size})"
        for iteration in range(-1, upper+3):
            actual = evaluate(f"replace(({bound}),'t',{iteration})")
            assert actual == str(int(1 <= iteration <= upper)), (size, iteration, actual)

        failures = []
        for marked in range(size+1):
            trials = range(1, upper+1)
            probability = sum(search_probability(size, marked, t) for t in trials)/upper
            angle = f"asin(sqrt({marked}/{size}))"
            terms = "+".join(f"sin({2*t+1}*{angle})^2" for t in trials)
            value = evaluate(f"({terms})/{upper}", approximate=True)
            observed = Fraction(value.replace(" ∕ ", "/"))
            assert abs(observed-probability) < Fraction(1, 10**28), (size, marked, observed)
            if marked and probability <= Fraction(2, 5):
                failures.append(dict(marked=marked, probability=str(probability)))
        randomized.append(dict(size=size, upper=upper, marked_counts=size+1,
                               failures_of_strict_bound=failures))
    assert dict(marked=3, probability="0") in randomized[1]["failures_of_strict_bound"]
    print(json.dumps(dict(source=inventory["source"], source_sha256=inventory["source_sha256"],
                          worker_sha256=hashlib.sha256(worker.read_bytes()).hexdigest(),
                          simulations=simulations, randomized_schedule=randomized, checks_by_occurrence=checks,
                          copy_reentries=len(copies)), indent=2))


if __name__ == "__main__":
    main()
