"""Replay the pinned Simon lesson formulas and check its oracle and probability equations."""
import argparse
from concurrent.futures import ThreadPoolExecutor
from fractions import Fraction
import hashlib
import json
import os
from pathlib import Path
import subprocess


def word(value, width):
    return f"qbitlabel({value},{width})"


def graph(values, width):
    pairs = [f"qtuple(vector({word(i, width)},{value}))" for i, value in enumerate(values)]
    return "qset(vector(" + ",".join(pairs) + "))"


def cases(copies):
    outputs = [19, 5, 5, 19, 26, 1, 1, 26]
    oracle = copies[29]
    for x, output in enumerate(outputs):
        for y, other in enumerate(outputs):
            inputs = [("f", oracle), ("x", word(x, 3)), ("y", word(y, 3))]
            for secret in (3, 5):
                promise = (output == other) == (x == y or x ^ secret == y)
                yield 7, inputs + [("s", word(secret, 3))], str(int(promise))
            yield 16, inputs, str(int((output == other) == (x == y)))
        for z in sorted(set(outputs)):
            yield 72, [("f", oracle), ("x", word(x, 3)), ("z", word(z, 5))], str(int(z == output))
    domain = [("f", oracle), ("Σ", "qset(vector(0,1))"), ("n", "3")]
    yield 56, domain, "1"
    for z in sorted({0, *outputs}):
        yield 60, domain + [("z", word(z, 5))], "1"

    for secret in (0, 3):
        oracle = graph([word(min(i, i ^ secret), 2) for i in range(4)], 2)
        weights = [Fraction(1, 4) if secret == 0 else
                   Fraction(1, 2) if (i & secret).bit_count() % 2 == 0 else Fraction(0) for i in range(4)]
        for y, weight in enumerate(weights):
            for correct in (True, False):
                # Change one reported probability for a negative equation control.
                trial = list(weights)
                if not correct:
                    trial[y] = 1 - weight if weight != Fraction(1, 2) else Fraction(1, 4)
                bindings = [("p", graph(trial, 2)), ("y", word(y, 2)), ("s", word(secret, 2)),
                            ("f", oracle), ("Σ", "qset(vector(0,1))"), ("n", "2")]
                yield 52, bindings, str(trial[y]).replace("/", " ∕ ")
                for i in (54, 70, 74, 95 if secret == 0 else 102):
                    yield i, bindings, str(int(correct))


    for secret in range(4):
        for width in (2, 3):
            outputs = [((1 << width) - 1) ^ min(i, i ^ secret) for i in range(4)]
            oracle = graph([word(output, width) for output in outputs], 2)
            bindings = [("f", oracle), ("m", str(width)), ("n", "2")]
            # The output word is the high register and the input word is the low register.
            for stage in (45, 49, 50):
                amplitudes = [Fraction(0)] * (4 << width)
                for x, output in enumerate(outputs):
                    if stage == 45:
                        amplitudes[x] += Fraction(1, 2)
                    elif stage == 49:
                        amplitudes[4 * output + x] += Fraction(1, 2)
                    else:
                        for y in range(4):
                            sign = (-1) ** (x & y).bit_count()
                            amplitudes[4 * output + y] += Fraction(sign, 4)
                entries = ",".join(str(v).replace("-", "−").replace("/", " ∕ ") for v in amplitudes)
                yield stage, bindings, f"matrix({len(amplitudes)},1,[{entries}])"

            for z in sorted(set(outputs)):
                fiber = [x for x, output in enumerate(outputs) if output == z]
                for y in range(4):
                    phase_sum = sum((-1) ** (x & y).bit_count() for x in fiber)
                    bound = [("f", oracle), ("z", word(z, width)), ("y", word(y, 2))]
                    yield 75, bound, str(phase_sum ** 2)
                    if secret:
                        yield 88, bound + [("w", word(fiber[0], 2)), ("s", word(secret, 2))], "1"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker", type=Path)
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()
    data = args.notebook.read_bytes()
    if hashlib.sha256(data).hexdigest() != "2a53c7740281662c4c68fd9b3a9492c3615ea3bbfead3c0d3cce9f2fab698f7a":
        raise ValueError("Simon notebook differs from the audited revision")
    cells = json.loads(data)["cells"]
    worker = args.worker.resolve()
    env = os.environ.copy()
    if (worker.parent / "data").is_dir():
        env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))

    def evaluate(expr):
        result = subprocess.run([str(worker), "--json"], input=("quantum:" + expr).encode(),
                                timeout=60, env=env, capture_output=True, check=True)
        value = json.loads(result.stdout)
        if value["approximate"]:
            raise ValueError(f"Expected exact evaluation for {expr}")
        return value["copy_text"]

    ledger = Path(__file__).with_name("ibm021-formula-audit.jsonl")
    rows = [json.loads(line) for line in ledger.read_bytes().splitlines()]
    if [i for row in rows for i in range(row["first"], row["last"] + 1)] != list(range(1, 178)):
        raise ValueError("Incomplete source occurrence inventory")

    def replay(row):
        source = "".join(cells[row["cell"]]["source"])[row["start"]:row["end"]]
        copy = evaluate(row["mode"] + source)
        if copy != row["copy"] or evaluate(row["mode"] + copy) != copy:
            raise ValueError(f"M{row['first']:03} changed on replay")
        return row["first"], copy

    with ThreadPoolExecutor(3) as pool:
        copies = dict(pool.map(replay, rows))

        def verify(case):
            i, bindings, expected = case
            expr = copies[i]
            for key, value in bindings:
                expr = f"replace(({expr}),{key},{value})"
            actual = evaluate(expr)
            if actual != expected:
                raise ValueError(f"M{i:03} expected {expected}, got {actual}")

        checks = list(cases(copies))
        list(pool.map(verify, checks))
    print(f"Verified {len(rows)} inputs covering 177 occurrences and {len(checks)} bound results.")


if __name__ == "__main__":
    main()
