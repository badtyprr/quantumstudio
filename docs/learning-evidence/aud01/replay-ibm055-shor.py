"""Decode every one-qubit Pauli error on the source nine-qubit Shor codewords."""
import argparse
import json
import math
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
args = parser.parse_args()
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
source = json.loads(Path(__file__).with_name("ibm055-inventory.json").read_bytes())["rows"][0]["literal"]
code = []
for term in source.split(r"\mapsto\:")[1:]:
    expr = re.split(r"\\\\\[|\\end\{aligned\}", term)[0]
    run = subprocess.run([worker, "--approx", "--json"], input=("quantum:"+expr).encode(),
                         env=env, capture_output=True, check=True, timeout=30)
    result = json.loads(run.stdout)
    assert (result["rows"], result["columns"]) == (512, 1)
    matrix = re.fullmatch(r"matrix\(512,1,\[([^\]]+)\]\)", result["copy_text"])
    column = [float(value.replace("−","-")) for value in matrix[1].split(",")]
    assert len(column) == 512
    code.append(column)
assert len(code) == 2
for logical, column in enumerate(code):
    for index, amplitude in enumerate(column):
        blocks = [(index >> shift) & 7 for shift in (0,3,6)]
        expected = ((-1)**(logical*blocks.count(7))/math.sqrt(8)
                    if all(block in (0,7) for block in blocks) else 0)
        assert abs(amplitude-expected) < 1e-13


def pauli(state, xmask, zmask):
    return [(-1)**((index & zmask).bit_count()) * state[index ^ xmask] for index in range(512)]


def syndrome(state, xmask, zmask):
    moved = pauli(state, xmask, zmask)
    overlap = sum(a.conjugate()*b for a,b in zip(state,moved))
    assert abs(abs(overlap)-1) < 1e-12
    return int(overlap.real < 0)


# The relative imaginary phase distinguishes successful correction from dephasing.
original = [(a+1j*b)/math.sqrt(2) for a,b in zip(*code)]
for wire in range(9):
    for x,z in [(1,0),(0,1),(1,1)]:
        noisy = pauli(original, x << wire, z << wire)
        for block in range(3):
            shift = 3*block
            pair = syndrome(noisy,0,3<<shift), syndrome(noisy,0,6<<shift)
            if pair != (0,0):
                bit = {(1,0):0, (1,1):1, (0,1):2}[pair]
                noisy = pauli(noisy,1<<(shift+bit),0)
        pair = syndrome(noisy,63,0), syndrome(noisy,63<<3,0)
        if pair != (0,0):
            block = {(1,0):0, (1,1):1, (0,1):2}[pair]
            noisy = pauli(noisy,0,1<<(3*block))
        fidelity = abs(sum(a.conjugate()*b for a,b in zip(original,noisy)))**2
        assert abs(fidelity-1) < 1e-12, (wire,x,z,fidelity)
print("Verified both 512-component codewords and corrected all 27 single-qubit Pauli errors.")
