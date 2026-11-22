"""Audit the pinned repetition-code lesson against independent three-qubit expectations."""
import argparse
from collections import Counter
from functools import lru_cache
import hashlib
from itertools import product
import json
import os
from pathlib import Path
import re
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("worker", type=Path)
parser.add_argument("notebook", type=Path)
parser.add_argument("figures", type=Path)
args = parser.parse_args()
here = Path(__file__).resolve().parent
worker = args.worker.resolve()
env = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(worker.parent / "data"))
inventory = json.loads((here / "ibm059-inventory.json").read_bytes())
rows = inventory["rows"]
assert hashlib.sha256(args.notebook.read_bytes()).hexdigest() == inventory["source_sha256"]
cells = json.loads(args.notebook.read_bytes())["cells"]
assert [cell["cell_type"] for cell in cells] == ["markdown"]
source = "".join(cells[0]["source"])
spans = re.finditer(r"\$\$[\s\S]*?\$\$|\$[^$\n]+?\$", source)
assert [(m.start(), m.end(), m.group()) for m in spans] == [
    (row["start"], row["end"], row["literal"]) for row in rows]
references = re.findall(r"!\[[^\]]*\]\(([^)]+)\)", source)
figures = [f for f in json.loads((here / "ibm057-figures.json").read_bytes()) if f["lesson"] == 59]
assert sorted(references) == sorted(f["path"] for f in figures)
for figure in figures:
    file = args.figures / Path(figure["path"]).name
    assert hashlib.sha256(file.read_bytes()).hexdigest() == figure["sha256"]


@lru_cache(maxsize=None)
def copy(expr):
    proc = subprocess.run([worker, "--json"], input="quantum:" + expr, text=True,
                          encoding="utf8", env=env, capture_output=True, timeout=30)
    if proc.returncode:
        raise RuntimeError(proc.stderr)
    result = json.loads(proc.stdout)
    assert not result["approximate"], expr
    return result["copy_text"]


def column(index):
    return "matrix(8,1,[" + ",".join(str(int(i == index)) for i in range(8)) + "])"


def apply_to_basis(expr, index):
    for name in ("qnamedket", "qketstate"):
        expr = copy(f'replace(({expr}),{name}("ψ"),|{index:03b}>)')
    return expr


def pauli_matrix(letters):
    size = 2 ** len(letters)
    flip = int("".join(str(int(c == "X")) for c in letters), 2)
    phase = int("".join(str(int(c == "Z")) for c in letters), 2)
    entries = [(-1) ** ((c & phase).bit_count()) if r == c ^ flip else 0
               for r in range(size) for c in range(size)]
    return f"matrix({size},{size},[" + ",".join(map(str, entries)) + "])"


for i, row in enumerate(rows, 1):
    literal = row["literal"]
    actual = copy(literal)
    assert actual == row["copy"], (i, actual)
    plain = literal.strip("$ ").replace(" ", "").replace(r"\mathbb{I}", "I")
    letters = plain.split(r"\otimes")
    if all(c in ("I", "X", "Z") for c in letters):
        assert actual.replace("−", "-") == pauli_matrix(letters), i
    elif plain in ("1", "+1", "-1", "0", "00"):
        assert int(actual.replace("−", "-")) == int(plain), i
    elif plain == r"\vert\psi\rangle":
        assert actual == "qketstate('ψ')", i
    elif plain in (r"\vert000\rangle", r"\vert111\rangle"):
        assert actual == column(0 if "000" in plain else 7), i
    elif plain == "(+1,+1)":
        assert actual == "qtuple(vector(1,1))", i
    elif i == 1:
        assert actual == "matrix(2,1,['α','β'])"
    elif i == 2:
        assert actual == "qcompare(qketstate('ψ'),matrix(8,1,['α',0,0,0,0,0,0,'β']),4)"
    elif i in (4, 25, 37, 38, 42, 45):
        for state in range(8):
            left = int((state & 6).bit_count() % 2 == 0)
            right = int((state & 3).bit_count() % 2 == 0)
            target = column(state ^ 4)
            expected = {4: f"vector({left},{right})", 25: f"qstateaction({column(state)},{target})",
                        37: str(left), 38: target, 42: target, 45: str(right)}
            assert apply_to_basis(actual, state) == expected[i], (i, state)
    elif i in (20, 79):
        assert actual == "1", i
    elif i == 50:
        assert actual == r"\begin{gathered}1\\1\end{gathered}"
    elif i == 53:
        # Verify the source table, its headers, and each generator's signs independently.
        groups = [["qoutcome(\"syndrome\")"] + [pauli_matrix(s) for s in ("III","XII","IXI","IIX")],
                  [pauli_matrix("ZZI"),"1","-1","-1","1"],
                  [pauli_matrix("IZZ"),"1","1","-1","-1"]]
        assert actual.replace("−", "-") == "vector(" + ",".join("vector(" + ",".join(g) + ")" for g in groups) + ")"
    else:
        raise AssertionError((i, literal))

classes = Counter()
for triple in product("IXYZ", repeat=3):
    word = "".join(triple)
    bits = [int(letter in "XY") for letter in triple]
    expected = (bits[0] ^ bits[1], bits[1] ^ bits[2])
    syndrome = copy(f"compact_syndrome(vector(compact_pauli(ZZI),compact_pauli(IZZ)),compact_pauli({word}))")
    assert syndrome == f"vector({expected[0]},{expected[1]})", word
    classes[expected] += 1
assert sorted(classes.values()) == [16] * 4
for index in range(3):
    generators = ["ZZI", "IZZ", "ZIZ"]
    del generators[index]
    group = "vector(" + ",".join(f"compact_pauli({g})" for g in generators) + ")"
    assert copy(f"compact_dimension({group})") == "2"
    for state in range(8):
        error = "".join("X" if b == "1" else "I" for b in f"{state:03b}")
        quiet = copy(f"compact_syndrome({group},compact_pauli({error}))") == "vector(0,0)"
        assert quiet == (state in (0, 7))

print(f"Verified {len(rows)} source occurrences, {len(figures)} figures, 64 Pauli syndromes and three generator choices.")
