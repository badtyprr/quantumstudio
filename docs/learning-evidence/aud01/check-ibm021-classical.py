"""Replay the strict query cutoff and Simon's collision-free transcript argument."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from itertools import combinations, permutations
import json
from math import comb, isqrt
from pathlib import Path
import subprocess


def exact(worker, expression):
    run = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                         capture_output=True, check=True, timeout=30)
    answer = json.loads(run.stdout)
    assert not answer["approximate"]
    return answer["copy_text"]


def cutoff_checks(worker, formula):
    checks = []
    for width in range(1, 33):
        size = 1 << width
        # q < sqrt(size)/2 - 1 exactly when 4*(q+1)^2 < size for q >= 0.
        last = isqrt((size - 1) // 4) - 1
        bound = f"replace(({formula}),n,{width})"
        first_excluded = max(0, last + 1)
        assert exact(worker, f"{first_excluded} < ({bound})") == "0"
        if last >= 0:
            assert exact(worker, f"{last} < ({bound})") == "1"
            assert 2 * (comb(last, 2) + 1) <= size - 1
        checks.append(last if last >= 0 else None)
    return checks


def collision_sets():
    checked = 0
    for width in range(1, 5):
        size = 1 << width
        for count in range(min(4, size) + 1):
            for queries in combinations(range(size), count):
                differences = {x ^ y for x, y in combinations(queries, 2)}
                for secret in range(1, size):
                    # Distinct pairs have distinct canonical labels. Relabeling
                    # the outputs preserves every equality in the transcript.
                    outputs = [min(x, x ^ secret) for x in queries]
                    collided = len(set(outputs)) < len(outputs)
                    assert collided == (secret in differences)
                assert len(differences) <= comb(count, 2)
                checked += 1
    return checked


def adaptive_experiment(count):
    size = 8
    frequencies = defaultdict(Counter)
    collided = 0
    for secret in range(1, size):
        pairs = sorted({min(x, x ^ secret) for x in range(size)})
        for labels in permutations(range(size), len(pairs)):
            oracle = dict(zip(pairs, labels))
            queries, outputs = [], []
            x = 0
            for _ in range(count):
                queries.append(x)
                outputs.append(oracle[min(x, x ^ secret)])
                if outputs[-1] in outputs[:-1]:
                    previous = outputs.index(outputs[-1])
                    assert queries[previous] ^ x == secret
                    collided += 1
                    break
                x = (outputs[-1] + sum(queries) + 1) % size
                while x in queries:
                    x = (x + 1) % size
            else:
                frequencies[tuple(queries), tuple(outputs)][secret] += 1
    best = collided
    total = collided
    for (queries, _), counts in frequencies.items():
        excluded = {x ^ y for x, y in combinations(queries, 2)}
        assert set(counts) == set(range(1, size)) - excluded
        assert len(set(counts.values())) == 1
        best += max(counts.values())
        total += sum(counts.values())
    assert total == 7 * 8 * 7 * 6 * 5
    probability = Fraction(best, total)
    assert probability <= Fraction(comb(count, 2) + 1, size - 1)
    return dict(queries=count, labeled_oracles=total, collision_free_transcripts=len(frequencies),
                collision_runs=collided, optimal_success_for_this_strategy=str(probability))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for arg in ("notebook", "worker", "output"):
        parser.add_argument(arg, type=Path)
    args = parser.parse_args()
    source = args.notebook.read_bytes()
    digest = sha256(source).hexdigest()
    assert digest == "2a53c7740281662c4c68fd9b3a9492c3615ea3bbfead3c0d3cce9f2fab698f7a"
    text = "".join(json.loads(source)["cells"][0]["source"]).split("### Classical difficulty")[1]
    records = json.loads(Path(__file__).with_name("ibm021-literal-results.json").read_bytes())
    bounds = [r["literal"] for r in records["results"] if r["id"] in ("IBM021-c0-M168", "IBM021-c0-M174")]
    assert len(bounds) == 2 and bounds[0] == bounds[1] and text.count(bounds[0]) == 2
    limits = cutoff_checks(args.worker, bounds[0].strip("$"))
    report = dict(source_sha256=digest, worker_sha256=sha256(args.worker.read_bytes()).hexdigest(),
                  formula=bounds[0], widths=list(range(1, 33)), largest_nonnegative_query_count=limits,
                  exhaustive_query_sets=collision_sets(), adaptive_experiments=[adaptive_experiment(q) for q in (2, 3)],
                  worst_case_argument=[
                      "Choose the nonzero secret uniformly and assign distinct, uniformly random labels to its XOR pairs. Fix the algorithm's random choices and a random stream of fresh labels. Answer repeated queries consistently. Until the first collision between distinct queries the stream determines a single path independent of the secret.",
                      "Among at most q distinct queries on that path, only their distinct pairwise XORs can cause a collision. If there are D such differences, credit success on all D secrets. Every remaining secret yields the same transcript, so the fixed final guess can succeed on at most one more. Averaging gives success at most (q(q-1)/2 + 1)/(2^n - 1).",
                      "For n <= 2 no nonnegative q meets the strict cutoff. For n >= 3, the cutoff implies (q+1)^2 < 2^n/4. Thus q(q-1)+2 <= (q+1)^2+1 < 2^n/4+1 <= 2^n-1. Average success is at most one half, so at least one promised input has failure probability at least one half for the randomized algorithm."])
    args.output.write_bytes((json.dumps(report, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()
