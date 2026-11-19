"""Exhaustively count independent Simon measurement transcripts by their GF(2) kernel."""
import argparse
from collections import defaultdict
from fractions import Fraction
from functools import cache
import hashlib
import json
from pathlib import Path
import subprocess


def audit(width, worker):
    size = 2**width
    orthogonal = [frozenset(x for x in range(size) if (x & y).bit_count() % 2 == 0)
                  for y in range(size)]
    initial = frozenset(range(size))
    witnesses = {initial: [0]}

    @cache
    def verify(kernel):
        rows = witnesses[kernel]
        digits = ",".join(bit for row in rows for bit in format(row, f"0{width}b"))
        expr = f"quantum:qgf2nullspace(matrix({len(rows)},{width},[{digits}]))"
        proc = subprocess.run([worker, "--json"], input=expr.encode(), capture_output=True,
                              check=True, timeout=30)
        result = json.loads(proc.stdout)
        if result["approximate"]:
            raise ValueError("Expected an exact GF(2) basis")
        columns = []
        if result["copy_text"] != "vector()":
            if width == 1 and result["copy_text"] == "1":
                columns = [1]
            else:
                if result["rows"] != width:
                    raise ValueError(f"Wrong kernel dimensions for {rows}")
                columns = [int("".join(bits), 2) for bits in zip(*result["cells"])]
        span = {0}
        for vector in columns:
            span |= {x ^ vector for x in span}
        if span != kernel or len(span) != 2**len(columns):
            raise ValueError(f"Native basis mismatch for rows {rows}")

    probabilities = {}
    for secret in range(size):
        target = frozenset((0, secret))
        outcomes = orthogonal[secret]
        counts = {initial: 1}
        verify(initial)
        for k in range(1, width + 11):
            following = defaultdict(int)
            for kernel, count in counts.items():
                for y in outcomes:
                    next_kernel = kernel & orthogonal[y]
                    if next_kernel not in witnesses:
                        witnesses[next_kernel] = witnesses[kernel] + [y]
                    verify(next_kernel)
                    following[next_kernel] += count
            counts = following
            if sum(counts.values()) != len(outcomes)**k:
                raise ValueError("Transcript count mismatch")
            probability = Fraction(counts.get(target, 0), len(outcomes)**k)
            dimension = width - int(secret != 0)
            exact = Fraction(1)
            for j in range(dimension):
                exact *= 1 - Fraction(2**j, 2**k)
            if probability != exact or (k >= width and probability < 1 - Fraction(1, 2**(k-width))):
                raise ValueError(f"Recovery probability mismatch for {secret}, {k}")
        probabilities[format(secret, f"0{width}b")] = str(probability)
    return dict(width=width, samples=width+10, native_kernels=len(witnesses),
                recovery_by_secret=probabilities)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("notebook", type=Path)
    parser.add_argument("worker", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    source_hash = hashlib.sha256(args.notebook.read_bytes()).hexdigest()
    if source_hash != "2a53c7740281662c4c68fd9b3a9492c3615ea3bbfead3c0d3cce9f2fab698f7a":
        raise ValueError("Unexpected source notebook")
    audits = [audit(width, args.worker) for width in range(1, 5)]
    report = dict(source_sha256=source_hash, section="Classical post-processing",
                  worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                  event="The kernel equals {0,s}, including the singleton {0} for the injective case.",
                  method="Count ordered independent measurement transcripts exactly by intersecting kernels. For each distinct kernel verify the span and independence of the native basis on a representative transcript. Compare every sample count from 1 to n+10 to the full-rank product for the sampled subspace.",
                  general_bound="For any non-target candidate v, exactly half the allowed outcomes y have v dot y = 0. Its probability of surviving k independent rows is 2^-k. Summing over fewer than 2^n false candidates bounds failure by 2^(n-k).",
                  audits=audits)
    args.output.write_bytes((json.dumps(report, indent=2) + "\n").encode())


if __name__ == "__main__":
    main()
