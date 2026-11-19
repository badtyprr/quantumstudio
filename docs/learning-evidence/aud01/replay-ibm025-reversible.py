"""Replay IBM-025's source matrix and garbage-free oracle equation."""
import json
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1]).resolve()
source = json.loads(Path(__file__).with_name("ibm025-reversible-inputs.json").read_bytes())
records = {}

def evaluate(expression):
    result = subprocess.run([worker, "--json"], input=("quantum:" + expression).encode(),
                            capture_output=True, timeout=20)
    assert result.returncode == 0, (expression, result.stderr)
    return json.loads(result.stdout)

for row in source["rows"]:
    records[row["id"][-4:]] = evaluate(row["literal"])

# A non-self-inverse permutation distinguishes applying f twice from
# applying the inverse. The saved function must also accept scalar bindings.
def graph(entries):
    pairs = [f"qtuple(vector(bitstring({x},2),bitstring({y},2)))" for x, y in entries]
    return "qset(vector(" + ",".join(pairs) + "))"

cycle = graph([(0, 1), (1, 2), (2, 3), (3, 0)])
inverse = graph([(1, 0), (2, 1), (3, 2), (0, 3)])
def forms(number):
    literal = next(row["literal"].strip("$") for row in source["rows"] if row["id"].endswith(number))
    record = records[number]
    result = (literal, record["display_text"], record["copy_text"])
    assert all(evaluate(body)["copy_text"] == record["copy_text"] for body in result)
    return result

for number, name in [("M028", "f"), ("M029", "g")]:
    for body in forms(number):
        assert evaluate(f"replace(replace(({body}),{name},3),x,7)")["copy_text"] == "21"
        for x in range(4):
            partial = evaluate(f"replace(({body}),x,bitstring({x},2))")["copy_text"]
            assert evaluate(f"replace(({partial}),{name},{cycle})")["copy_text"] == f"qbitlabel({(x+1)%4},2)"
for number in ("M067", "M083", "M087"):
    for body in forms(number):
        assert evaluate(f"replace(({body}),f,{cycle})={inverse}")["copy_text"] == "1"
        assert evaluate(f"replace(({body}),f,2)=1/2")["copy_text"] == "1"
for body in forms("M068"):
    for x in range(4):
        assert evaluate(f"replace(replace(({body}),f,{cycle}),x,bitstring({x},2))")["copy_text"] == "1"
for number in ("M085", "M091"):
    for body in forms(number):
        assert "qinversefunction(" in evaluate(body)["copy_text"]
for invalid in (graph([(0, 1), (0, 2)]), graph([(0, 2), (1, 2)])):
    proc = subprocess.run([worker, "--json"], input=f"quantum:replace(f^(-1),f,{invalid})".encode(),
                          capture_output=True, timeout=20)
    assert proc.returncode and b"one-to-one" in proc.stderr

# Check the other lesson expressions against concrete register and circuit
# assignments. Repeated printed expressions must retain the same meaning.
def bind(body, bindings):
    for name, value in bindings:
        body = f"replace(({body}),{name},{value})"
    return body

def matches(body, bindings, expected):
    query = f"({bind(body, bindings)})=({expected})"
    assert evaluate(query)["copy_text"] == "1", query

permutation = "matrix(4,4,[0,0,0,1,1,0,0,0,0,1,0,0,0,0,1,0])"
alphabet = (r"\Sigma", r"\{0,1\}")
literal_groups = {}
for row in source["rows"]:
    number = row["id"][-4:]
    literal = row["literal"].strip("$").strip()
    previous = literal_groups.setdefault(literal, number)
    assert records[previous]["copy_text"] == records[number]["copy_text"]

for literal, number in literal_groups.items():
    if literal in ("C", "R", "Q", "U", "n", "m", "k", "t", "x", "f", "g"):
        value = permutation if literal in ("C", "R", "Q", "U") else cycle if literal in ("f", "g") else "3"
        for body in (literal, records[number]["copy_text"]):
            matches(body, [(literal, value)], value)
for number, symbol in [("M005", "a"), ("M006", "b"), ("M070", "x")]:
    for body in forms(number):
        matches(body, [(symbol, "bitstring(1,2)")], "basis(1,4)")
for number in ("M014", "M026", "M060", "M066"):
    name = "g" if number == "M026" else "f"
    for body in (next(row["literal"].strip("$") for row in source["rows"] if row["id"].endswith(number)),
                 records[number]["copy_text"]):
        for mapping, answer in [(cycle, "1"), (graph([(0, 1)]), "0")]:
            matches(body, [("n", 2), ("m", 2), ("k", 2), alphabet, (name, mapping)], answer)
for body in (r"x\in\Sigma^n", records["M069"]["copy_text"]):
    for width, answer in [(2, "1"), (3, "0")]:
        matches(body, [alphabet, ("n", 2), ("x", f"bitstring(1,{width})")], answer)
for body in (r"\Sigma=\{0,1\}", records["M015"]["copy_text"]):
    matches(body, [alphabet], "1")
    matches(body, [(alphabet[0], r"\{0,2\}")], "0")
for body in (r"t=\operatorname{size}(C)", records["M010"]["copy_text"]):
    for size in (2, 3):
        matches(body, [("size(C)", 2), ("t", size)], str(int(size == 2)))
for cost, answer in [("n", "1"), ("n^2", "0")]:
    matches(f"{cost}=({records['M049']['copy_text']})", [("t", "n")], answer)
for number in ("M071", "M073"):
    row = next(row for row in source["rows"] if row["id"].endswith(number))
    for body in (row["literal"].strip("$").strip(), records[number]["display_text"], records[number]["copy_text"]):
        for x in range(4):
            bindings = [("f", cycle), ("x", f"bitstring({x},2)")]
            if number == "M071":
                matches(body, bindings, f"basis({(x + 1) % 4},4)")
            else:
                for operator, answer in [(permutation, "1"), ("identity(4)", "0")]:
                    matches(body, bindings + [("U", operator)], answer)
for number in ("M084", "M085"):
    row = next(row for row in source["rows"] if row["id"].endswith(number))
    label = row["literal"].strip("$")
    for body in (label, records[number]["copy_text"]):
        matches(body, [(label, permutation)], permutation)

# A zero word has both a value and a width. Bind each operand first,
# then copy the intermediate result before supplying the other operand.
zero_word = records["M055"]
source_word = next(row["literal"].strip("$") for row in source["rows"] if row["id"].endswith("M055"))
for body in (source_word, zero_word["display_text"], zero_word["copy_text"]):
    assert evaluate(body)["copy_text"] == zero_word["copy_text"]
    for count, value, width in [(0, 0, 0), (1, 0, 1), (2, 0, 2), (2, 0, 1),
                                (2, 1, 2), (1000, 0, 1000), (1000, 0, 999)]:
        bits = f"bitstring({value},{width})"
        expected = str(int(value == 0 and width == count))
        for first, second in [(("m", count), ("y", bits)), (("y", bits), ("m", count))]:
            partial = evaluate(f"replace(({body}),{first[0]},{first[1]})")["copy_text"]
            assert evaluate(f"replace(({partial}),{second[0]},{second[1]})")["copy_text"] == expected
for operand, expected in [("0", "1"), ("1", "0"), ("i", "0"), ("vector(0,0)", "1"),
                          ("matrix(2,1,[0,1])", "0")]:
    assert evaluate(f"replace(replace(({source_word}),y,{operand}),m,2)")["copy_text"] == expected
for expr in ("bitstring(0,3)!=0^2", "0^2=bitstring(0,2)", "0^(1+1)=bitstring(0,2)"):
    assert evaluate(expr)["copy_text"] == "1"

# R is the reversible circuit in the lesson. Bind after entry, display, and
# Copy to distinguish an inverse permutation, transpose, and conjugation.
adjoint = records["M038"]
literal = next(row["literal"].strip("$") for row in source["rows"] if row["id"].endswith("M038"))
for body in (literal, adjoint["display_text"], adjoint["copy_text"]):
    assert evaluate(body)["copy_text"] == adjoint["copy_text"]
    for operand, expected in [
        ("matrix(2,3,[1,i,2,3,4,i])", "matrix(3,2,[1,3,-i,4,2,-i])"),
        ("matrix(3,3,[0,0,1,1,0,0,0,1,0])", "matrix(3,3,[0,1,0,0,0,1,1,0,0])"),
        ("i", "-i"), ("7", "7"),
    ]:
        assert evaluate(f"replace(({body}),R,{operand})={expected}")["copy_text"] == "1"
for number, gate in [("M002", "matrix(2,2,[1,1,1,-1])/sqrt(2)"),
                     ("M003", "matrix(2,2,[1,0,0,(1+i)/sqrt(2)])"),
                     ("M004", "matrix(2,2,[1,0,0,(1-i)/sqrt(2)])")]:
    assert evaluate(f"({records[number]['copy_text']})=({gate})")["copy_text"] == "1"
assert evaluate("R\u2020\u2020")["copy_text"] == evaluate("R")["copy_text"]

toffoli = records["M001"]["copy_text"]
# IBM orders the two low bits as controls and the high bit as target.
for column in range(8):
    target = column ^ (4 if column & 3 == 3 else 0)
    assert evaluate(f"{toffoli}*basis({column},8)=basis({target},8)")["copy_text"] == "1"

row = next(row for row in source["rows"] if row["id"].endswith("M062"))
original = row["literal"].strip("$").strip()
copied = records["M062"]["copy_text"]
displayed = records["M062"]["display_text"]
assert evaluate(copied)["copy_text"] == evaluate(displayed)["copy_text"] == copied
# Enumerate all four one-bit Boolean functions, all basis inputs, and
# two implementations. A faulty implementation always flips one extra bit.
for table in ((0, 0), (0, 1), (1, 0), (1, 1)):
    pairs = [f"qtuple(vector(bitstring({x},1),bitstring({value},1)))"
             for x, value in enumerate(table)]
    graph = "qset(vector(" + ",".join(pairs) + "))"
    for faulty in (False, True):
        entries = [str(int(i == (j ^ (4 * table[j & 1]) ^ (2 if faulty else 0))))
                   for i in range(8) for j in range(8)]
        operator = "matrix(8,8,[" + ",".join(entries) + "])"
        for x in (0, 1):
            for y in (0, 1):
                for body in (original, displayed, copied):
                    bindings = [("f", graph), ("x", f"bitstring({x},1)"),
                                ("y", f"bitstring({y},1)"), ("k", "1"), ("Q", operator)]
                    for name, value in bindings:
                        body = f"replace(({body}),{name},{value})"
                    assert evaluate(body)["copy_text"] == str(int(not faulty)), (table, faulty, x, y)
assert evaluate('replace(|y # 01>,y,bitstring(3,2))')["copy_text"] == "matrix(4,1,[0,0,1,0])"
print("Verified 91 source inputs, eight Toffoli columns and 96 oracle substitutions.")
