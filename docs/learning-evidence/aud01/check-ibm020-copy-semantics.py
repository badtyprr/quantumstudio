"""Verify finite bindings of both GUI copies of the eight changing IBM-020 formulas."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess

HERE = Path(__file__).resolve().parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("records", "worker", "output"):
        parser.add_argument(name, type=Path)
    args = parser.parse_args()
    receipt = json.loads((HERE / "ibm020-logical-copy.json").read_bytes())
    raw = args.records.read_bytes()
    if hashlib.sha256(raw).hexdigest() != receipt["raw_records_sha256"]:
        raise ValueError("Unexpected GUI records")
    counts = Counter()

    def check(expression, expected):
        run = subprocess.run([args.worker, "--json"], input=("quantum:" + expression).encode(),
                             capture_output=True, check=True, timeout=30)
        result = json.loads(run.stdout)
        actual = result["copy_text"].replace("−", "-")
        if result["approximate"] or actual != expected:
            raise ValueError(f"Unexpected value for {expression}: {actual}")

    for row in json.loads(raw):
        identifier = row["id"]
        if identifier not in receipt["changed_copy_after_reentry"]:
            continue
        for key in ("copy", "second_copy"):
            text = row[key]
            if identifier == "M03":
                for bit in (0, 1):
                    check(f"replace(replace({text},qketstate('a'),basis({bit},2)),a,{bit})", "1")
                    counts[identifier] += 1
                continue
            kind = identifier.split("-")[-1]
            if kind in ("M028", "M029"):
                # The GUI interpreted f(x) as multiplication. Supply the lesson's
                # BV oracle explicitly and preserve this distinction in the report.
                pattern = r"""'f' ⋅ ("qboundindex_\d+")|qmul\('f',("qboundindex_\d+")\)"""
                text, changed = re.subn(pattern, lambda m: "qcenterdot('s'," +
                                        (m[1] or m[2]) + ")", text)
                if changed != 1:
                    raise ValueError("Expected exactly one scalar oracle occurrence")
            for n in (1, 2, 3):
                size = 1 << n
                for secret in range(1 if kind == "M027" else size):
                    q = f"replace(replace(replace({text},qpower('Σ',n),bitstrings({n})),n,{n}),s,bitstring({secret},{n}))"
                    if kind == "M066":
                        check(q, "1")
                    else:
                        if kind in ("M027", "M028"):
                            scale = 2 * size
                            column = [(-1)**((x & secret).bit_count()) for x in range(size)]
                        else:
                            scale = 2
                            column = [int(x == secret) for x in range(size)]
                        elements = column + [-v for v in column]
                        expected = f"matrix({2*size},1,[" + ",".join(map(str, elements)) + "])"
                        check(f"sqrt({scale})*({q})", expected)
                    counts[identifier] += 1
    if sorted(counts) != sorted(receipt["changed_copy_after_reentry"]):
        raise ValueError("Incomplete formula inventory")
    report = dict(gui_records_sha256=receipt["raw_records_sha256"],
                  worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                  exact_checks_by_source_id=counts, widths=[1, 2, 3],
                  method="Compared first and second copies separately to independently generated signed columns or true equalities. Bound the binary domains, widths and secrets; bound the one-qubit ket explicitly in M03.",
                  oracle_adaptations=["R13-0-M028", "R13-0-M029"],
                  limitation="These two formulas required replacing scalar multiplication by the promised BV oracle. The finite checks do not establish unbound oracle interpretation or identical copy text.")
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
