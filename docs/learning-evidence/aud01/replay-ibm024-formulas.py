"""Replay the original IBM-024 formulas with a calculator worker and the pinned notebook."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
from pathlib import Path
import os
import subprocess


def bind(expression, pairs):
    for key, value in pairs:
        expression = f"replace(({expression}),{key},{value})"
    return expression


def checks(copies):
    for n in (1, 2, 4, 7, 16):
        for i in (38, 80, 169):
            yield i, bind(copies[i], [("n", n)]), f'"C_{n}"'
        for gates in (9*n-5, 21*n-11):
            sized = bind(copies[42], [("n", n), (f"size(C_{n})", gates)])
            for count in (gates, gates+1):
                yield 42, bind(sized, [(f"t({n})", count)]), str(int(count == gates))
        for i, result in ((50, n+1), (55, 2*n-1), (56, 2*n-1), (57, n-1),
                          (58, 4*n-2), (59, 9*n-5), (60, 5*n-3)):
            yield i, bind(copies[i], [("n", n)]), str(result)
        for value in (-1, 0, 2**n-1, 2**n):
            for other in (0, 2**n):
                yield 49, bind(copies[49], [("n", n), ("N", value), ("M", other)]), str(int(0 <= value < 2**n and other < 2**n))
        for i in (67, 78):
            for threshold in (n, n+1):
                pairs = [("n", n), ('"n_0"', threshold)] if i == 67 else [("n", n), ("m", 2), ('"k_0"', threshold+2)]
                yield i, bind(copies[i], pairs), str(int(n >= threshold))
    for cost, linear in (("9*n-5", 1), ("21*n-11", 1), ("n^2", 0)):
        yield 82, bind(copies[82], [('qcostcall("size",vector(qindexedlabel("C_",n,"")))', cost)]), str(linear)
    for n in (1, 4, 16):
        m, k = 3, 5
        length = n.bit_length()
        for i, value in ((87, n*n), (95, n*m), (99, n*length*length.bit_length()),
                         (110, n*m), (115, n*m), (116, n*length**2*length.bit_length()),
                         (137, k*m*m+n*m), (146, n**3), (152, n*n)):
            copy = copies[i]
            if not copy.startswith("qbigorder(") or not copy.endswith(")"):
                raise ValueError(f"M{i:03} lost its asymptotic bound")
            expr = copy[len("qbigorder("):-1]
            pairs = [(key, v) for key,v in (("n",n),("'m'",m),("'k'",k)) if key in expr]
            yield i, bind(expr, pairs), str(value)
    for i in (123, 124):
        for base, exponent, modulus in ((7, 0, 5), (7, 3, 1), (11, 2**128+3, 97)):
            # Supply the modulus before the exponent to exercise modular exponentiation.
            yield i, bind(copies[i], [("M", modulus), ("N", base), ("K", exponent)]), str(pow(base, exponent, modulus))
    for n in (2, 4, 8):
        for i, value in ((149, 2**(n//2)), (153, n*n*2**(n//2))):
            body = copies[i][len("qbigorder("):-1]
            yield i, bind(body, [("n", n)]), str(value)
        term = copies[155]
        prefix = "qpower(2,qbigorder("
        if not term.startswith(prefix) or not term.endswith("))"):
            raise ValueError("M155 lost its exponential or asymptotic bound")
        exponent = term[len(prefix):-2]
        yield 155, bind(f"({exponent})^3", [("n", n)]), str(n*n.bit_length()**2)
        for degree in (1, 2, 3):
            body = copies[159][len("qbigorder("):-1]
            yield 159, bind(body, [("qcostparam('c')", degree), ("n", n)]), str(n**degree)
        body = copies[163][len("qbigorder("):-1]
        yield 163, bind(body, [("'ε'", 1), ("n", n)]), str(2**n)
    for i in (165, 166, 168):
        for n in (-1, 0, 1):
            yield i, bind(copies[i], [("n", n)]), str(int(n != 0))
    for i, expression in copies.items():
        # Verify bare identifiers as independent bindings, including repeated occurrences.
        if expression in {"'N'", "'M'", "'K'", "'C'", "'U'", "'t'", "'k'", "'m'", "'q'", "'r'", "n"}:
            yield i, bind(expression, [(expression, 17)]), "17"
    for value, largest in ((15, 3), (16, 4), (24, 4), (25, 5)):
        values = ",".join(map(str, range(2, largest+1)))
        yield 147, bind(copies[147], [("N", value)]), f"qset(vector({values}))"
    for epsilon in (-1, 0, 1):
        yield 164, bind(copies[164], [("'ε'", epsilon)]), str(int(epsilon > 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("worker", type=Path)
    parser.add_argument("notebook", type=Path)
    args = parser.parse_args()
    source = args.notebook.read_bytes()
    if hashlib.sha256(source).hexdigest() != "554cc9694595ec167fb501776310e6bfdfe0a87a5c638d2c79ba8a4fdf09bbcd":
        raise ValueError("The notebook differs from the audited source")
    cells = json.loads(source)["cells"]
    worker = args.worker.resolve()
    env = os.environ.copy()
    if (worker.parent / "data").is_dir():
        env.setdefault("QALCULATE_DEFINITIONS_DIR", str(worker.parent / "data"))

    def evaluate(expression):
        proc = subprocess.run([str(worker), "--json"], input=("quantum:"+expression).encode(),
                              capture_output=True, env=env, timeout=30, check=True)
        result = json.loads(proc.stdout)
        if result["approximate"]:
            raise ValueError(f"Expected exact evaluation of {expression}")
        return result["copy_text"]

    rows = [json.loads(line) for line in Path(__file__).with_name("ibm024-formula-audit.jsonl").read_bytes().splitlines()]
    if [row["id"] for row in rows] != list(range(1, 171)):
        raise ValueError("Incomplete source inventory")

    def replay(row):
        literal = "".join(cells[row["cell"]]["source"])[row["start"]:row["end"]]
        if hashlib.sha256(literal.encode()).hexdigest() != row["sha256"]:
            raise ValueError(f"M{row['id']:03} source differs")
        copy = evaluate(row["mode"]+literal)
        if copy != row["copy"] or evaluate(row["mode"]+copy) != copy:
            raise ValueError(f"M{row['id']:03} source or Copy changed")
        return row["id"], copy

    def verify(case):
        i, expr, expected = case
        actual = evaluate(expr)
        if actual != expected:
            raise ValueError(f"M{i:03} expected {expected}, got {actual}")

    with ThreadPoolExecutor(3) as pool:
        copies = dict(pool.map(replay, rows))
        cases = list(checks(copies))
        list(pool.map(verify, cases))
    print(f"Verified {len(rows)} source formulas and {len(cases)} bound results.")


if __name__ == "__main__":
    main()
