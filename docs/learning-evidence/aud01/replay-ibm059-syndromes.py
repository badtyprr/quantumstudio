"""Check the repetition-code stabilizer signs and the two Pauli observables."""
import argparse
import json
import os
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser()
parser.add_argument("worker", type=Path)
worker = parser.parse_args().worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent/"data"))
rows = json.loads(Path(__file__).with_name("ibm059-inventory.json").read_bytes())["rows"]


def evaluate(expr):
    p = subprocess.run([worker,"--json"],input=("quantum:"+expr).encode(),capture_output=True,check=True,env=env,timeout=30)
    result = json.loads(p.stdout)
    assert not result["approximate"]
    return result


assert evaluate(rows[19]["literal"])["copy_text"] == "1"
table = evaluate(rows[52]["literal"])
assert (table["rows"],table["columns"]) == (3,5)
for row,generator in enumerate(("Z@Z@I","I@Z@Z"),1):
    for column,error in enumerate(("I@I@I","X@I@I","I@X@I","I@I@X"),1):
        sign = table["cells"][row][column].replace("−","-")
        assert evaluate(f"({generator})*({error})=={sign}*({error})*({generator})")["copy_text"] == "1"
for state, expected in (("|000>","1"),("|111>","1"),("|010>","0")):
    relation = evaluate(rows[3]["literal"])["copy_text"]
    # The source gives both stabilizer equations as separate aligned rows.
    result = evaluate(f'replace(({relation}),qnamedket("ψ"),{state})')["copy_text"]
    result = evaluate(f'replace(({result}),qketstate("ψ"),{state})')["copy_text"]
    assert result == f"vector({expected},{expected})", result
print("Verified the repetition stabilizer group, eight syndrome signs and three codeword probes.")

# The printed two-bit outcome in M017 has significant leading zeroes.
# Use the explicit word entry to retain its width through Copy and decoding.
assert rows[16]["literal"] == "$00$"
group = "vector(compact_pauli(ZZI),compact_pauli(IZZ))"
for error in range(8):
    high, middle, low = (error >> 2) & 1, (error >> 1) & 1, error & 1
    digits = f"{high ^ middle}{middle ^ low}"
    word = evaluate(f'bitstring("{digits}")')["copy_text"]
    assert evaluate(word)["copy_text"] == word
    decoded = evaluate(f"compact_correction({group},{word},1)")["copy_text"]
    # A majority vote restores either logical codeword through one flip.
    # Two or three flips give the opposite codeword despite a clear syndrome.
    expected_residual = 0 if error.bit_count() <= 1 else 7
    expected_mask = error ^ expected_residual
    assert decoded == f"vector(3,{expected_mask},0,0)", (error, decoded)
print("Verified all eight physical bit-flip patterns and the logical failure boundary.")
