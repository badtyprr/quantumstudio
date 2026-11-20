"""Exercise the worker process and JSON contract used by the Windows GUI."""
import json
import re
from decimal import Decimal
import os
from pathlib import Path
import subprocess
import sys

worker = Path(sys.argv[1] if len(sys.argv) > 1 else "quantum-worker" + (".exe" if os.name == "nt" else "")).resolve()
checks = 0

def run(expression, *flags, success=True):
    global checks
    result = subprocess.run([str(worker), *flags], input=expression.encode("utf-8"), capture_output=True, timeout=30)
    assert (result.returncode == 0) == success, (expression[:100], result.returncode, result.stderr)
    checks += 1
    return result

def data(expression, *flags):
    result = run(expression, "--json", *flags)
    value = json.loads(result.stdout.decode("utf-8"))
    assert set(value) == {"text", "display_text", "copy_text", "approximate", "rows", "columns", "cells", "probabilities", "bloch"}
    return value


# Physical units must survive Copy without becoming quantum variables.
for speed in ("c", "element([c;2*c],1,1)"):
    text = data("quantum:"+speed)["copy_text"]
    assert data("quantum:("+text+")/c")["copy_text"] == "1"
    assert data("quantum:"+text)["copy_text"] == text
frequency = data("quantum:MHz")["copy_text"]
assert data("quantum:("+frequency+")/kHz")["copy_text"] == "1000"
classical_speed = data("c")["copy_text"]
assert data("("+classical_speed+")/c")["copy_text"] == "1"
assert "qphysicalunit" not in classical_speed

# The computational-cost lesson expresses modular powers using a spaced text label.
for gap in (r"\hspace{1mm} ", r"\hspace{1mm}"):
    source = "$N^K" + gap + r"(\text{mod }M)$"
    result = data("quantum:" + source)
    copied = result["copy_text"]
    assert data("quantum:" + copied)["copy_text"] == copied
    assert data("quantum:" + result["display_text"])["copy_text"] == copied
    for base, exponent, modulus in ((0, 0, 1), (0, 1, 13), (23, 0, 17), (23, 5, 17), (2, 1024, 101), (3, 2**128 + 1, 65537)):
        expected = str(pow(base, exponent, modulus))
        numeric = f"${base}^{{{exponent}}}" + gap + rf"(\text{{mod }}{modulus})$"
        assert data("quantum:" + numeric)["copy_text"] == expected
        bound = f"replace(replace(replace({copied},N,{base}),K,{exponent}),M,{modulus})"
        assert data("quantum:" + bound)["copy_text"] == expected

assert b"modulus must be nonzero" in run("quantum:2^5 pmod (0)", success=False).stderr

# Asymptotic upper bounds compare polynomial growth for large input sizes.
for formula, expected in [
    ("17 n^3 - 257 n^2 + 65537 = O(n^3)", "1"), ("n^3=O(n^2)", "0"),
    ("n^3!=O(n^2)", "1"), ("123456 n=O(n^2)", "1"), ("(n+1)^2=O(n)", "0"),
    ("(n^3+n)-n^3=O(n)", "1"), ("0=O(0)", "1"), ("n=O(0)", "0"),
    ("1=O(n)", "1"), ("n^2=replace(O(n^c),c,3)", "1"), ("cost(lg(8))", "4"),
]:
    assert data("quantum:" + formula)["copy_text"] == expected
for args in ("n", "n,m"):
    formula = f"g({args})=O(h({args}))"
    record = data("quantum:" + formula)
    for body in (formula, record["copy_text"], record["display_text"]):
        for cost, expected in (("n", "1"), ("n^3", "0")):
            probe = f"replace(replace(({body}),g({args}),{cost}),h({args}),n^2)"
            assert data("quantum:" + probe)["copy_text"] == expected
for formula in ("O(nm)", "O(n^c)", r"O(n(\operatorname{lg}(n))^2)", "g(n)+2=O(n^2)"):
    copied = data("quantum:" + formula)["copy_text"]
    assert "qbigorder(" in copied and data("quantum:" + copied)["copy_text"] == copied
for cost, expected in ((6, "1"), (7, "0")):
    probe = f"replace(replace(replace(cost(g(n,m)<=c*h(n,m)),g(n,m),{cost}),h(n,m),3),cost(c),2)"
    assert data("quantum:" + probe)["copy_text"] == expected
assert data("quantum:cost(replace((c>0),c,-1))")["copy_text"] == "0"
assert data("quantum:nn^2=O(n^3)")["copy_text"] == "1"
assert data("quantum:cost(replace(replace(nm^2,n,3),m,2))")["copy_text"] == "12"
for source, binding, expected in [
    ("cost(c>0)", "c,-1", "0"),
    ("g(n)=replace(O(n^c),c,3)", "g(n),n^4", "0"),
    ("0<1,2<g(n)=O(n^2)", "g(n),3", "1"),
    ("0<1,2<g(n)=O(n^2)", "g(n),1", "0"),
]:
    for body in (source, data("quantum:" + source)["copy_text"]):
        assert data(f"quantum:replace(({body}),{binding})")["copy_text"] == expected
run("quantum:O(" + "n" * 700 + ")", "--json", success=False)

# The comma in a shared bound is local to a grouped expression. Function
# arguments and vector elements continue to be independent comparisons.
shared_bound = r"0\leq N,M\leq 2^n - 1"
saved_bound = data("quantum:$$" + shared_bound + ".$$")["copy_text"]
for body in (shared_bound, saved_bound):
    for width in (0, 1, 3):
        maximum = 2**width - 1
        for a, b in ((0, maximum), (maximum, 0), (-1, 0), (0, -1),
                     (maximum + 1, 0), (0, maximum + 1), (-1, maximum + 1)):
            expr = f"replace(replace(replace(({body}),N,{a}),M,{b}),n,{width})"
            assert data("quantum:" + expr)["copy_text"] == str(int(0 <= a <= maximum and 0 <= b <= maximum))
for expr, truth in [("5 > 1,2,4 >= 1", "1"), ("5 > 1,5 >= 1", "0"),
                    ("0 <= 2,3 < 3", "0"), ("0 < 1,2 < 3 <= 2", "0"),
                    ("vector(0 <= 3,4 <= 2)", "vector(1,0)")]:
    assert data("quantum:" + expr)["copy_text"] == truth
run("quantum:0 <= x,y", "--json", success=False)

# An isolated binary word needs a width, while an equation can learn the
# type of its right-hand literal or named application from later bindings.
for digits, value in (("011", 3), ("00101", 5), ("00001", 1), ("", 0)):
    assert data(f'quantum:bitstring("{digits}")')["copy_text"] == f"qbitlabel({value},{len(digits)})"
run('quantum:bitstring("102")', "--json", success=False)
assert data("quantum:011 + 1")["copy_text"] == "12"
for equation in ("s=011", "011=s"):
    result = data("quantum:" + equation)
    for body in (equation, result["copy_text"], result["display_text"]):
        for probe, truth in [('bitstring("011")', "1"), ('bitstring("0011")', "0"),
                             ('bitstring("111")', "0"), ("11", "1"), ("3", "0")]:
            assert data(f"quantum:replace(({body}),s,{probe})")["copy_text"] == truth
for equation in ("z=f(x)", "f(x)=z"):
    result = data("quantum:" + equation)
    for body in (equation, result["copy_text"], result["display_text"]):
        assert data(f"quantum:replace(replace(replace(({body}),z,6),x,3),f,2)")["copy_text"] == "1"

for n in (0, 1, 2, 7, 8, 15, 16, 2**128 - 1, 2**128):
    assert data(rf"quantum:$\operatorname{{lg}}({n})$")["copy_text"] == str(max(1, n.bit_length()))
for value in ("-1", "3/2"):
    run(f"quantum:bitlength({value})", "--json", success=False)
assert data(r"quantum:$\log_{2}(8)$")["copy_text"] == "3"
for argument, expected in (("2^512-1",511),("2^512",512),("1/8",-3),("1/9",-4),("3/2",0)):
    assert data(f"quantum:floor(log2({argument}))")["copy_text"] == str(expected).replace("-", "−")
assert data("quantum:lg(100)")["copy_text"] == "2"

# A circuit size is a formal gate count. Bind the count independently
# of its circuit label or the cost function used to describe it.
for formula in (r"\operatorname{size}(C)", "size(C_n)"):
    record = data("quantum:" + formula)
    assert "qcostcall(" in record["copy_text"]
    assert data("quantum:" + record["display_text"])["copy_text"] == record["copy_text"]
for body in (r"t(n) = \operatorname{size}(C_n)", "t(n) = size(C_n)"):
    original = data("quantum:" + body)
    for form in (body, original["copy_text"], original["display_text"]):
        for count in (72, 73):
            probe = f"replace(replace(({form}),t(n),73),size(C_n),{count})"
            assert data("quantum:" + probe)["copy_text"] == str(int(count == 73))
run("quantum:size(C_1,C_2)", "--json", success=False)

for fn, parameters in (("t","n"),("g","n"),("h","n,m"),("a","m,k")):
    application = f"{fn}({parameters})"
    held = data("quantum:" + application)
    assert "qcostcall(" in held["copy_text"]
    for form in (application, held["display_text"], held["copy_text"]):
        assert data(f"quantum:replace({form},{application},17)")["copy_text"] == "17"
    numerical = data(f"quantum:replace({held['copy_text']},n,3)")
    assert data("quantum:" + numerical["display_text"])["copy_text"] == numerical["copy_text"]
assert data("quantum:replace(replace(g(n),g,4),n,3)")["copy_text"] == "12"
assert data("quantum:replace(replace(replace(g(n,m),g,2),n,3),m,4)")["copy_text"] == "vector(6,8)"
graph = "qset(vector(qtuple(vector(bitstring(0,1),bitstring(1,1)))))"
assert data(f"quantum:replace(replace(g(n),g,{graph}),n,bitstring(0,1))")["copy_text"] == "qbitlabel(1,1)"
assert data("quantum:g(n,m)=g(n,m)")["copy_text"] == "1"
assert data("quantum:g(n,m)!=g(n,m)")["copy_text"] == "0"
assert data("quantum:replace(n(n-1),n,3)")["copy_text"] == "6"

# An isolated cost witness binds the same ordered size arguments on both sides.
for witness in ("g(n,m)<=c*h(n,m)", "c*h(n,m)>=g(n,m)", "a(k)<=c*b(k)"):
    result = data("quantum:" + witness)
    assert "qcostcall(" in result["copy_text"] and "qcostparam(" in result["copy_text"]
    for form in (witness, result["display_text"], result["copy_text"]):
        left, right = ("a(k)", "b(k)") if witness.startswith("a") else ("g(n,m)", "h(n,m)")
        for cost_value in (6, 7):
            probe = f"replace(replace(replace(({form}),{left},{cost_value}),{right},3),c,2)"
            assert data("quantum:" + probe)["copy_text"] == str(int(cost_value <= 6))
# Arithmetic following the right operand is outside the standalone witness grammar.
assert "qcostparam" not in data("quantum:g(n)<=c*h(n)+1")["copy_text"]

# Both open-ended circuit families describe one circuit per input size.
circuits = []
for literal in (r"\{C_1, C_2, C_3,\ldots\}", r"\{C_1, C_2,\ldots,\}"):
    original = data("quantum:" + literal)
    family = original["copy_text"]
    assert data("quantum:" + original["display_text"])["copy_text"] == family
    assert data("quantum:" + family)["copy_text"] == family
    for index in (1, 2, 3, 19):
        expected = data(f"quantum:C_{index}")["copy_text"]
        assert data(f"quantum:familyat({family},{index})")["copy_text"] == expected
    circuits.append(family)
assert circuits[0] == circuits[1]
assert data(f"quantum:member(C_19,{circuits[0]})")["copy_text"] == "1"
assert "qmember(" in data(f"quantum:member(D_19,{circuits[0]})")["copy_text"]
pending_index = data(f"quantum:familyat({circuits[0]},n)")["copy_text"]
assert data(f"quantum:replace({pending_index},n,12)")["copy_text"] == data("quantum:C_12")["copy_text"]
for index in ("0", "-1", "3/2"):
    run(f"quantum:familyat({circuits[0]},{index})", "--json", success=False)
for invalid in (r"\{C_1,D_2,\ldots\}", r"\{C_1,C_3,\ldots\}"):
    run("quantum:" + invalid, "--json", success=False)

# Trial division enumerates integer candidates, including the square root
# exactly when the input is a perfect square.
trial_range = data(r"quantum:$2,\ldots,\sqrt{N}$")["copy_text"]
assert data("quantum:" + trial_range)["copy_text"] == trial_range
for n, expected in ((2, []), (3, []), (4, [2]), (15, [2, 3]), (16, [2, 3, 4]), (17, [2, 3, 4])):
    canonical = "qset(vector(" + ",".join(map(str, expected)) + "))"
    assert data(f"quantum:replace({trial_range},N,{n})")["copy_text"] == canonical
run(f"quantum:replace({trial_range},N,1026^2)", "--json", success=False)
run(r"quantum:1,...,3 \in \{1,2,3\}", "--json", success=False)

for dots in ("...", r"\dots", r"\ldots", r"\cdots"):
    samples = rf"z^1, {dots}, z^{{2}} \in \{{0,1\}}^3"
    partial = data(f'quantum:replace(({samples}),"z^2",bitstring(0,3))')["copy_text"]
    for width, expected in ((3, "1"), (2, "0")):
        assert data(f'quantum:replace(({partial}),"z^1",bitstring(0,{width}))')["copy_text"] == expected
for invalid in (r"z^2,...,z^3 \in \{1\}", r"z^1,...,y^3 \in \{1\}", r"z^1,...,z^0 \in \{1\}"):
    run("quantum:" + invalid, "--json", success=False)
assert data("quantum:replace(z^2,z,3)")["copy_text"] == "9"

copied_dot = data(r"quantum:w \cdot y")["copy_text"]
assert data(f"quantum:replace(replace({copied_dot},w,bitstring(3,2)),y,bitstring(3,2))")["copy_text"] == "0"
assert data(f"quantum:replace(replace({copied_dot},w,3),y,3)")["copy_text"] == "9"

# Bind a deferred ket sum after copying its norm or normalization.
for operation in ("norm", "normalize"):
    pending = data(rf"quantum:{operation}(\sum_{{x\in d}}{{|x>}})")["copy_text"]
    bound = data(f"quantum:replace({pending},d,bitstrings(1))")["copy_text"]
    assert bound == data(rf"quantum:{operation}(\sum_{{x\in bitstrings(1)}}{{|x>}})")["copy_text"]
    invalid = rf"quantum:replace({operation}(\sum_{{x\in d}}{{x}}),d,\{{1,2\}})"
    assert run(invalid, "--json", success=False).stdout == b""

# A centered dot is parity on bit strings, including labels supplied by a binding.
for z in range(16):
    entries = [rf"bitstring({z},4) \cdot bitstring({x},4)" for x in range(16)]
    expected = [str((x & z).bit_count() % 2) for x in range(16)]
    assert data("quantum:vector(" + ",".join(entries) + ")")["copy_text"] == "vector(" + ",".join(expected) + ")"
assert data(r"quantum:replace(replace(x \cdot y,x,bitstring(2,2)),y,bitstring(1,2))")["copy_text"] == "0"
assert data(r"quantum:\sum_{x\in bitstrings(2)}{\sum_{y\in bitstrings(2)}{x\cdot y}}")["copy_text"] == "6"
assert data(r"quantum:replace(replace(z\cdot x=0,z,bitstring(2,2)),x,bitstring(1,2))")["copy_text"] == "1"
assert data(r"quantum:2 \cdot 3")["copy_text"] == "6"

# A power used as a domain retains its alphabet until the caller binds it.
word_member = data(r"quantum:x \in \Sigma^n")["copy_text"]
for alphabet in [r"\{1,0\}", "bitstrings(1)"]:
    expr = rf"replace(replace(replace({word_member},\Sigma,{alphabet}),n,2),x,bitstring(1,2))"
    assert data("quantum:" + expr)["copy_text"] == "1"
assert data(r"quantum:replace(tuple(3,4) \in A^2,A,\{3,4\})")["copy_text"] == "1"
assert data(r"quantum:replace(\Sigma^2,\Sigma,3)")["copy_text"] == "9"
assert b"nonnegative integer" in run(r"quantum:x \in A^(-1)", "--json", success=False).stderr

# Set equality is independent of member order, also for copied graph domains.
for expression, expected in [
    (r"\{2,1\}=\{1,2\}", "1"),
    (r"\{2,1\}!=\{2,3\}", "1"),
    (r"\{2,1\}=\{1,2\}=\{2,1\}", "1"),
    (r"replace(\{x,1\}=\{1\},x,1)", "1"),
    (r"replace(\{x,1\}=\{1\},x,2)", "0"),
]:
    assert data("quantum:" + expression)["copy_text"] == expected

# A descending bit definition denotes a word of exactly the given width.
word = r"s=s_{n-1} \cdots s_0"
copied_word = data("quantum:" + word)["copy_text"]
for width, bindings, value, label_width, expected in [
    (0, [], 0, 0, "1"), (1, [0], 0, 2, "0"), (1, [1], 1, 1, "1"),
    (4, [0, 1, 0, 0], 2, 4, "1"), (4, [0, 1, 0, 0], 4, 4, "0"),
]:
    expr = f"replace(({copied_word}),n,{width})"
    for index, bit in enumerate(bindings):
        expr = f"replace(({expr}),s_{index},{bit})"
    assert data(f"quantum:replace(({expr}),s,bitstring({value},{label_width}))")["copy_text"] == expected
assert b"zero or one" in run(f"quantum:replace(({word}),s_1,2)", "--json", success=False).stderr

# Shared membership distributes across probes only where commas are not arguments.
for expression, expected in [
    (r"1,2,3\in\{3,1,2\}", "1"), (r"1,2,3\in\{1,3\}", "0"),
    (r"1,2\notin\{3\}", "1"), (r"1,2\notin\{1\}", "0"),
    (r"vector(3,1\in\{1\})", "vector(3,1)"),
    (r"vector((3,1\in\{1\}),4)", "vector(0,4)"),
    (r"(1,2\in\{1,2\}) and (2,3\in\{1,2\})", "0"),
]:
    assert data("quantum:" + expression)["copy_text"] == expected, expression

# A total function must have one output per source and stay inside the codomain.
for graph, domain, target, expected in [
    ("tuple(1,2),tuple(2,2)", "2,1", "2,3", "1"),
    ("tuple(1,2)", "1,2", "2,3", "0"),
    ("tuple(1,2),tuple(2,3)", "1", "2,3", "0"),
    ("tuple(1,2),tuple(1,3)", "1", "2,3", "0"),
    ("tuple(1,2)", "1", "3", "0"),
    ("", "", "", "1"),
]:
    signature = rf"f:\{{{domain}\}} \to \{{{target}\}}"
    expr = f"replace(({signature}),f,qset(vector({graph})))"
    assert data("quantum:" + expr)["copy_text"] == expected, expr

# Biconditional has lower precedence than disjunction and accepts grouped predicates.
for lhs in (0, 1):
    for rhs in (0, 1):
        assert data(rf"quantum:[{lhs}=1] \Leftrightarrow [{rhs}=1]")["copy_text"] == str(int(lhs == rhs))
assert data(r"quantum:1 \vee 0 \iff 0")["copy_text"] == "0"
assert b"Boolean predicates" in run(r"quantum:2 \iff 0", "--json", success=False).stderr

# Symbolic direct sum keeps its operand domains through Copy and substitution.
symbolic_sum = data(r"quantum:w \oplus s")["copy_text"]
assert data(f"quantum:replace(replace({symbolic_sum},w,6),s,3)")["copy_text"] == "5"
assert data(f"quantum:replace(replace({symbolic_sum},w,bitstring(6,3)),s,bitstring(3,3))")["copy_text"] == "qbitlabel(5,3)"
assert data(f"quantum:replace(replace({symbolic_sum},w,X),s,Z)")["rows"] == 4
assert b"nonnegative integer" in run(r"quantum:w \oplus (-1)", "--json", success=False).stderr

# Equality of bit strings includes their declared width and evaluated bits.
for expression, expected in [
    ("bitstring(1+1,3)=bitstring(2,3)", "1"),
    ("bitstring(2,3)!=bitstring(2,2)", "1"),
    ("bitstring(2,3)=bitstring(1,3)", "0"),
    ("bitstring(2,3)=bitstring(2,3)=bitstring(2,2)", "0"),
    ("replace(bitstring(x,3)=bitstring(2,3),x,2)", "1"),
]:
    assert data("quantum:" + expression)["copy_text"] == expected
# Each complete two-bit table denotes a function graph. Leading zeros are data.
for mask in range(16):
    order = (3, 1, 0, 2)
    rows = [f"f({i:02b}) & = {(mask >> i) & 1}" for i in order]
    table = r"\begin{aligned}" + r"\\".join(rows) + r"\end{aligned}"
    copied = data("quantum:" + table)["copy_text"]
    assert copied.startswith("qset(vector(")
    assert data("quantum:" + copied)["copy_text"] == copied
    queries = [f"member(tuple(bitstring({i},2),{bit}),{copied})" for i in range(4) for bit in range(2)]
    expected = [str(int(bit == ((mask >> i) & 1))) for i in range(4) for bit in range(2)]
    assert data("quantum:vector(" + ",".join(queries) + ")")["copy_text"] == "vector(" + ",".join(expected) + ")"
    applied = f"replace(vector(f(00),f(01),f(10),f(11)),f,{copied})"
    assert data("quantum:" + applied)["copy_text"] == "vector(" + ",".join(str((mask >> i) & 1) for i in range(4)) + ")"
    summed = rf"replace(\sum_{{x\in bitstrings(2)}}{{f(x)}},f,{copied})"
    assert data("quantum:" + summed)["copy_text"] == str(bin(mask).count("1"))
pending = data(f"quantum:replace(f(x),f,{copied})")["copy_text"]
assert pending.startswith("qgraphapply(")
assert data(f"quantum:replace({pending},x,bitstring(2,2))")["copy_text"] == "1"
assert b"no output for this bit string" in run(f"quantum:replace(f(1),f,{copied})", "--json", success=False).stderr
conflict = "qset(vector(tuple(bitstring(0,2),0),tuple(bitstring(0,2),1)))"
assert b"conflicting outputs" in run(f"quantum:replace(f(00),f,{conflict})", "--json", success=False).stderr
# Multi-bit outputs are strings too: their leading zeros and widths survive lookup.
word_table = r"\begin{aligned}g(00)&=001\\g(01)&=100\\g(10)&=000\\g(11)&=001\end{aligned}"
word_graph = data("quantum:" + word_table)["copy_text"]
assert data("quantum:" + word_graph)["copy_text"] == word_graph
image = data(r"quantum:\operatorname{range}(f)")["copy_text"]
assert data(f"quantum:replace({image},f,{word_graph})")["copy_text"] == "qset(vector(qbitlabel(1,3),qbitlabel(4,3),qbitlabel(0,3)))"
assert data(r"quantum:\operatorname{range}(vector(2,9,3))")["copy_text"] == "7"
assert data("quantum:qfunctionrange(qset(vector()))")["copy_text"] == "qset(vector())"
assert b"ordered pairs" in run("quantum:qfunctionrange(qset(vector(1)))", "--json", success=False).stderr
assert b"conflicting outputs" in run(f"quantum:qfunctionrange({conflict})", "--json", success=False).stderr
# A set argument to an inverse function denotes its complete inverse image.
preimage = data(r"quantum:g^{-1}(\{bitstring(1,3),bitstring(4,3)\})")["copy_text"]
assert data(f"quantum:replace({preimage},g,{word_graph})")["copy_text"] == "qset(vector(qbitlabel(0,2),qbitlabel(1,2),qbitlabel(3,2)))"
assert data(f"quantum:qpreimage({word_graph},qset(vector()))")["copy_text"] == "qset(vector())"
assert b"conflicting outputs" in run(f"quantum:qpreimage({conflict},qset(vector()))", "--json", success=False).stderr
assert data("quantum:replace(f^(-1)(6),f,2)")["copy_text"] == "3"
for bits, value in (("00",1),("01",4),("10",0),("11",1)):
    assert data(f"quantum:replace(g({bits}),g,{word_graph})")["copy_text"] == f"qbitlabel({value},3)"
    ket = data(rf"quantum:replace(\vert g({bits}) \rangle,g,{word_graph})")
    assert ket["copy_text"] == data(f"quantum:qketstate(bitstring({value},3))")["copy_text"]
assert not data("quantum:" + word_table.replace("=100","=10"))["copy_text"].startswith("qset(")
for changed in (table.replace("f(11)", "g(11)"), table.replace("f(11)", "f(01)"),
                table.replace("f(11)", "f(1)"), table.replace("f(", "i("), table.replace("= 1", "= 2", 1)):
    assert not data("quantum:" + changed)["copy_text"].startswith("qset(")
assert data("quantum:replace(f(11),f,3)")["copy_text"] == "33"

# XOR preserves the width of binary labels before the next dot or ket operation.
for x in range(8):
    query = ",".join(rf"bitvalue(bitstring({x},3) \oplus bitstring({y},3))" for y in range(8))
    expected = "vector(" + ",".join(str(x ^ y) for y in range(8)) + ")"
    assert data("quantum:vector(" + query + ")")["copy_text"] == expected
assert data(r"quantum:bitstring(0,0) \oplus bitstring(0,0)")["copy_text"] == "qbitlabel(0,0)"

# IBM-020 parity relations can simplify to a disjunction in scalar context.
for expr in ("z*x=0", "x=0 and (y=0 or z=0)", "vector(x=0 or y=0, x=0 and y=0)"):
    copied = data("quantum:" + expr)["copy_text"]
    assert " or " in copied
    for prefix in ("", "quantum:"):
        assert data(prefix + copied)["copy_text"] == copied
assert data("quantum:|| |0> ||")["copy_text"] == "1"

# Large exact matrices copied by the GUI must re-enter through quantum notation.
# Start in ordinary calculator syntax so the first evaluation is independent of
# the quantum parser's explicit-entry budget, then compare every copied entry.
entries = ["-1/(2*sqrt(2))", "1/(2*sqrt(2))", "i/3", "-2/7"] + ["0"] * 1020
original_matrix = data("matrix(512,2,[" + ",".join(entries) + "])")
reentered_matrix = data("quantum:" + original_matrix["copy_text"])
for value in (original_matrix, reentered_matrix):
    assert (value["rows"], value["columns"]) == (512, 2)
    assert value["approximate"] is False
assert reentered_matrix["copy_text"] == original_matrix["copy_text"]

# Indexed orthonormal families retain their integer domains through copy.
for flags in ((), ("--approx",)):
    def basis_value(expression):
        return data("quantum:" + expression, *flags)

    for body, expected in (("<b(0)|b(0)>", "1"), ("<b(0)|b(2)>", "0")):
        assert basis_value("orthofamily(" + body + ",B,b,3)")["text"] == expected
    assert basis_value("orthofamily(<b_0|b_2>,B,b,3)")["text"] == "0"
    for expression in (
        "orthofamily(orthobasis(<red|blue>,Colors,[|red>,|blue>]),B,b,n)",
        "orthobasis(orthofamily(<b(0)|b(1)>,B,b,3),Colors,[|red>,|blue>])",
        "orthobasis(orthobasis(<red|blue>,Other,[|green>,|yellow>]),Colors,[|red>,|blue>])",
        "orthofamily(orthofamily(<b(0)|b(1)>,C,c,3),B,b,3)",
    ):
        assert basis_value(expression)["text"] == "0"
    for vectors in (("[1;0;0]", "[0;1;0]", "[0;0;1]"),
                    ("[1;1]/sqrt(2)", "[1;-1]/sqrt(2)"),
                    ("[1;i]/sqrt(2)", "[1;-i]/sqrt(2)")):
        size = len(vectors)
        complete = basis_value("+".join("density(" + v + ")" for v in vectors))
        assert complete["rows"] == complete["columns"] == size
        assert [[complex(cell.replace("i", "j").replace("−", "-")) for cell in row] for row in complete["cells"]] == [[int(j == k) for k in range(size)] for j in range(size)]
        for j, left in enumerate(vectors):
            for k, right in enumerate(vectors):
                assert complex(basis_value("(" + left + ")†*(" + right + ")")["text"].replace("i", "j").replace("−", "-")) == int(j == k)
    inner_finite = basis_value("orthofamily(orthobasis(|b_1>,C,[|b_0>,|b_1>]),B,b,1)")
    assert "qorthoket" in inner_finite["copy_text"] and "qorthofamilyket" not in inner_finite["copy_text"]
    inner_indexed = basis_value("orthobasis(orthofamily(|b_1>,B,b,3),C,[|b_0>,|b_1>])")
    assert "qorthofamilyket" in inner_indexed["copy_text"] and "qorthoket" not in inner_indexed["copy_text"]
    for body in ("<b(j)|b(k)>", "<b(j)|b(j)>", "|b(j)>"):
        original = basis_value("orthofamily(" + body + ",B,b,n)")
        copied = basis_value(original["copy_text"])
        assert copied["copy_text"] == original["copy_text"]
        assert "qortho" not in copied["display_text"]
        for replacement in ("n,0", "n,-1", "n,3/2", "j,-1", "j,1/2", "j,[0;1]"):
            run("quantum:replace(" + copied["copy_text"] + "," + replacement + ")", "--json", *flags, success=False)
        bounded = basis_value("replace(" + copied["copy_text"] + ",n,3)")["copy_text"]
        run("quantum:replace(" + bounded + ",j,3)", "--json", *flags, success=False)
    delta = basis_value("orthofamily(<b(j)|b(k)>,B,b,n)")["copy_text"]
    assert "qorthodelta" in delta
    assert basis_value("replace(replace(replace(" + delta + ",j,1),k,1),n,3)")["text"] == "1"
    assert basis_value("replace(replace(replace(" + delta + ",j,1),k,2),n,3)")["text"] == "0"
    for body in ("|b(j)><b(j)|", "density(|b(j)>)", "|b_j><b_j|"):
        identity = basis_value("orthofamily(sum(" + body + ",0,n-1,j),B,b,n)")
        assert identity["copy_text"] == "qorthoidentity(n)"
        assert basis_value(identity["copy_text"])["copy_text"] == identity["copy_text"]
        for size in (1, 3):
            actual = basis_value("replace(" + identity["copy_text"] + ",n," + str(size) + ")")
            expected = basis_value("qidentity(" + str(size) + ")")
            assert actual["cells"] == expected["cells"] and actual["rows"] == actual["columns"] == size
        run("quantum:replace(" + identity["copy_text"] + ",n,0)", "--json", *flags, success=False)
    for body, upper in (("|b(j)><b(j)|", "n-2"), ("2|b(j)><b(j)|", "n-1"),
                        ("|b(j)><b(k)|", "n-1"), ("|b(0)><b(0)|", "n-1")):
        result = basis_value("orthofamily(sum(" + body + ",0," + upper + ",j),B,b,n)")
        assert "qorthoidentity" not in result["copy_text"]
    cross = basis_value("orthofamily(|b(j)>,B,b,n)†*orthofamily(|b(j)>,C,b,n)")
    assert "qorthofamilyket" in cross["copy_text"] and "qorthodelta" not in cross["copy_text"]
    assert basis_value(cross["copy_text"])["copy_text"] == cross["copy_text"]
    for expression in (
        "orthofamily(|b(j)>,B,b,0)", "orthofamily(|b(-1)>,B,b,n)",
        "orthofamily(|b(j)>,B,b,n)†*orthofamily(|b(j)>,B,b,3)",
        "orthofamily(|b(j)>,B,b,n)†*orthofamily(|c(j)>,B,c,n)",
    ):
        run("quantum:" + expression, "--json", *flags, success=False)

# Explicit operator domains survive canonical copy and delayed substitution.
for flags in ((), ("--approx",)):
    for property_name, valid, invalid in (
        ("unitary", "[0,i;i,0]", "[1,0;0,2]"),
        ("hermitian", "[1,i;-i,2]", "[1,1;0,1]"),
        ("projector", "[1,1;1,1]/2", "[1,0;0,2]"),
    ):
        original = data("quantum:operatorparam(A,2," + property_name + ")", *flags)
        copied = data("quantum:" + original["copy_text"], *flags)
        assert copied["copy_text"] == original["copy_text"]
        assert "operatorparam" in copied["copy_text"]
        for expression in ("operatorparam(A,2," + property_name + ")", copied["copy_text"]):
            actual = data("quantum:replace(" + expression + ",A," + valid + ")", *flags)
            expected = data("quantum:" + valid, *flags)
            assert actual["cells"] == expected["cells"] and actual["rows"] == 2
            run("quantum:replace(" + expression + ",A," + invalid + ")", "--json", *flags, success=False)
            run("quantum:replace(" + expression + ",A,identity(3))", "--json", *flags, success=False)
    delayed = data("quantum:operatorparam([x,0;0,1],2,unitary)", *flags)
    assert "operatorparam" in delayed["copy_text"]
    run("quantum:replace(" + delayed["copy_text"] + ",x,2)", "--json", *flags, success=False)
    assert data("quantum:replace(" + delayed["copy_text"] + ",x,1)", *flags)["cells"] == [["1", "0"], ["0", "1"]]

# Simplified unitary identities keep their premise through copy/substitution.
for flags in ((), ("--approx",)):
    domain = "operatorparam(A,2,unitary)"
    for expression in ("adjoint(" + domain + ")*" + domain,
                       domain + "*adjoint(" + domain + ")"):
        result = data("quantum:" + expression, *flags)
        assert "qunitaryidentity" in result["copy_text"]
        assert result["display_text"] == "I_{2}  (A unitary; dimension 2)"
        copied = data("quantum:" + result["copy_text"], *flags)
        assert copied["copy_text"] == result["copy_text"]
        for invalid in ("[1,0;0,2]", "identity(3)"):
            run("quantum:replace(" + copied["copy_text"] + ",A," + invalid + ")", "--json", *flags, success=False)
        assert data("quantum:replace(" + copied["copy_text"] + ",A,[0,1;1,0])", *flags)["cells"] == [["1", "0"], ["0", "1"]]
    for property_name in ("hermitian", "projector"):
        domain = "operatorparam(A,2," + property_name + ")"
        assert data("quantum:adjoint(" + domain + ")", *flags)["copy_text"] == data("quantum:" + domain, *flags)["copy_text"]
    projector = "operatorparam(A,2,projector)"
    square = data("quantum:" + projector + "*" + projector, *flags)
    assert square["copy_text"] == data("quantum:" + projector, *flags)["copy_text"]
    run("quantum:replace(" + square["copy_text"] + ",A,[1,0;0,2])", "--json", *flags, success=False)
    symbolic = data("quantum:adjoint(operatorparam(A,n,unitary))*operatorparam(A,n,unitary)", *flags)
    assert "qunitaryidentity" in symbolic["copy_text"] and "dimension n" in symbolic["display_text"]
    for invalid_dimension in ("0", "-1", "1/2"):
        run("quantum:replace(" + symbolic["copy_text"] + ",n," + invalid_dimension + ")", "--json", *flags, success=False)
    singleton = data("quantum:adjoint(operatorparam(A,1,unitary))*operatorparam(A,1,unitary)", *flags)
    assert "qunitaryidentity" in singleton["copy_text"]
    assert data("quantum:replace(" + singleton["copy_text"] + ",A,identity(1))", *flags)["cells"] == [["1"]]
    middle = data("quantum:adjoint(operatorparam(A,2,unitary))*matrixparam(B,2,2)*operatorparam(A,2,unitary)", *flags)
    assert "qunitaryidentity" not in middle["copy_text"] and "'B'" in middle["copy_text"]
    run("quantum:adjoint(operatorparam(A,2,unitary))*operatorparam(A,3,unitary)", "--json", *flags, success=False)

# The editor can declare properties without rewriting typed symbol occurrences.
for flags in ((), ("--approx",)):
    unitary = data("quantum:operatorassume(adjoint(A)*A,A,2,unitary)", *flags)
    assert "qunitaryidentity" in unitary["copy_text"]
    assert data("quantum:operatorassume(adjoint(A),A,2,hermitian)", *flags)["copy_text"] == data("quantum:operatorparam(A,2,hermitian)", *flags)["copy_text"]
    assert data("quantum:operatorassume(A*A,A,2,projector)", *flags)["copy_text"] == data("quantum:operatorparam(A,2,projector)", *flags)["copy_text"]
    for body in ("|A>", "<A|A>", "operatorparam(A,3,hermitian)", "matrixparam(A,3,3)"):
        assert data("quantum:operatorassume(" + body + ",A,2,unitary)", *flags)["copy_text"] == data("quantum:" + body, *flags)["copy_text"]
    inner = "operatorassume(adjoint(A),A,2,hermitian)"
    assert data("quantum:operatorassume(" + inner + ",A,2,unitary)", *flags)["copy_text"] == data("quantum:" + inner, *flags)["copy_text"]
    for expression in ("operatorassume(1,A,0,unitary)", "operatorassume(1,A,2,invalid)", "operatorassume(1,H,2,unitary)"):
        run("quantum:" + expression, "--json", *flags, success=False)

# .NET Framework may prepend a UTF-8 BOM when opening redirected stdin.
# Accept one transport preamble, not repeated or truncated protocol prefixes.
for mode, request in (("--exact-circuit", "QEXACT1\n0\n0\n0\n0\n"),
                      ("--sample", "QSAMPLE2\n0\n10\n1731\n0\n0\n0\n")):
    plain = run(request, mode)
    assert run("\ufeff" + request, mode).stdout == plain.stdout
    assert not run("\ufeff\ufeff" + request, mode, success=False).stdout
    assert not run("\ufeff" + request[:5], mode, success=False).stdout

# A register family preserves bit substitutions before its width is supplied.
for flags in ((), ("--approx",)):
    family = '|x_(n-1) ... x_0>'
    symbolic = data("quantum:" + family, *flags)
    copied = data("quantum:" + symbolic["copy_text"], *flags)
    assert copied["copy_text"] == symbolic["copy_text"]
    assert "qregisterfamily" not in symbolic["display_text"] and "⋯" in symbolic["display_text"]
    assert data(r"quantum:\vert x_{n-1}\cdots x_0\rangle", *flags)["copy_text"] == symbolic["copy_text"]
    annotated = data("quantum:replace(|x_(n-1) ... x_1 x_0>,x_0,1)", *flags)
    assert "x_1 present" in annotated["display_text"] and "x_0 = 1" in annotated["display_text"]
    roundtrip = data("quantum:" + annotated["copy_text"], *flags)
    assert roundtrip["display_text"] == annotated["display_text"]
    bra = data("quantum:replace(<x_(n-1) ... x_1 x_0|,x_0,1)", *flags)
    assert "x_0 = 1" in bra["display_text"] and "x_1 present" in bra["display_text"]
    for expression, expected in (
        ("replace(replace(replace(" + family + ",x_0,1),x_1,0),n,2)", "|01>"),
        ("replace(replace(replace(" + family + ",n,2),x_0,1),x_1,0)", "|01>"),
        ("replace(replace(replace(" + family + ",x_0,x_0+1),x_0,0),n,1)", "|1>"),
        ("replace(replace(replace(|x_(n-1) ... x_1 x_0>,x_1,0),x_0,1),n,2)", "|01>"),
    ):
        actual = data("quantum:" + expression, *flags)
        reference = data("quantum:" + expected, *flags)
        assert (actual["rows"], actual["columns"], actual["cells"]) == (
            reference["rows"], reference["columns"], reference["cells"]
        ), (expression, flags, actual, reference)
    # Empty registers are the one-dimensional tensor identity. Wide registers
    # retain a symbolic family until their bits and a manageable width are known.
    empty = data("quantum:replace(" + family + ",n,0)", *flags)
    assert (empty["rows"], empty["columns"], empty["cells"]) == (1, 1, [["1"]])
    empty_copy = data(empty["copy_text"], *flags)
    assert (empty_copy["rows"], empty_copy["columns"], empty_copy["cells"]) == (1, 1, [["1"]])
    wide = data("quantum:replace(" + family + ",n,11)", *flags)
    assert wide["rows"] == wide["columns"] == 0 and wide["cells"] == []
    assert "x_10" in wide["display_text"] and "qregisterfamily" not in wide["display_text"]
    wide_copy = data(wide["copy_text"], *flags)
    assert wide_copy["copy_text"] == wide["copy_text"]
    assert wide_copy["display_text"] == wide["display_text"]
    for expression in (
        "replace(" + family + ",x_0,2)",
        "replace(" + family + ",n,-1)",
        "replace(" + family + ",n,1/2)",
        "replace(replace(" + family + ",x_2,1),n,2)",
        "replace(|x_(n-1) ... x_1 x_0>,n,1)",
        "|x_1 ... x_2 x_1 x_0>",
    ):
        rejected = run("quantum:" + expression, "--json", *flags, success=False)
        assert rejected.returncode == 2 and not rejected.stdout

    # Independent two-bit Hadamard amplitudes: (-1)^(x dot y) / 2.
    for x in range(4):
        expression = "replace(replace(replace(H^{\\otimes n}|x_(n-1) ... x_0>,n,2),x_1," + str(x >> 1) + "),x_0," + str(x & 1) + ")"
        actual = data("quantum:" + expression, *flags)
        expected = [[Decimal("-0.5" if ((x & y).bit_count() % 2) else "0.5")] for y in range(4)]
        cells = [[Decimal(cell.replace("−", "-")) for cell in row] for row in actual["cells"]]
        assert (actual["rows"], actual["columns"], cells) == (4, 1, expected), (expression, actual, expected)

# Original M11-T2, actual ordinary Copy, both binding orders and every signed
# Walsh column for widths one through three. The source does not write x_1,
# so width one must collapse to one factor rather than duplicating x_0.
hadamard_family = r"\bigl(H \vert x_{n-1} \rangle \bigr) \otimes \cdots \otimes \bigl(H \vert x_{0} \rangle \bigr)"


def hadamard_data(expression):
    result = run(expression, "--json")
    assert not result.stderr, (expression, result.stderr)
    value = json.loads(result.stdout.decode("utf-8"))
    assert value["approximate"] is False
    return value


hadamard_symbolic = hadamard_data("quantum:" + hadamard_family)
hadamard_copy = hadamard_data(hadamard_symbolic["copy_text"])
assert hadamard_data(hadamard_copy["copy_text"])["copy_text"] == hadamard_copy["copy_text"]
for width in range(1, 4):
    for x in range(1 << width):
        signs = [str(-1 if (x & y).bit_count() % 2 else 1) for y in range(1 << width)]
        size = str(1 << width)
        reference = hadamard_data("matrix(" + size + ",1,[" + ",".join(signs) + "])/sqrt(" + size + ")")
        for source, width_first in ((hadamard_family, True), (hadamard_copy["copy_text"], False)):
            bindings = [("x_" + str(bit), (x >> bit) & 1) for bit in range(width)]
            bindings.insert(0 if width_first else len(bindings), ("n", width))
            expression = source
            for name, value in bindings:
                expression = "replace(" + expression + "," + name + "," + str(value) + ")"
            actual = hadamard_data("quantum:" + expression)
            copied = hadamard_data(actual["copy_text"])
            for value in (actual, copied):
                assert (value["rows"], value["columns"], value["cells"]) == (
                    1 << width, 1, reference["cells"]
                ), (width, x, width_first, value, reference)
empty_product = hadamard_data("quantum:qmul(qidentity(1),qidentity(1))")
for width in (0, 11):
    actual = hadamard_data("quantum:replace(" + hadamard_copy["copy_text"] + ",n," + str(width) + ")")
    copied = hadamard_data(actual["copy_text"])
    for value in (actual, copied):
        if width == 0:
            assert value["copy_text"] == empty_product["copy_text"] == "1"
            assert (value["rows"], value["columns"], value["cells"]) == (
                empty_product["rows"], empty_product["columns"], empty_product["cells"])
        else:
            assert value["rows"] == value["columns"] == 0 and value["cells"] == []
            assert "x_" in value["display_text"] and "11" in value["display_text"]
            for internal in ("qregisterfamily", "qmatrix", "qpower", "qtensorpow"):
                assert internal not in value["display_text"], value
    assert copied["copy_text"] == actual["copy_text"]
for name, value in (("n", "-1"), ("n", "3/2"), ("x_0", "2"), ("x_0", "-1"), ("x_0", "1/2")):
    rejected = run("quantum:replace(" + hadamard_copy["copy_text"] + "," + name + "," + value + ")", "--json", success=False)
    assert rejected.returncode == 2 and not rejected.stdout and rejected.stderr

# Tensor powers retain their matrix and count constraints until substitution.
for flags in ((), ("--approx",)):
    for expression, resolved, expected in (
        (r"H^{\otimes n}", "n,2", "tensor(H,H)"),
        ("tensorpow(|0>,n)", "n,2", "|00>"),
        ("tensorpow(<0|,n)", "n,2", "<00|"),
    ):
        symbolic = data("quantum:" + expression, *flags)
        assert "qtensorpow" in symbolic["copy_text"]
        assert "qtensorpow" not in symbolic["display_text"]
        copied = data("quantum:" + symbolic["copy_text"], *flags)
        assert copied["display_text"] == symbolic["display_text"], (expression, flags, symbolic, copied)
        assert "qmatrix" not in copied["display_text"] and "qpower" not in copied["display_text"]
        actual = data("quantum:replace((" + copied["copy_text"] + ")," + resolved + ")", *flags)
        reference = data("quantum:" + expected, *flags)
        assert (actual["rows"], actual["columns"], actual["cells"]) == (
            reference["rows"], reference["columns"], reference["cells"]
        ), (expression, flags, actual, reference)
        for width in (0, 11):
            retained = data("quantum:replace((" + copied["copy_text"] + "),n," + str(width) + ")", *flags)
            reentered = data(retained["copy_text"], *flags)
            for value in (retained, reentered):
                if width == 0:
                    assert (value["rows"], value["columns"], value["cells"]) == (1, 1, [["1"]])
                else:
                    assert value["rows"] == value["columns"] == 0 and value["cells"] == []
                    assert "qtensorpow" in value["copy_text"] and "qtensorpow" not in value["display_text"]
            assert reentered["copy_text"] == retained["copy_text"]
        for invalid in ("-1", "1/2"):
            rejected = run("quantum:replace((" + copied["copy_text"] + "),n," + invalid + ")",
                           "--json", *flags, success=False)
            assert rejected.returncode == 2 and not rejected.stdout
            assert b"Tensor power requires a nonnegative integer exponent" in rejected.stderr
    for expression in ("tensorpow(2,n)", "tensorpow(2,0)"):
        rejected = run("quantum:" + expression, "--json", *flags, success=False)
        assert rejected.returncode == 2 and not rejected.stdout
        assert b"requires a matrix" in rejected.stderr
    for expression in ("tensorpow(basis(x,2),-1)", "tensorpow(H,[1,2])"):
        rejected = run("quantum:" + expression, "--json", *flags, success=False)
        assert rejected.returncode == 2 and not rejected.stdout
        assert b"Tensor power requires a nonnegative integer exponent" in rejected.stderr
    for count, expected in (("0", "matrix(1,1,[1])"), ("1", "|1>"), ("2", "|11>")):
        symbolic = data("quantum:tensorpow(basis(x,2),n)", *flags)
        copied = data("quantum:" + symbolic["copy_text"], *flags)
        resolved = "replace(replace((" + copied["copy_text"] + "),n," + count + "),x,1)"
        value = data("quantum:" + resolved, *flags)
        reference = data("quantum:" + expected, *flags)
        assert (value["rows"], value["columns"], value["cells"]) == (
            reference["rows"], reference["columns"], reference["cells"]
        ), (count, flags, value, reference)
        rejected = run("quantum:replace(replace((" + copied["copy_text"] + "),n," + count + "),x,2)",
                       "--json", *flags, success=False)
        assert rejected.returncode == 2 and not rejected.stdout
        assert b"basis(index,dimension)" in rejected.stderr

# Known register shapes reject contradictions before symbolic bits are bound.
for flags in ((), ("--approx",)):
    for expression in (
        "H|x_1 x_0>", "H*|x_1 x_0>", "|x_1 x_0>+|0>",
        "<0|x_1 x_0>", "trace(|x_1 x_0>)",
        "H*(|x_1>_2|0>)",
        "replace(|k>_n+|0>,n,4)",
    ):
        rejected = run("quantum:" + expression, "--json", *flags, success=False)
        assert rejected.returncode == 2 and not rejected.stdout
        assert b"incompatible declared matrix dimensions" in rejected.stderr
    for expression in (
        "tensor(H,H)|x_1 x_0>", "|x_1>_2|0>", "<x_1|_2<0|",
        "|x_1 x_0><0|", "|k>_n+|0>",
    ):
        symbolic = data("quantum:" + expression, *flags)
        assert symbolic["copy_text"]
        copied = data("quantum:" + symbolic["copy_text"], *flags)
        # Re-entry may normalize constructor names; compare the resolved shape
        # and values rather than requiring identical serialization.
        bound = lambda value: "replace(replace(replace(replace((" + value + "),x_1,1),x_0,0),n,2),k,1)"
        actual = data("quantum:" + bound(copied["copy_text"]), *flags)
        expected = data("quantum:" + bound(expression), *flags)
        assert (actual["rows"], actual["columns"], actual["cells"]) == (
            expected["rows"], expected["columns"], expected["cells"]
        ), (expression, flags, actual, expected)
    for expression in (
        "norm(vec(replace(tensor(H,H)|x_1 0>,x_1,1)-tensor(H,H)|10>))",
        "norm(vec(replace(|x_1>_2|0>,x_1,1)-|10>))",
        "norm(vec(replace(<x_1|_2<0|,x_1,1)-<10|))",
        "norm(vec(replace(replace(|k>_n+|0>,n,2),k,1)-(|1>+|0>)))",
    ):
        value = data("quantum:" + expression, *flags)["text"]
        assert Decimal(value.replace("−", "-")) == 0, (expression, flags, value)

# Copying deferred functions must preserve nested matrix/vector separators.
for flags in ((), ("--approx",)):
    for expression in (
        "tensor(H,H)|x_1 x_0>",
        "|x_1>_2|0>",
        "<x_1|_2<0|",
        "|x_1 x_0><0|",
        "|k>_n+|0>",
    ):
        original = data("quantum:" + expression, *flags)
        copied = data("quantum:" + original["copy_text"], *flags)
        # Compare evaluated values, not spelling: canonical wrappers can change
        # on re-entry without changing the state or its basis constraints.
        substitutions = lambda value: "replace(replace(replace(replace((" + value + "),x_1,1),x_0,0),n,2),k,1)"
        expected = data("quantum:" + substitutions(expression), *flags)
        actual = data("quantum:" + substitutions(copied["copy_text"]), *flags)
        assert (actual["rows"], actual["columns"], actual["cells"]) == (
            expected["rows"], expected["columns"], expected["cells"]
        ), (expression, flags, actual, expected)
        bad = "replace((" + copied["copy_text"] + ")," + ("k" if expression.startswith("|k>") else "x_1") + ",-1)"
        rejected = run("quantum:" + bad, "--json", *flags, success=False)
        assert rejected.returncode == 2 and not rejected.stdout
        assert b"basis(index,dimension)" in rejected.stderr

# Indexed register factors stay symbolic without losing their one-bit domains.
for flags in ((), ("--approx",)):
    for expression in ("|x_1 x_0>", r"\vert x_1 x_0\rangle",
                       "|0 x_1 x_0>", "<x_1 x_0|"):
        symbolic = data("quantum:" + expression, *flags)
        copied = data("quantum:" + symbolic["copy_text"], *flags)
        assert "qbasis" in copied["copy_text"] and "qtensor" in copied["copy_text"]
        resolved = "replace(replace((" + copied["copy_text"] + "),x_1,1),x_0,0)"
        expected = "<10|" if expression.startswith("<") else "|010>" if expression.startswith("|0 ") else "|10>"
        assert data("quantum:norm(vec((" + resolved + ")-(" + expected + ")))", *flags)["text"] == "0"
        for invalid in ("-1", "2", "1/2"):
            rejected = run("quantum:replace((" + copied["copy_text"] + "),x_1," + invalid + ")",
                           "--json", *flags, success=False)
            assert rejected.returncode == 2 and not rejected.stdout
            assert b"basis(index,dimension)" in rejected.stderr
    for expression in ("tensor(basis(x_1,2),2)", "tensor(2,basis(x_1,2))"):
        rejected = run("quantum:" + expression, "--json", *flags, success=False)
        assert rejected.returncode == 2 and not rejected.stdout
        assert b"Quantum operation requires two matrices." in rejected.stderr

# Symbolic binary labels retain validation until values and widths are supplied.
for flags in ((), ("--approx",)):
    for expression in [
        "bitstring(x,n)", "bitvalue(bitstring(x,n))",
        "qketstate(bitstring(x,n))",
        "bitxor(bitstring(x,n),bitstring(y,n))",
        "bitdot(bitstring(x,n),bitstring(y,n))",
        "qketstate(vector(bitstring(x,n),bitstring(y,n)))",
        "qketstate(bitstring(x,n))-qketstate(bitstring(x,n))",
        "cardinality(vector(bitstring(x,n),bitstring(y,n)))",
        "member(bitstring(x,n),vector(bitstring(y,n)))",
        "qsumset(1,vector(bitstring(x,n),bitstring(y,n)),k)",
    ]:
        value=data("quantum:"+expression,*flags)
        assert "qbitlabel" in value["copy_text"]
        assert "qbitlabel" not in value["display_text"]
        copied=data("quantum:"+value["copy_text"],*flags)
        assert "qbitlabel" in copied["copy_text"]
        run("quantum:replace(replace(("+copied["copy_text"]+"),x,8),n,2)","--json",*flags,success=False)
    wide = data("quantum:bitstring(x,11)", *flags)
    copied_wide = data(wide["copy_text"], *flags)
    assert copied_wide["copy_text"] == wide["copy_text"]
    assert "bitstring(x, 11)" == wide["display_text"]
    assert data("quantum:bitvalue(replace(" + copied_wide["copy_text"] + ",x,2047))", *flags)["text"] == "2047"
    rejected = run("quantum:replace(" + copied_wide["copy_text"] + ",x,2048)", "--json", *flags, success=False)
    assert rejected.returncode == 2 and not rejected.stdout and rejected.stderr
    for expression in [
        "bitstring(-1,n)", "bitstring(1/2,n)", "bitstring(x,-1)",
        "bitstring(x,1/2)", "bitstring(1,0)",
        "bitxor(bitstring(x,2),bitstring(y,3))",
        "bitdot(bitstring(x,2),bitstring(y,3))",
        "bitxor(bitstring(x,n),[0,2])",
        "qketstate(vector(bitstring(x,2),bitstring(y,3)))",
    ]:
        run("quantum:"+expression,"--json",*flags,success=False)
    for expression in [
        "norm(vec(replace(replace(qketstate(bitstring(x,n)),x,1),n,3)-|001>))",
        "replace(replace(bitvalue(bitstring(x,n)),x,1),n,3)-1",
        "norm(vec(replace(replace(replace(qketstate(bitxor(bitstring(x,n),bitstring(y,n))),x,1),y,2),n,2)-|11>))",
        "replace(replace(replace(bitdot(bitstring(x,n),bitstring(y,n)),x,1),y,3),n,2)-1",
        "norm(vec(replace(replace(replace(qketstate(vector(bitstring(x,n),bitstring(y,n))),x,0),y,3),n,2)-|Phi+>))",
        "replace(replace(bitvalue(bitstring(x,n)),x,0),n,0)",
    ]:
        value=data("quantum:"+expression,*flags)
        assert abs(Decimal(value["text"].replace("−","-")))<Decimal("1e-12"),(expression,value)

    for expression in ["cardinality(vector(bitstring(x,n),bitstring(y,n)))", "member(bitstring(x,n),vector(bitstring(y,n)))", "qsumset(1,vector(bitstring(x,n),bitstring(y,n)),k)"]:
        copied=data("quantum:"+expression,*flags)["copy_text"]
        value=data("quantum:replace(replace(replace(("+copied+"),x,1),y,1),n,2)",*flags)
        assert Decimal(value["text"])==1

# The built-in GHZ label is the normalized, positive-phase three-qubit state.
for flags in ((), ("--approx",)):
    ghz = data("quantum:|GHZ>", *flags)
    assert (ghz["rows"], ghz["columns"]) == (8, 1)
    for expression, expected in [
        ("<GHZ|GHZ>", "1"),
        ("norm(vec(|GHZ>-(|000>+|111>)/sqrt(2)))", "0"),
        ("norm(vec(|GHZ><GHZ|-density((|000>+|111>)/sqrt(2))))", "0"),
        ("|<000|GHZ>|^2", "0.5"),
        ("|<111|GHZ>|^2", "0.5"),
        ("<001|GHZ>", "0"),
        ("norm(vec(<GHZ|-qdag((|000>+|111>)/sqrt(2))))", "0"),
    ]:
        value = data("quantum:" + expression, *flags)
        if flags:
            assert abs(Decimal(value["text"].replace("−", "-")) - Decimal(expected)) < Decimal("1e-12")
        elif expected == "0.5":
            assert value["text"] in ("0.5", "1/2", "1 ∕ 2")
        else:
            assert value["text"] == expected, (expression, flags, value)
    assert data("quantum:" + ghz["copy_text"], *flags)["cells"] == ghz["cells"]
    assert data("quantum:|GHZ⟩", *flags)["cells"] == ghz["cells"]

# Complete declared-basis projector sums are identity; subsets are not.
def basis_completeness_result(expression,approx=False,reject=False):
    flags=("--approx",) if approx else ()
    if reject:
        rejected=run("quantum:"+expression,"--json",*flags,success=False)
        assert rejected.returncode==2 and not rejected.stdout and rejected.stderr
        return None
    return data("quantum:"+expression,*flags)

for approx in (False,True):
    for n in range(1,5):
        labels=["state_"+str(k) for k in range(n)]
        declaration="["+",".join("|"+label+">" for label in labels)+"]"
        body="+".join("|"+label+"><"+label+"|" for label in reversed(labels))
        value=basis_completeness_result("orthobasis("+body+",B,"+declaration+")",approx)
        assert value["cells"]==[["1" if i==j else "0" for j in range(n)] for i in range(n)]
        assert basis_completeness_result(value["copy_text"],approx)["cells"]==value["cells"]
    value=basis_completeness_result("orthobasis(density(|red>)+density(|blue>),B,[|red>,|blue>])",approx)
    assert value["cells"]==[["1","0"],["0","1"]]
    for body,labels in [
        ("|red><red|","[|red>,|blue>]"),
        ("|red><red|+|red><red|","[|red>,|blue>]"),
        ("|red><blue|+|blue><red|","[|red>,|blue>]"),
        ("2*|red><red|+|blue><blue|","[|red>,|blue>]"),
        ("|red><red|+|blue><blue|","[|red>,|blue>,|green>]"),
    ]:
        value=basis_completeness_result("orthobasis("+body+",B,"+labels+")",approx);assert value["rows"]==0
        assert basis_completeness_result(value["copy_text"],approx)["copy_text"]==value["copy_text"]
    value=basis_completeness_result("orthobasis(|red><red|,B,[|red>,|blue>])+orthobasis(|blue><blue|,C,[|red>,|blue>])",approx)
    assert value["rows"]==0
    basis_completeness_result("orthobasis(|red><red|,B,[|red>,|blue>])+orthobasis(|green><green|,B,[|red>,|green>])",approx,True)

# Fourier basis action becomes a finite sum without discarding its domain.
for flags in [(), ("--approx",)]:
    for operator in ['QFT_N','QFT_N†','QFT_N^(-1)']:
        expanded=data('quantum:'+operator+'|x>_N',*flags)
        assert 'qfourierdomain' in expanded['copy_text'] and 'qsum(' in expanded['copy_text']
        assert '∑' in expanded['display_text'] and '∈ ℤ' in expanded['display_text']
        copied=data('quantum:'+expanded['copy_text'],*flags)
        assert '∑' in copied['display_text'] and '∈ ℤ' in copied['display_text']
        for n,x in [(1,0),(2,1),(3,2),(4,1)]:
            substituted='replace(replace(('+expanded['copy_text']+'),N,'+str(n)+'),x,'+str(x)+')'
            reference=operator.replace('_N','_'+str(n))+'|'+str(x)+'>_'+str(n)
            residual=data('quantum:norm(('+substituted+')-('+reference+'))',*flags)['text'].replace('−','-')
            assert all(abs(Decimal(part.rstrip('i')))<Decimal('1e-25') for part in residual.split(' + '))
        wide = data('quantum:replace(replace(('+expanded['copy_text']+'),N,65),x,0)', *flags)
        wide_copy = data(wide['copy_text'], *flags)
        for value in (wide, wide_copy):
            assert value['rows'] == value['columns'] == 0 and value['cells'] == []
            assert 'qfourierdomain' in value['copy_text'] and '65' in value['copy_text']
            assert '∑' in value['display_text'] and 'qfourierdomain' not in value['display_text']
        assert wide_copy['copy_text'] == wide['copy_text']
        for n,x in [('4','4'),('4','-1'),('4','1/2'),('0','0'),('65','65'),('4','i')]:
            rejected=run('quantum:replace(replace(('+expanded['copy_text']+'),N,'+n+'),x,'+x+')','--json',*flags,success=False)
            assert rejected.returncode==2 and not rejected.stdout and rejected.stderr
    free=data('quantum:QFT_N|k>_N',*flags)
    for expression in ['norm(replace(replace(('+free['copy_text']+'),N,4),k,1)-QFT_4|1>_4)',
                       'norm(replace(sum(QFT_N|x>_N,0,N-1,x),N,4)-2*|0>_4)']:
        residual=data('quantum:'+expression,*flags)['text'].replace('−','-')
        assert all(abs(Decimal(part.rstrip('i')))<Decimal('1e-25') for part in residual.split(' + '))
    for expression in ['0*(QFT_N|x>_N)','(QFT_N|x>_N)-(QFT_N|x>_N)','QFT_N|qboundindex_fourier_0>_N']:
        guarded=data('quantum:'+expression,*flags)
        symbol='qboundindex_fourier_0' if 'qboundindex_fourier_0' in expression else 'x'
        invalid='replace(replace(('+guarded['copy_text']+'),N,4),'+symbol+',4)'
        rejected=run('quantum:'+invalid,'--json',*flags,success=False)
        assert rejected.returncode==2 and not rejected.stdout and b'index in range' in rejected.stderr
        if symbol!='x':
            residual=data('quantum:norm(replace(replace(('+guarded['copy_text']+'),N,4),'+symbol+',1)-QFT_4|1>_4)',*flags)['text'].replace('−','-')
            assert all(abs(Decimal(part.rstrip('i')))<Decimal('1e-25') for part in residual.split(' + '))
    assert 'qfourierdomain' not in data('quantum:QFT_N|x>',*flags)['copy_text']
    rejected=run('quantum:qfourierdomain(1,0,2)','--json',*flags,success=False)
    assert rejected.returncode==2 and not rejected.stdout and rejected.stderr

# Named orthonormal bases justify only within-basis contractions.
for flags in [(), ("--approx",)]:
    for expression,expected in [
        ("orthobasis(<red|red>,B,[|red>,|blue>])","1"),
        ("orthobasis(<red|blue>,B,[|red>,|blue>])","0"),
        ("orthobasis(<blue|red>,B,[|red>,|blue>])","0"),
        ("orthobasis(<blue|blue>,B,[|red>,|blue>])","1"),
        ("orthobasis(<x|x>,B,[|x>])","1"),
    ]:
        assert data("quantum:"+expression,*flags)["text"]==expected
    for expression in [
        "orthobasis(|red>,B,[|red>,|blue>])",
        "orthobasis(|red>,B,[|red>,|blue>])†*orthobasis(|red>,C,[|red>,|blue>])",
        "<red|red>",
    ]:
        result=data("quantum:"+expression,*flags)
        assert result["rows"]==0 and result["text"] not in ("0","1")
        assert data("quantum:"+result["copy_text"],*flags)["copy_text"]==result["copy_text"]
        if expression.startswith("orthobasis"):
            assert "basis B" in result["display_text"] and "qorthoket" not in result["display_text"]
    for expression in [
        "orthobasis(<red|red>,B,[|red>,|red>])",
        "orthobasis(<red|red>,B,[])",
        "orthobasis(<red|red>,B,[1,2])",
        "orthobasis(|red>,B,[|red>,|blue>])†*orthobasis(|red>,B,[|red>,|green>])",
        'qorthoket("missing","B",vector("red","blue"))',
    ]:
        rejected=run("quantum:"+expression,"--json",*flags,success=False)
        assert rejected.returncode==2 and not rejected.stdout and rejected.stderr

# IBM's Fourier definition uses juxtaposed bound indices in its phase.
for flags in [(), ("--approx",)]:
    rejected=run("quantum:qtexgroupsum(0,1,x,"+"x"*600+")", "--json", *flags, success=False)
    assert rejected.returncode==2 and rejected.stdout==b"" and b"complexity limit" in rejected.stderr

for flags in [(), ("--approx",)]:
    for expression, expected in [
        (r'\sum_{x=0}^{2}\sum_{y=0}^{3} xy',18),
        (r'\sum_{x=0}^{2}{\sum_{y=0}^{3}{xy}}',18),
        ('∑_{x=0}^{2}{∑_{y=0}^{3}{xy}}',18),
        (r'\sum_{i=0}^{2}{ii}',5),
        (r'\sum_{x=0}^{1}{\sum_{y=0}^{1}{\sum_{xy=0}^{2}{xy}}}',12),
        (r'\sum_{x=0}^{1}\sum_{y=0}^{1}\sum_{xy=0}^{2} xy',12),
        (r'\sum_{x=0}^{2}{xx+\sum_{x=0}^{1}{xx}}',8),
        (r'\prod_{x=1}^{3}{xx}',36),
        (r'\sum_{x\in\{0,2,5\}}{xx}',29),
    ]:
        assert Decimal(data('quantum:'+expression,*flags)['text'])==expected
    formula=r'\frac{1}{\sqrt{N}}\sum_{x=0}^{N-1}\sum_{y=0}^{N-1}\omega_N^{xy}|x\rangle\langle y|'
    for dimension in range(1,5):
        expression='frobeniusnorm(replace(replace(('+formula+'),ω_N,exp(2*pi*i/N)),N,'+str(dimension)+')-QFT_'+str(dimension)+')'
        assert abs(Decimal(data('quantum:'+expression,*flags)['text'].replace('−','-')))<Decimal('1e-25')
    symbolic=data(r'quantum:\sum_{x=0}^{N}{xx}',*flags)
    assert Decimal(data('quantum:replace(('+symbolic['copy_text']+'),N,3)',*flags)['text'])==14

# Fourier sums display mathematical notation without changing canonical copy data.
for flags in [(), ("--approx",)]:
    for expression in ['QFT_N|x>_N','sum(exp(2*pi*i*x*k/N)*basis(k,N),0,N-1,k)/sqrt(N)','sum(exp(i*k)*basis(k,N),0,N-1,k)']:
        result=data('quantum:'+expression,*flags)
        assert not any(token in result['display_text'] for token in ['qsum','qexp','qbasis','qboundindex']), result
        assert '⟩_{' in result['display_text'], result
        copied=data('quantum:'+result['copy_text'],*flags)
        if expression=='QFT_N|x>_N':
            assert '∑' in copied['display_text'] and '∈ ℤ' in copied['display_text']
        else:
            assert copied['display_text']==result['display_text']
        difference='replace(('+expression+')-('+result['copy_text']+'),N,4)'
        difference='norm('+('replace('+difference+',x,1)' if re.search(r'\bx\b',expression) else difference)+')'
        parts=data('quantum:'+difference,*flags)['text'].replace('−','-').split(' + ')
        assert all(abs(Decimal(part.rstrip('i')))<Decimal('1e-25') for part in parts)
    result=data('quantum:basis(x,N)†',*flags)
    assert 'N' in result['display_text'] and '†' in result['display_text'], result

# Declared complex Gram matrices are PSD, but need not have full rank.
for flags in [(), ("--approx",)]:
    for gram in ['M†*M','M*M†','M† M']:
        for shape in ['n,n','2,3','3,1']:
            assert Decimal(data('quantum:matrixassume('+gram+'>=0,M,'+shape+')',*flags)['text'])==1
    for expression in ['0<=M†*M','0<=M*M†']:
        assert Decimal(data('quantum:matrixassume('+expression+',M,2,3)',*flags)['text'])==1
    for expression in ['M†*M<0','0>M*M†']:
        assert Decimal(data('quantum:matrixassume('+expression+',M,2,3)',*flags)['text'])==0
    for expression in ['M†*M>0','M†*M<=0','M^T*M>=0','M†*N>=0']:
        result=data('quantum:matrixassume(matrixassume('+expression+',M,2,2),N,2,2)',*flags)
        assert result['text'] not in ('0','1'), result
    assert Decimal(data('quantum:[i,0;0,i]^T*[i,0;0,i]>=0',*flags)['text'])==0

# Workspace matrix declarations must not rewrite labels or local indices.
for flags in [(), ("--approx",)]:
    identity='Tr(α A+β B)-α Tr(A)-β Tr(B)'
    assert Decimal(data('quantum:matrixassume(matrixassume('+identity+',A,n,n),B,n,n)',*flags)['text'])==0
    assert Decimal(data('quantum:matrixassume(sum(A,0,2,A),A,2,2)',*flags)['text'])==3
    for original in ['|A>','<A|A>','matrixparam(A,3,3)']:
        assert data('quantum:matrixassume('+original+',A,2,2)',*flags)['copy_text']==data('quantum:'+original,*flags)['copy_text']
    run('quantum:matrixassume(Tr(M),M1,2,2)',*flags,success=False)
    assert 'M_1' in data('quantum:matrixassume(Tr(M_1),M_1,2,2)',*flags)['copy_text']
    symbolic=data('quantum:matrixassume(Tr(A),A,n,n)',*flags)
    assert data('quantum:matrixassume('+symbolic['copy_text']+',A,n,n)',*flags)['copy_text']==symbolic['copy_text']
    for expression in ['matrixassume(Tr(A),A,2,3)','matrixassume(1,A,0,2)','matrixassume(Tr(X),X,2,2)','matrixassume(i,i,2,2)','matrixassume(matrixassume(Tr(A),A,2,3),A,2,2)','matrixassume(matrixassume(Tr(n),n,2,3),n,2,2)']:
        run('quantum:'+expression,*flags,success=False)

# Trace linearity applies only when declared square shapes justify it.
for flags in [(), ("--approx",)]:
    left='matrixparam(A,n,n)';right='matrixparam(B,n,n)'
    source=r'replace(replace(\operatorname{Tr}(\alpha A+\beta B)-\alpha\operatorname{Tr}(A)-\beta\operatorname{Tr}(B),A,matrixparam(A,n,n)),B,matrixparam(B,n,n))'
    assert Decimal(data('quantum:'+source,*flags)['text'])==0
    for expression in ['Tr(α*'+left+'+β*'+right+')-α*Tr('+left+')-β*Tr('+right+')','Tr('+left+'-'+right+')-Tr('+left+')+Tr('+right+')','Tr(complexparam(z)*'+left+')-complexparam(z)*Tr('+left+')']:
        assert Decimal(data('quantum:'+expression,*flags)['text'])==0,expression
    symbolic=data('quantum:Tr(2*'+left+')',*flags)
    assert data('quantum:'+symbolic['copy_text'],*flags)['copy_text']==symbolic['copy_text']
    value=data('quantum:replace(replace('+symbolic['copy_text']+',n,2),A,identity(2))',*flags)
    assert Decimal(value['text'])==4
    for expression in ['Tr(matrixparam(A,n,n)+matrixparam(B,m,m))','Tr(matrixparam(A,1,2)*matrixparam(B,2,1)+matrixparam(C,1,2)*matrixparam(D,2,1))']:
        assert 'qadd' in data('quantum:'+expression,*flags)['copy_text'],expression
    for expression in ['Tr(0*matrixparam(A,2,3))','0*Tr(5)','Tr(5)-Tr(5)']:
        run('quantum:'+expression,*flags,success=False)

# Declared matrix shapes constrain operations before matrix values are known.
for flags in [(), ("--approx",)]:
    for expression in ['Tr(matrixparam(A,2,3))','matrixparam(A,2,2)+matrixparam(B,3,3)','matrixparam(A,2,3)*matrixparam(B,2,2)','Tr(matrixparam(A,2,3)^T)','Tr(2*matrixparam(A,2,3))','Tr(matrixparam(A,2,3)*matrixparam(B,3,4))']:
        run('quantum:'+expression,*flags,success=False)
    for expression in ['Tr(matrixparam(A,n,n))','matrixparam(A,n,n)+matrixparam(B,m,m)','matrixparam(A,2,3)*matrixparam(B,3,2)']:
        value=data('quantum:'+expression,*flags)
        assert 'matrixparam' in value['copy_text'],value
    value=data('quantum:replace(replace(matrixparam(A,2,2)*matrixparam(B,2,2),A,X),B,X)',*flags)
    assert value['cells']==[['1','0'],['0','1']],value

# Matrix domains survive serialization and validate each substituted axis.
for flags in [(), ("--approx",)]:
    symbolic=data('quantum:matrixparam(A,n,n)',*flags)
    assert 'matrixparam' in symbolic['copy_text'],symbolic
    assert data('quantum:'+symbolic['copy_text'],*flags)['copy_text']==symbolic['copy_text']
    for expression in ['replace(matrixparam(A,2,2),A,X)','replace(replace(matrixparam(A,n,n),n,2),A,X)','replace(replace(matrixparam(A,n,n),A,X),n,2)']:
        value=data('quantum:'+expression,*flags)
        assert value['rows']==value['columns']==2 and value['cells']==[['0','1'],['1','0']],value
    scalar=data('quantum:Tr(replace(matrixparam(A,1,1),A,matrix(1,1,[5])))',*flags)
    assert Decimal(scalar['text'])==5
    for expression in ['matrixparam(A,0,n)','matrixparam(A,n,-1)','matrixparam(A,1.5,2)','replace(matrixparam(A,2,2),A,5)','replace(matrixparam(A,2,2),A,matrix(2,1,[1,0]))','matrixparam(X,n,3)']:
        run('quantum:'+expression,*flags,success=False)

# Explicit quantum matrices retain shape even when both dimensions equal one.
for flags in [(), ("--approx",)]:
    for expression,expected in [('matrix(1,1,[5])',5),('matrix(2-1,2/2,[5])',5),('identity(1)',1)]:
        value=data('quantum:'+expression,*flags)
        assert value['rows']==value['columns']==1 and Decimal(value['cells'][0][0])==expected,value
        copied=data('quantum:'+value['copy_text'],*flags)
        assert copied['rows']==copied['columns']==1 and copied['cells']==value['cells'],copied
        assert Decimal(data('quantum:Tr('+expression+')',*flags)['text'])==expected
    for expression in ['Tr(5)','Tr(matrix(1,2,[1,2]))','matrix(0,1,[5])','matrix(1.5,1,[5])']:
        run('quantum:'+expression,*flags,success=False)

# A sum binds a bare phase-alias label, while explicit +i remains a state.
for flags in [(), ("--approx",)]:
    for expression in ['norm(sum(|i>,0,1,i)-(|0>+|1>))','norm(vec(sum(|i><i|,0,1,i)-I))','norm(sum(|+i>,0,1,i)-2|+i>)','norm(|i>-|+i>)','norm(sum(sum(|i>,0,1,j),0,1,i)-2*(|0>+|1>))','norm(sum(sum(|i>,0,1,i),0,1,i)-2*(|0>+|1>))']:
        assert abs(Decimal(data('quantum:'+expression,*flags)['text']))<Decimal('1e-12'),expression
    symbolic=data('quantum:sum(|i>,0,n-1,i)',*flags)
    assert 'qboundindex' not in symbolic['display_text'],symbolic
    concrete=data('quantum:replace('+symbolic['copy_text']+',n,3)',*flags)
    assert concrete['rows']==3 and concrete['columns']==1 and all(Decimal(row[0])==1 for row in concrete['cells']),concrete

# Local constant-named indices must not capture imaginary units generated by gates.
for flags in [(), ("--approx",)]:
    for expression,expected in [('sum(i,0,2,i)',3),('sum(e,0,2,e)',3),('sum(pi,0,2,pi)',3),('sum(sum(i,0,i,i),0,2,i)',4),('norm(vec(sum(i*Y,0,2,i)-3*Y))',0),('norm(vec(sum(Y,0,2,i)-3*Y))',0),('norm(vec(sum(P(i),0,1,i)-P(0)-P(1)))',0),('abs(sum(i,0,2,i)+i)^2',10),('sum(i^2,0,2,i)',5)]:
        assert abs(Decimal(data('quantum:'+expression,*flags)['text'])-expected)<Decimal('1e-12'),expression
    value=data(r'quantum:\sum_{i=0}^{1}{a_(i,0)}',*flags)
    assert data('quantum:'+value['copy_text'],*flags)['copy_text']==value['copy_text']

for marker in ['\x1c','\x1d']:
    assert data('quantum:1+'+marker+'i')['copy_text']==data('quantum:1+i')['copy_text']

# A comma inside a paired coefficient subscript is not a matrix separator.
for flags in [(), ("--approx",)]:
    source=r'\begin{pmatrix}\alpha_{0,0}&\alpha_{0,1}\\\alpha_{1,0}&\alpha_{1,1}\end{pmatrix}'
    matrix=data('quantum:'+source,*flags)
    expected=data('quantum:qindexedmatrix("α_",1,1,0,0)',*flags)
    assert matrix['rows']==matrix['columns']==2 and matrix['cells']==expected['cells'],matrix
    assert data('quantum:'+matrix['copy_text'],*flags)['cells']==matrix['cells']
    replaced=data('quantum:replace('+source+r',\alpha_{0,1},7)',*flags)
    assert replaced['rows']==replaced['columns']==2 and Decimal(replaced['cells'][0][1])==7,replaced
    assert data('quantum:2a_(0,1)',*flags)['copy_text']==data('quantum:2*a_(0,1)',*flags)['copy_text']
    symbolic=data('quantum:a_(k,l+1)',*flags)
    assert symbolic['display_text'].startswith('a_('),symbolic
    assert data('quantum:'+symbolic['display_text'],*flags)['copy_text']==symbolic['copy_text']
    concrete=data('quantum:replace(replace('+symbolic['copy_text']+',k,2),l,3)',*flags)
    assert concrete['copy_text']==data('quantum:a_(2,4)',*flags)['copy_text']
    for bad in ['a_(0,1/2)','a_(k,1/2)','a_([0,1],2)']:
        assert run('quantum:'+bad,'--json',*flags,success=False).stdout==b''

# Indexed matrix dimensions and paired coefficient labels survive substitution.
for flags in [(), ("--approx",)]:
    expression='qindexedmatrix("a_",m-1,n-1,1,1)'
    symbolic=data('quantum:'+expression,*flags)
    assert symbolic['rows']==symbolic['columns']==0
    concrete=data('quantum:replace(replace('+expression+',m,3),n,2)',*flags)
    assert concrete['rows']==3 and concrete['columns']==2
    assert data('quantum:'+concrete['copy_text'],*flags)['cells']==concrete['cells']
    cell=data('quantum:replace(qindexedmatrix("a_",0,0,0,0),"a_0,0",7)',*flags)
    assert cell['rows']==cell['columns']==1 and Decimal(cell['cells'][0][0])==7
    for bad in ['qindexedmatrix("a_",n,-1,0,0)','qindexedmatrix("a_",-1,n,0,0)','qindexedmatrix("a_",n,1024,0,0)','qindexedmatrix("a_",2,1/2,0,0)','qindexedmatrix("a_",n,2,0,3)','qindexedmatrix("a_",n,m,-1,0)']:
        assert run('quantum:'+bad,'--json',*flags,success=False).stdout==b''

dots = r"\begin{pmatrix}z^1 \cdot t\\z^2 \cdot t\\\vdots\\z^{k} \cdot t\end{pmatrix}"
partial_dots = data(f'quantum:replace(({dots}),"z^2",bitstring(3,2))')["copy_text"]
expr = f'replace(replace(replace(({partial_dots}),k,2),"z^1",bitstring(1,2)),t,bitstring(3,2))'
assert data("quantum:" + expr)["cells"] == [["1"], ["0"]]
for bad in [dots.replace("z^2", "z^3"), dots.replace("z^2", "y^2"),
            dots.replace("t", "x", 1), "qzerocolumnlike(matrix(1,2,[0,0]),1)",
            "qzerocolumnlike(matrix(2,1,[0,0]),3)", "gf2_mul(M,matrix(1,1,[2]))"]:
    run("quantum:" + bad, "--json", success=False)

sample_rows = 'qsamplewordrows("z^",k,n-1,vector(),2)'
pending_rows = data(f'quantum:replace(replace({sample_rows},"z^2_0",1),"z^1",bitstring(0,1))')["copy_text"]
expanded_rows = data(f"quantum:replace(replace({pending_rows},k,2),n,1)")["copy_text"]
for label, value in [('"z^2"', "bitstring(1,2)"), ('"z^1_0"', "0")]:
    expanded_rows = data(f"quantum:replace({expanded_rows},{label},{value})")["copy_text"]
assert expanded_rows == "vector(1,0)"
for bad in ['qsamplewordrows("z^",1,0,vector(),2)', 'qsamplewordrows("z^",k,-1,vector(),2)',
            'qsamplewordrows("z^",2,1,vector(1,0,0,1,0,1),2)',
            'qsamplewordrows("z^",2,0,vector(1,1,3),2)']:
    run("quantum:" + bad, "--json", success=False)

# Sample numbers start at one, while the bit columns run down to zero.
sample_matrix = 'qsamplebitmatrix("z^",k,n-1,2,0)'
sample_display = data("quantum:" + sample_matrix)["display_text"]
assert "⋱" in sample_display
assert data("quantum:" + sample_display)["copy_text"] == data("quantum:" + sample_matrix)["copy_text"]
for bad in [sample_display.replace("z^(2)_0", "z^(1)_0"),
            sample_display.replace("z^(k)_0", "z^(k)_1"),
            sample_display.replace("⋱", "⋮"),
            'qsamplebitmatrix("z^",1,n,2,0)', 'qsamplebitmatrix("z^",k,-1,2,0)']:
    run("quantum:" + bad, "--json", success=False)

# Natural and source-derived matrix patterns evaluate to the same indexed cells.
for flags in [(), ("--approx",)]:
    for expression in ['[a_(0,0), ⋯, a_(0,n-1); ⋮, ⋱, ⋮; a_(m-1,0), ⋯, a_(m-1,n-1)]',r'\begin{pmatrix}a_{0,0}&\cdots&a_{0,n-1}\\[1mm]\vdots&\ddots&\vdots\\a_{m-1,0}&\cdots&a_{m-1,n-1}\end{pmatrix}']:
        symbolic=data('quantum:'+expression,*flags)
        assert '⋱' in symbolic['display_text'] and 'qindexedmatrix' not in symbolic['display_text'],symbolic
        shown=data('quantum:replace(replace('+symbolic['display_text']+',m,3),n,2)',*flags)
        concrete=data('quantum:replace(replace('+expression+',m,3),n,2)',*flags)
        assert shown['cells']==concrete['cells']
        expected=data('quantum:qindexedmatrix("a_",2,1,0,0)',*flags)
        assert concrete['rows']==3 and concrete['columns']==2 and concrete['cells']==expected['cells']
        assert data('quantum:replace(replace('+symbolic['copy_text']+',m,3),n,2)',*flags)['cells']==expected['cells']
        square='replace(replace('+expression+',m,2),n,2)'
        trace=data('quantum:replace(replace(Tr('+square+'),"a_0,0",3),"a_1,1",5)',*flags)
        assert Decimal(trace['text'])==8,trace
        assert run('quantum:replace('+expression+',m,0)','--json',*flags,success=False).stdout==b''

# Indexed column constraints must survive symbolic dimensions and substitution.
for flags in [(), ("--approx",)]:
    descending=data(r"quantum:\begin{pmatrix}s_{n-1}\\\vdots\\s_0\end{pmatrix}", *flags)
    assert "⋮" in descending["display_text"]
    for text in (descending["copy_text"], descending["display_text"]):
        for n in (1, 3, 5):
            actual=data(f"quantum:replace({text},n,{n})", *flags)
            reference=data("quantum:matrix("+str(n)+",1,[" + ",".join(f'"s_{i}"' for i in reversed(range(n))) + "])", *flags)
            assert actual["copy_text"] == reference["copy_text"]
    assert run("quantum:replace([s_(n-1); ⋮; s_1; s_0],n,1)", "--json", *flags, success=False).stdout==b""
    symbolic=data('quantum:qindexedcolumn("alpha_",n-1,1)',*flags)
    assert symbolic['rows']==symbolic['columns']==0
    concrete=data('quantum:replace('+symbolic['copy_text']+',n,3)',*flags)
    assert concrete['rows']==3 and concrete['columns']==1
    assert data('quantum:'+concrete['copy_text'],*flags)['cells']==concrete['cells']
    singleton=data('quantum:qindexedcolumn("alpha_",0,0)',*flags)
    assert singleton['rows']==singleton['columns']==1
    assert Decimal(data('quantum:replace(qindexedcolumn("alpha_",0,0),alpha_0,5)',*flags)['cells'][0][0])==5
    for expression in ['replace(qindexedcolumn("alpha_",n-1,1),n,1)','qindexedcolumn("alpha_",-1,0)','qindexedcolumn("alpha_",1/2,0)','qindexedcolumn("alpha_",1024,0)','qindexedcolumn("alpha_",2,-1)','qindexedcolumn("bad+_",2,0)']:
        assert run('quantum:'+expression,'--json',*flags,success=False).stdout==b''

# User-entered columns retain their family and dimension through evaluation.
for flags in [(), ("--approx",)]:
    for expression in ['[alpha_0; alpha_1; ⋮; alpha_(n-1)]', r'\begin{pmatrix}\alpha_0\\\alpha_1\\\vdots\\\alpha_{n-1}\end{pmatrix}']:
        symbolic=data('quantum:'+expression,*flags)
        assert symbolic['rows']==symbolic['columns']==0
        assert '⋮' in symbolic['display_text'] and 'qindexedcolumn' not in symbolic['display_text'],symbolic
        assert data('quantum:'+symbolic['display_text'],*flags)['copy_text']==symbolic['copy_text']
        concrete=data('quantum:replace('+expression+',n,3)',*flags)
        assert concrete['rows']==3 and concrete['columns']==1,concrete
        assert data('quantum:replace('+symbolic['copy_text']+',n,3)',*flags)['cells']==concrete['cells']
        assert run('quantum:replace('+expression+',n,1)','--json',*flags,success=False).stdout==b''
    concrete=data('quantum:replace(replace(replace([a_0; a_1; ⋮; a_2],a_0,2),a_1,3),a_2,4)',*flags)
    assert [[Decimal(c) for c in row] for row in concrete['cells']]==[[2],[3],[4]],concrete

# A trace call after ^ is an exponent, not a transpose followed by r(...).
for flags in [(), ("--approx",)]:
    for expression,expected in [('2^Tr(I)',4),('2^Tr(X)',1),('2^Tr([1,0;0,2])',8),('norm(vec([1,2;3,4]^T-[1,3;2,4]))',0)]:
        assert Decimal(data('quantum:'+expression,*flags)['text'])==expected,expression

# A derivation is a list of independent results, not one combined matrix.
for flags in [(), ("--approx",)]:
    for expression,expected in [
        (r"\begin{aligned}1+1&=2\\2+2&=5\end{aligned}", "1.  1\n\n2.  0"),
        (r"\begin{gathered}1+2\\3+4\end{gathered}", "1.  3\n\n2.  7"),
        (r"\begin {gathered}1+2\\3+4\end {gathered}", "1.  3\n\n2.  7"),
    ]:
        value=data("quantum:"+expression,*flags)
        assert value['display_text']==expected,value
        assert value['rows']==value['columns']==0 and value['cells']==[],value
        assert data("quantum:"+value['copy_text'],*flags)['display_text']==expected
    value=data(r"quantum:\begin{gathered}|0>\\|1>\end{gathered}",*flags)
    assert value['rows']==value['columns']==0 and value['cells']==[],value
    assert value['display_text'].startswith('1.  ') and '\n\n2.  ' in value['display_text'],value
    assert data("quantum:"+value['copy_text'],*flags)['display_text']==value['display_text']
    single=data(r"quantum:\begin{aligned}|0>\end{aligned}",*flags)
    assert single['rows']==2 and single['columns']==1,single
    assert Decimal(data(r"quantum:\langle{+i}\vert Y\vert{+i}\rangle",*flags)['text'])==1

for expression,shown in [('Tr(A)','Tr(A)'),('Tr(QFT_N)','Tr(QFT_N)')]:
    value=data('quantum:'+expression)
    assert value['display_text']==shown,value
    assert data('quantum:'+value['copy_text'])['display_text']==shown
    assert data('quantum:'+shown)['display_text']==shown
ordered=data('quantum:Tr(A*C*B)')
assert ordered['display_text']=='Tr(A · C · B)',ordered
substituted=data('quantum:replace(replace(replace('+ordered['copy_text']+',A,X),B,Y),C,Z)')
assert substituted['text'].replace('−','-')=='-2i',substituted
assert data('quantum:Tr(X*Z*Y)')['text']==substituted['text']
for expression in ['Tr(2)','Tr([1,2;3,4;5,6])','replace(Tr(A),A,2)','replace(Tr(A),A,[1;2])','Tr(Tr(A))','Tr(2*Tr(A))','Tr(sin(x))','Tr(sin(x)+cos(x))','Tr(2^x)']:
    assert run('quantum:'+expression,'--json',success=False).stdout==b''

# Scalar evaluation nodes must still present nested quantum functions naturally.
for expression,shown in [
    ('Tr(A)=Tr(B)', 'Tr(A) = Tr(B)'),
    ('Tr(A)+Tr(B)', 'Tr(A) + Tr(B)'),
    ('Tr(A)-Tr(B)', 'Tr(A) − Tr(B)'),
    ('Tr(A)^2', 'Tr(A)^2'),
    ('2*Tr(A)', '2 · Tr(A)'),
    ('(1+i)*Tr(A)', '(1 + i) · Tr(A)'),
    ('Tr(A)<=Tr(B)', 'Tr(A) ≤ Tr(B)'),
    ('Tr(A)!=Tr(B)', 'Tr(A) ≠ Tr(B)'),
    ('1/Tr(A)', '1 / Tr(A)'),
    ('Tr(A)/(Tr(B)+Tr(C))', 'Tr(A) / (Tr(B) + Tr(C))'),
    ('-(Tr(A)+Tr(B))', '−Tr(A) − Tr(B)'),
]:
    value=data('quantum:'+expression)
    assert value['display_text']==shown,(expression,value)
    assert data('quantum:'+value['copy_text'])['text']==value['text']
    assert data('quantum:'+shown)['text']==value['text']

# Bound ket names follow the displayed binder and survive dimension substitution.
for expression,shown in [
    (r"\sum_{k=0}^{n-1}{alpha_k|k>}", "∑_{k=0}^{n − 1} (alpha_k |k⟩)"),
    (r"\sum_{j=0}^{k}{|j>}", "∑_{j=0}^{k} (|j⟩)"),
]:
    value=data('quantum:'+expression)
    assert value['display_text']==shown,value
    assert data('quantum:'+value['copy_text'])['display_text']==shown
    assert data('quantum:'+shown)['display_text']==shown
source=r"\sum_{k=0}^{n-1}{alpha_k|k>}"
shown=data('quantum:'+source)['display_text']
assert data('quantum:replace('+source+',n,3)')['cells']==data('quantum:replace('+shown+',n,3)')['cells']

# Human-readable presentation must leave canonical clipboard expressions intact.
for expression,shown in [
    ("QFT_N|x>", "QFT_N |x⟩"),
    ("<Bell|after CZ>", "⟨Bell|after CZ⟩"),
    (r"\sum_{k=0}^{m-1} p_k \rho_k", "∑_{k=0}^{m − 1} (p_k · ρ_k)"),
    (r"\sum_{j=0}^{k}{p_j}", "∑_{j=0}^{k} (p_j)"),
    (r"\sum_{j=0}^{n}{p_k_j}", "∑_{j=0}^{n} (p_k_j)"),
    (r"\sum_{k=0}^{n}{sin(k)}", "∑_{k=0}^{n} (sin(k))"),
    (r"\sum_{k=0}^{n}{k^2}", "∑_{k=0}^{n} (k^2)"),
]:
    value=data("quantum:"+expression)
    assert value['display_text']==shown,(expression,value)
    assert data("quantum:"+value['copy_text'])['display_text']==shown
    assert data("quantum:"+shown)['display_text']==shown
assert data("quantum:∑_{k=0}^{3} k^2")['text']=='14'
for label in ['a+b','0','i','x']:
    value=data('quantum:qnamedket("'+label+'")')
    assert value['display_text']==value['text'],value

# Scalar products commute even when built-in and custom functions are mixed.
for flags in [(), ("--approx",)]:
    for component in ["re", "im", "abs"]:
        left = component + "(complexparam(x))"
        right = "complexparam(x)"
        for first, second in [(left,right),(right,left)]:
            assert data("quantum:"+first+"*"+second+"-"+second+"*"+first,*flags)["text"] == "0"
assert data("quantum:density(exp(i*t)*complexparam(x)|0>)-density(complexparam(x)|0>)")["cells"] == [["0","0"],["0","0"]]

# Explicit complex parameters retain their domain through worker serialization.
for flags in [(), ("--approx",)]:
    for symbol in ["x", r"\alpha"]:
        original = "conj(complexparam(" + symbol + "))"
        copied = data("quantum: " + original, *flags)["copy_text"]
        value = data("quantum: replace((" + copied + ")," + symbol + ",1+i)-(1-i)", *flags)
        assert value["text"] == "0", value
    density = data(r"quantum: density(complexparam(\alpha)|0>+complexparam(\beta)|1>)", *flags)
    substituted = r"replace(replace((" + density["copy_text"] + r"),\alpha,1),\beta,i)"
    value = data("quantum: (" + substituted + ")-[1,-i;i,1]", *flags)
    assert value["cells"] == [["0", "0"], ["0", "0"]], value
    for invalid in ["complexparam(x+y)", "complexparam([1;2])", "complexparam(inf)"]:
        run("quantum: " + invalid, "--json", *flags, success=False)

# Exact clipboard values must survive re-entry without decimal truncation.
for prefix in ["", "quantum: "]:
    for expression in ["1/3", "-22/7", "(1+2i)/3", "sqrt(2)/3",
                       "1/123456789012345678901234567890123456789"]:
        value = data(prefix + expression)
        assert data(prefix + "(" + value["copy_text"] + ")-(" + expression + ")")["text"] == "0"
for expression in ["[1/3,2/7;5/9,-11/13]", "density(((1+2i)/3)*|0>-(2/3)*|1>)"]:
    value = data("quantum: " + expression)
    residual = "quantum: (" + value["copy_text"] + ")-(" + expression + ")"
    assert data(residual)["cells"] == [["0", "0"], ["0", "0"]]

# Symbolic phase adjoints retain exact exponent conjugation through the GUI path.
for gate in ["Rz(x)", "Rx(x)", "Ry(x)", "[1,0;0,exp(i*x)]"]:
    value = data("quantum: dagger(" + gate + ")*(" + gate + ")")
    assert (value["rows"], value["columns"], value["cells"]) == (2, 2, [["1", "0"], ["0", "1"]]), value
assert data("quantum: norm((|0>+exp(i*x)*|1>)/sqrt(2))")["text"] == "1"

# Symbolic members retain their free names inside nested summations.
for flags in [(), ("--approx",)]:
    for expression in [
        "qsumset(qsum(x+y,0,1,y),vector(y),x)-(2*y+1)",
        "qsumset(qsumset(x+y,vector(0,1),y),vector(y),x)-(2*y+1)",
        "qsumset(qsum(qsum(x+y,0,1,y),0,1,y),vector(y),x)-(4*y+2)",
    ]:
        assert data(expression, *flags)["text"] == "0"

# A bra ending one projector must not consume the next weighted summand.
for flags in [(), ("--approx",)]:
    for expression, expected in [
        ("0.5*|0><0|+0.5*|+><+|", [["0.75", "0.25"], ["0.25", "0.25"]]),
        ("0.5*|0><0|-0.5*|+><+|", [["0.25", "-0.25"], ["-0.25", "-0.25"]]),
        ("0.5*|0⟩⟨0|+0.5*|1⟩⟨1|", [["0.5", "0"], ["0", "0.5"]]),
        ("|0><0|+2*|1><1|+3*|0><0|", [["4", "0"], ["0", "2"]]),
    ]:
        from decimal import Decimal
        value = data("quantum: " + expression, *flags)
        assert (value["rows"], value["columns"]) == (2, 2), value
        assert [[Decimal(cell.replace("−", "-")) for cell in row] for row in value["cells"]] == [[Decimal(cell) for cell in row] for row in expected], value
    assert data("quantum: <0|-X|1>", *flags)["text"].replace("−", "-") == "-1"

# Printed radian suffixes and explicit degrees are mathematical angle factors.
for flags in [(), ("--approx",)]:
    for prefix in ["", "quantum: "]:
        result = data(prefix + "sqrt(8*25GHz*0.5GHz) - 0.5GHz", *flags)
        assert result["text"] == "9.5 GHz", result
    assert data("quantum: (1GHz)/(1MHz)", *flags)["text"] == "1000"
    assert data("quantum: (1mHz)/(1Hz)", *flags)["text"] == "0.001"
    assert data("quantum: H|0>", *flags)["rows"] == 2
    assert data("quantum: 'GHz'", *flags) == data("'GHz'", *flags)

for flags in [(), ("--approx",)]:
    for expression, expected in [("cos(pi rad)", "-1"), ("sin(30 deg)", "0.5"),
                                  ("cos(90deg)", "0"), ("norm(vec(Rz(180 deg)-Rz(pi)))", "0")]:
        from decimal import Decimal
        assert Decimal(data("quantum: " + expression, *flags)["text"].replace("−", "-")) == Decimal(expected)
    original = r"\cos(\theta/2)|0>+e^{i\phi}\sin(\theta/2)|1>"
    printed = data("quantum: " + original, *flags)
    copied = data("quantum: " + printed["text"], *flags)
    if not flags:
        assert copied == printed
    assert (copied["rows"], copied["columns"]) == (2, 1)
    replaced = "replace(replace(" + printed["text"] + r",\theta,pi/2),\phi,pi/2)"
    residual = "norm((" + replaced + ")-|+i>)"
    if flags:
        # Approximate printing rounds e to 30 significant decimal digits.
        parts = data("quantum: " + residual, *flags)["text"].replace("−", "-").split(" + ")
        assert len(parts) in (1, 2)
        assert 0 <= Decimal(parts[0]) < Decimal("1e-25")
        if len(parts) == 2:
            assert parts[1].endswith("i") and Decimal(parts[1][:-1]) == 0
    else:
        assert data("quantum: " + residual)["text"] == "0"
    assert data("quantum: 'rad'", *flags) == data("'rad'", *flags)
    assert data("quantum: 'deg'", *flags) == data("'deg'", *flags)
assert "rad" in data("1 rad")["text"]

# Copying preserves matrix values and dimensions, including beyond the UI cell cap.
for flags in [(), ("--approx",)]:
    for expression in ["I", "[1+i,2;3,4-i]", "[1,2,3;4,5,6]", "[1,2;3,4;5,6]",
                       "matrix(1,3,[1,2,3])", "basis(0,1)", "0*basis(0,1)", "i*basis(0,1)", "basis(0,256)"]:
        first = data("quantum: " + expression, *flags)
        assert first["copy_text"]
        assert data("quantum: " + first["copy_text"], *flags) == first
        assert data(first["copy_text"], *flags) == first

# Printed symbolic results must be usable as quantum input again.
for flags in [(), ("--approx",)]:
    for expression in ["QFT_N|x>_N", "|high>", r"\alpha|0>+\beta|1>"]:
        first = data("quantum: " + expression, *flags)
        copied=data("quantum: " + first["text"], *flags)
        if expression=="QFT_N|x>_N":
            # Canonical parsing can rename a generated sum index.
            assert '∑' in copied['display_text'] and '∈ ℤ' in copied['display_text']
            residual=data('quantum:norm(replace(replace(('+first['copy_text']+')-('+copied['copy_text']+'),N,4),x,1))',*flags)['text'].replace('−','-')
            assert all(abs(Decimal(part.rstrip('i')))<Decimal('1e-25') for part in residual.split(' + '))
        else:
            assert copied==first
    for expression, symbol, value in [(r"\sum_{k=0}^{N-1}{|k>}", "N", "3"),
                                      (r"1/sqrt(|\Sigma|)\sum_{a\in\Sigma}{|a>}", r"\Sigma", "bitstrings(1)")]:
        first = data("quantum: " + expression, *flags)
        copied = data("quantum: " + first["text"], *flags)
        def substituted(text):
            return data("quantum: replace(" + text + "," + symbol + "," + value + ")", *flags)
        assert substituted(copied["text"]) == substituted(expression)
    for literal in ["'π⊗σ_x²'", "'a b'", '"a\'⊗b"', "'a\"⊗b'"]:
        assert data("quantum: " + literal, *flags) == data(literal, *flags)
    run("quantum: 'unfinished", *flags, success=False)
    run('quantum: "unfinished', *flags, success=False)

# Mixed adjoint operations simplify even when dimensions are unresolved.
for flags in [(), ("--approx",)]:
    for outer, inner, composed in [("qdag", "qconj", "qtranspose"), ("qconj", "qdag", "qtranspose"),
                                    ("qdag", "qtranspose", "qconj"), ("qtranspose", "qdag", "qconj"),
                                    ("qconj", "qtranspose", "qdag"), ("qtranspose", "qconj", "qdag")]:
        nested = outer + "(" + inner + "(QFT_N))"
        reduced = composed + "(QFT_N)"
        assert data("quantum: " + nested, *flags) == data("quantum: " + reduced, *flags)
        for dimension in [1, 3, 4]:
            assert data("quantum: replace(" + nested + ",N," + str(dimension) + ")", *flags) == data("quantum: " + composed + "(QFT_" + str(dimension) + ")", *flags)
        assert run("quantum: replace(" + nested + ",N,0)", "--json", *flags, success=False).stdout == b""

# Suit labels are names, not automatically assigned basis coordinates.
for flags in [(), ("--approx",)]:
    for command, symbol in [("clubsuit", "♣"), ("diamondsuit", "♢"), ("heartsuit", "♡"), ("spadesuit", "♠")]:
        assert data("quantum: |\\" + command + ">", *flags) == data("quantum: |" + symbol + ">", *flags)
    suits = r"\frac{1}{2}\vert\clubsuit\rangle+\frac{i}{2}\vert\diamondsuit\rangle-\frac{1}{2}\vert\heartsuit\rangle-\frac{i}{2}\vert\spadesuit\rangle"
    symbolic = data("quantum: " + suits, *flags)
    assert symbolic["rows"] == 0 and "qnamedket" in symbolic["text"]
    for index, command in enumerate(["clubsuit", "diamondsuit", "heartsuit", "spadesuit"]):
        suits = "replace(" + suits + ",|\\" + command + ">,|" + str(index) + ">_4)"
    assert data("quantum: norm((" + suits + ")-[1;i;-1;-i]/2)", *flags)["text"] == "0"
    assert data("quantum: norm(" + suits + ")", *flags)["text"] == "1"

for flags in [(), ("--approx",)]:
    for bare, grouped in [("|x>_N", "|x>_{N}"), ("<x|_N", "<x|_{N}"),
                          ("QFT_N|x>_N", "QFT_N|x>_{N}"),
                          ("|x>_N^2", "(|x>_{N})^2")]:
        assert data("quantum: " + bare, *flags) == data("quantum: " + grouped, *flags)

for flags in [(), ("--approx",)]:
    assert data(r"quantum: \sum_{k=0}^{2}{|k>}", *flags)["cells"] == [["1"], ["1"], ["1"]]
    assert data(r"quantum: replace(\sum_{k=0}^{N-1}{|k>},N,3)", *flags)["cells"] == [["1"], ["1"], ["1"]]
    assert data(r"quantum: \sum_{k=0}^{2}{|k>_4}", *flags)["cells"] == [["1"], ["1"], ["1"], ["0"]]
    assert data(r"quantum: \sum_{k=0}^{2}{\sum_{k=0}^{1}{|k>}}", *flags)["cells"] == [["3"], ["3"]]
    assert data(r"quantum: \sum_{k=0}^{2}{<k|k>}", *flags)["text"] == "3"
    decimal = data(r"quantum: \frac{1}{\sqrt{385}}\sum_{k=0}^9 (k+1)\vert k\rangle", *flags)
    assert decimal["rows"] == 10 and decimal["columns"] == 1
    if flags:
        for k, row in enumerate(decimal["cells"]):
            assert abs(float(row[0]) - (k+1)/385**0.5) < 1e-13

for flags in [(), ("--approx",)]:
    for expression in ["|0>_1", "QFT_1|0>_1", "qdensity(|0>_1)", "qdag(|0>_1)", "qconj(|0>_1)", "qtranspose(|0>_1)", "qketstate(bitstrings(0))", r"\sum_{k=0}^{0}{|k>}",
                       r"replace(\sum_{k=0}^{N-1}{|k>},N,1)"]:
        value=data("quantum: "+expression, *flags)
        assert value["rows"] == value["columns"] == 1 and value["cells"] == [["1"]], (expression, value)
    for expression in ["qnorm(qbasis(0,1))", "qmul(qdag(qbasis(0,1)),qbasis(0,1))", "matrix(1,1,[1])"]:
        scalar=data(expression, *flags)
        assert scalar["text"] == "1" and scalar["rows"] == scalar["columns"] == 0
# Complex amplitudes must preserve state shape before adjoint/density evaluation.
for flags in [(), ("--approx",)]:
    for expression, expected in [("i*|0>_1", "i"), ("|0>_1*i", "i"),
                                 ("qdag(i*|0>_1)", "-i"), ("qconj(i*|0>_1)", "-i"),
                                 ("qtranspose(i*|0>_1)", "i"), ("qdensity(i*|0>_1)", "1"),
                                 ("qnormalize(i*|0>_1)", "i")]:
        value = data("quantum: " + expression, *flags)
        assert value["rows"] == value["columns"] == 1, (expression, value)
        assert value["cells"][0][0].replace("−", "-") == expected, (expression, value)
# Wide basis columns remain exact symbolic terms instead of allocating a dense state.
wide_sum = data(r"quantum: \sum_{k=0}^{1024}{|k>}")
wide_sum_copy = data(wide_sum["copy_text"])
for value in (wide_sum, wide_sum_copy):
    assert value["rows"] == value["columns"] == 0 and value["cells"] == []
    indices = re.findall(r"qbasis\((\d+),\s*1025\)", value["copy_text"])
    assert len(indices) == 1025 and set(map(int, indices)) == set(range(1025))
assert wide_sum_copy["copy_text"] == wide_sum["copy_text"]
for expression in [r"\sum_{k=1}^{2}{|k>}",
                   r"\sum_{k=0}^{2}{|k>_2}", "basis(0,0)", "basis(1,1)", "basis(-1,1)"]:
    assert run("quantum: " + expression, "--json", success=False).stdout == b""

# An unknown domain stays symbolic; an explicit singleton is already a set.
for flags in [(), ("--approx",)]:
    uniform = r"1/sqrt(|\Sigma|)\sum_{a\in\Sigma}{|a>}"
    symbolic = data("quantum: " + uniform, *flags)
    assert "qsumset(" in symbolic["text"] and "qbars(" in symbolic["text"]
    assert data("quantum: replace(" + uniform + r",\Sigma,bitstrings(1))", *flags) == data("quantum: |+>", *flags)
    for expression, expected in [("replace(cardinality(S),S,vector(2,3,3))", "2"),
                                 ("replace(|S|,S,vector(2,3,3))", "2"),
                                 ("replace(|S|,S,-3)", "3"),
                                 ("replace(|S|,S,3+4*i)", "5"),
                                 (r"replace(\sum_{x\in S}{x},S,vector())", "0"),
                                 ("cardinality(vector(x))", "1"), ("|vector(x)|", "1")]:
        assert data("quantum: " + expression, *flags)["text"] == expected
    for expression in ["replace(cardinality(S),S,3)", "replace(cardinality(S),S,[1,2;3,4])"]:
        assert run("quantum: " + expression, "--json", *flags, success=False).stdout == b""

# Quantum amplitudes and error bounds remain symbolic even in approximate mode.
for flags in [(), ("--approx",)]:
    for command, letter in [("Sigma", "Σ"), ("Pi", "Π"), ("Gamma", "Γ"),
                            ("Delta", "Δ"), ("Omega", "Ω"), ("tau", "τ"),
                            ("xi", "ξ"), ("varpi", "ϖ"), ("varsigma", "ς")]:
        assert data("quantum: \\" + command, *flags) == data("quantum: " + letter, *flags)
    for letter in "αβγδεζηθικλμνξορστυφχψωΓΔΘΛΞΠΣΦΨΩ":
        result = data("quantum: " + letter, *flags)
        assert result["text"] == "'" + letter + "'" and not result["approximate"]
    state = data(r"quantum: \alpha|0>+\beta|1>", *flags)
    assert state["cells"] == [["'α'"], ["'β'"]]
    assert data(r"quantum: \ket{x}_\alpha", *flags) == data(r"quantum: |x>_{α}", *flags)
assert data("quantum: δ(1)")["text"] == "0"
assert data(r"quantum: \sum_{\alpha=0}^{1}{|\alpha>_2}")["cells"] == [["1"], ["1"]]
assert data(r"quantum: \sum_{\delta=0}^{2}{\delta^2}")["text"] == "5"
assert data(r"quantum: replace(\alpha,\alpha,1/2)")["text"] == "0.5"
assert data("α", "--approx")["approximate"]

assert data("quantum: alpha", "--approx")["approximate"]

for flags in [(), ("--approx",)]:
    for expression in [r"\cos^2(\pi\theta)", r"\sin^2(\pi\theta)",
                       r"\frac{1}{\sqrt{2}}|0>+\frac{e^{2\pi i\theta}}{\sqrt{2}}|1>"]:
        assert "θ" in data("quantum: " + expression, *flags)["text"]
    assert data(r"quantum: \ket{x}_\theta", *flags) == data(r"quantum: |x>_{θ}", *flags)
assert data("quantum: θ(1)")["text"] == "1"
assert data("quantum: θ(-1)")["text"] == "0"

for flags in [(), ("--approx",)]:
    symbolic = data(r"quantum: \sum_{k=0}^{N-1}{k}", *flags)
    assert "qsum(" in symbolic["text"] and "N" in symbolic["text"]
    assert data(r"quantum: replace(\sum_{k=0}^{N-1}{k},N,4)", *flags)["text"] == "6"
    assert data(r"quantum: replace(\sum_{k=0}^{N-1}{|k>_4},N,4)", *flags)["cells"] == [["1"], ["1"], ["1"], ["1"]]
for expression in [r"\sum_{k=0.5}^{N}{k}", r"\sum_{k=0}^{1.5}{k}", r"\sum_{k=2}^{1}{k}", "qsum(k,0,[1,2],k)"]:
    assert run("quantum: " + expression, "--json", success=False).stdout == b""

for flags in [(), ("--approx",)]:
    assert data("quantum: 1 <= |-2|", *flags)["text"] == "1"
    assert data("quantum: 3 <= |-2|", *flags)["text"] == "0"
    assert data("quantum: |-1| ≤ 2|-1/2|", *flags)["text"] == "1"
    assert data(r"quantum: |e^{2\pi i (-1/2)}-1| <= 2\pi|-1/2|", *flags)["text"] == "1"

assert run("1+1").stdout.decode("utf-8").strip() == "2"
assert data("1+1")["text"] == "2"
assert data("sqrt(2)", "--approx")["approximate"] is True
matrix = data("[1,2;3,4]")
assert (matrix["rows"], matrix["columns"], matrix["cells"]) == (2, 2, [["1", "2"], ["3", "4"]])
large = data("identity(12)")
assert (large["rows"], large["columns"], large["cells"]) == (12, 12, [])
assert data("[1/4;3/4]", "--probabilities")["probabilities"] == [0.25, 0.75]
assert data("[1;1]", "--probabilities")["probabilities"] == []
assert data("[-1;2]", "--probabilities")["probabilities"] == []
assert data("[i;1]", "--probabilities")["probabilities"] == []
assert data("[0;0;1]", "--bloch")["bloch"] == [0, 0, 1]
assert data("[0;0;2]", "--bloch")["bloch"] == []
assert data("[i;0;0]", "--bloch")["bloch"] == []
assert data("1" + " " * 32767)["text"] == "1"
assert b"32768" in run("1" + " " * 32768, success=False).stderr
assert b"32768" in run("x" * 1000000, success=False).stderr
assert b"Usage:" in run("1", "--unknown", success=False).stderr
assert run("qmul([1,0;0,1],[1;2;3])", "--json", success=False).stdout == b""
def state_request(definitions, expression):
    # Each record has two decimal byte lengths, followed by the raw fields.
    value = "QSTATES1\n" + str(len(definitions)) + "\n"
    for name, definition in definitions:
        value += f"{len(name.encode('utf-8'))}\n{len(definition.encode('utf-8'))}\n{name}{definition}"
    return value + expression

for definitions,expression in [
    ([("red","2|0>")],"orthobasis(<red|red>,B,[|red>])"),
    ([("psi(t)","[1;t]")],"orthobasis(<psi_1|psi_1>,B,[|psi_1>])"),
]:
    rejected=run(state_request(definitions,"quantum:"+expression),"--states","--json",success=False)
    assert rejected.returncode==2 and not rejected.stdout and b"cannot override" in rejected.stderr


# Complex declarations apply before evaluation and survive later substitution.
for flags in [(), ("--approx",)]:
    declared = [("psi(a:complex,b:complex)", "a|0>+b|1>")]
    original = data(state_request(declared, "quantum:density(|psi(x,y)>)"), "--states", *flags)
    expression = "quantum:replace(replace(("+original["copy_text"]+"),x,1),y,i)-[1,-i;i,1]"
    assert data(expression,*flags)["cells"] == [["0","0"],["0","0"]]
    for name, body, expression, expected in [
        ("psi(a:complex,b:complex)", "a|0>+b|1>", "density(|psi(1,i)>)-[1,-i;i,1]", [["0","0"],["0","0"]]),
        ("psi(a:complex,b)", "exp(i*b)*a|0>", "density(|psi(i,pi/2)>)-[1,0;0,0]", [["0","0"],["0","0"]]),
        ("psi(a:complex)", "complexparam(a)|0>", "|psi(i)>", [["i"],["0"]]),
        ("psi(a:complex)", "qsum(a*|0>,0,1,a)", "|psi(i)>", [["1"],["0"]]),
        ("psi(a:complex)", "a|0>", "|psi(0)>", [["0"],["0"]]),
    ]:
        result = data(state_request([(name,body)],"quantum:"+expression),"--states",*flags)
        assert len(result["cells"]) == len(expected)
        for actual_row, expected_row in zip(result["cells"], expected):
            assert len(actual_row) == len(expected_row)
            for actual, target in zip(actual_row, expected_row):
                assert actual == target or (flags and target == "0" and Decimal(actual) == 0), (name, body, expression, flags, result)
for name in ["psi(a:real)","psi(a:complex,a)","psi(:complex)","psi(a:complex:complex)"]:
    run(state_request([(name,"a|0>")],"1"),"--states",success=False)

family = [("psi(alpha)", "cos(alpha)|0>+sin(alpha)|1>")]
for flags in [(), ("--approx",)]:
    for expression, cells in [("|psi(0)>", [["1"], ["0"]]), ("|psi(pi/2)>", [["0"], ["1"]])]:
        from decimal import Decimal
        value = data(state_request(family, "quantum:"+expression), "--states", *flags)
        assert (value["rows"], value["columns"]) == (2, 1)
        if not flags:
            assert value["cells"] == cells
        assert all(abs(Decimal(value["cells"][r][0].replace("−", "-"))-Decimal(cells[r][0])) < Decimal("1e-25") for r in range(2)), value
    assert abs(Decimal(data(state_request(family, "quantum:<psi(0)|psi(pi/2)>"), "--states", *flags)["text"].replace("−", "-"))) < Decimal("1e-25")
    symbolic = data(state_request(family, "quantum:|psi(t)>"), "--states", *flags)
    assert symbolic["rows"] == 2 and "t" in symbolic["text"]
    assert data(state_request(family, "quantum:"+symbolic["copy_text"]), "--states", *flags) == symbolic
    undeclared = data("quantum:|unknown(pi/8)>", *flags)
    assert "qstatecall" in undeclared["text"]
    if not flags:
        assert data("quantum:"+undeclared["copy_text"], *flags) == undeclared
    else:
        # Copied decimal literals are exact decimals, so approximation metadata
        # need not survive. Resolve the same family and compare its value.
        declaration = [("unknown(x)", "x*|0>")]
        original = data(state_request(declaration, "quantum:|unknown(pi/8)>"), "--states", *flags)
        copied = data(state_request(declaration, "quantum:"+undeclared["copy_text"]), "--states", *flags)
        assert (copied["rows"], copied["columns"]) == (2, 1)
        assert all(abs(Decimal(copied["cells"][r][0].replace("−", "-"))-Decimal(original["cells"][r][0].replace("−", "-"))) < Decimal("1e-25") for r in range(2))
    assert data(state_request([("scaled(x)", "x*|0>")], "quantum:<scaled(2)|scaled(2)>"), "--states", *flags)["text"] == "4"
    for bad in ["|psi([1;2])>", "|psi(infinity)>", "|psi(undefined)>"]:
        run(state_request(family, "quantum:"+bad), "--states", *flags, success=False)
for bad_family in [
    [("psi()", "|0>")], [("psi(X)", "X|0>")],
    [("psi(x)", "|psi(x)>")], [("psi(x)", "|missing(x)>")],
    [("psi(x)", "|0>"), ("psi(y)", "|1>")],
]:
    run(state_request(bad_family, "1"), "--states", success=False)
assert data(state_request(family, "alpha"), "--states") == data("alpha")
assert data(state_request([("scaled(m)", "m*|0>")], "1 m"), "--states") == data("1 m")
assert data(state_request([("fixed", "|1>"), ("scaled(fixed)", "fixed*|0>")], "quantum:|fixed>"), "--states")["cells"] == [["0"], ["1"]]
assert data(state_request([("first(x)", "x*|0>"), ("second(x)", "x*|1>")], "quantum:|first(2)>+|second(3)>"), "--states")["cells"] == [["2"], ["3"]]

for parameter in ["α", "theta_1"]:
    declaration = [("ψ("+parameter+")", parameter+"*|0>")]
    assert data(state_request(declaration, "quantum:|ψ(2)>"), "--states")["cells"] == [["2"], ["0"]]
    assert data(state_request(declaration, "quantum:|ψ(t)>"), "--states") == data("quantum:t*|0>")
run(state_request([("psi(π)", "π*|0>")], "1"), "--states", success=False)

for label in ["|psi_{pi/2}>", r"\ket{psi_{pi/2}}", r"\ket{psi_{\pi/2}}"]:
    assert data(state_request(family, "quantum:"+label), "--states")["cells"] == [["0"], ["1"]]
for label in ["|psi_t>", "|psi_{t}>"]:
    assert data(state_request(family, "quantum:"+label), "--states") == data(state_request(family, "quantum:|psi(t)>"), "--states")
assert data(state_request([("psi_t", "|1>")]+family, "quantum:|psi_t>"), "--states")["cells"] == [["0"], ["1"]]
assert data(state_request(family+[("psi_t", "|1>")], "quantum:|psi_t>"), "--states")["cells"] == [["0"], ["1"]]
assert data(state_request(family, r"quantum:\braket{psi_{pi/2}}{psi_0}"), "--states")["text"] == "0"
greek_family = [("ψ(α)", "cos(α)|0>+sin(α)|1>")]
assert data(state_request(greek_family, r"quantum:\ket{\psi_{\pi/2}}"), "--states")["cells"] == [["0"], ["1"]]
assert data(state_request(greek_family, r"quantum:\ket{\psi_\beta}"), "--states") == data(state_request(greek_family, "quantum:|ψ(β)>"), "--states")
for label in ["|psi_{}>", "|psi_{1,2}>"]:
    run(state_request(family, "quantum:"+label), "--states", success=False)


for expression in ["|unknown_{a+b}>", r"\dyad{psi_{pi/2}}{psi_0}", r"\mel{psi_{pi/2}}{X}{psi_0}"]:
    value = data(state_request(family, "quantum:"+expression), "--states")
    assert data(state_request(family, "quantum:"+value["copy_text"]), "--states") == value
mixture = "(2+sqrt(2))/4*|psi_{pi/8}><psi_{pi/8}|+(2-sqrt(2))/4*|psi_{5*pi/8}><psi_{5*pi/8}|"
value = data(state_request(family, "quantum:"+mixture), "--states", "--approx")
assert (value["rows"],value["columns"]) == (2,2)
for r in range(2):
    for c in range(2):
        assert abs(Decimal(value["cells"][r][c])-Decimal("0.75" if (r,c)==(0,0) else "0.25")) < Decimal("1e-25"), value

bloch_family = [("psi(theta,phi)", "cos(theta/2)|0>+exp(i*phi)*sin(theta/2)|1>")]
for expression, expected in [("|psi(0,0)>","|0>"),("|psi(pi/2,0)>","|+>"),("|psi(pi/2,pi/2)>","|+i>")]:
    assert data(state_request(bloch_family, "quantum:"+expression), "--states") == data("quantum:"+expected)
value = data(state_request(bloch_family, "quantum:|psi(t,p)>"), "--states")
assert value['rows']==2 and 't' in value['text'] and 'p' in value['text']
assert data(state_request(bloch_family, "quantum:"+value['copy_text']), "--states") == value
assert data(state_request([("pair(x,y)","x*|0>+y*|1>")],"quantum:|pair(y,x)>"),"--states") == data("quantum:y*|0>+x*|1>")
for expression in ["|psi(1)>","|psi(1,2,3)>","|psi([1;2],0)>","|psi(0,infinity)>"]:
    run(state_request(bloch_family,"quantum:"+expression),"--states",success=False)
for declaration in ["psi(x,x)","psi(x,)","psi(,x)"]:
    run(state_request([(declaration,"|0>")],"1"),"--states",success=False)
assert data(state_request([("pair(m,alpha)","m*|0>+alpha*|1>")],"1 m"),"--states") == data("1 m")
names = ["a"+str(k) for k in range(16)]
assert data(state_request([("wide("+",".join(names)+")", "a0*|0>+a15*|1>")],"quantum:|wide("+",".join(str(k) for k in range(16))+")>"),"--states")["cells"] == [["0"],["15"]]
run(state_request([("wide("+",".join(names+["a16"])+")", "|0>")],"1"),"--states",success=False)

definitions = [("Bell", "|Phi+>"), ("after CZ", "CZ|Bell>")]
for flags in [(), ("--approx",)]:
    for expression, expected in [("<Bell|Bell>", 1), ("<Bell|after CZ>", 0), ("<after CZ|after CZ>", 1)]:
        assert abs(float(data(state_request(definitions, "quantum:" + expression), "--states", *flags)["text"]) - expected) < 1e-12
assert data(state_request([("weighted", "2|0>")], "quantum:<weighted|weighted>"), "--states")["text"] == "4"
assert data(state_request([("symbolic", "[a;b]")], "quantum:|symbolic>"), "--states")["rows"] == 2
assert data(state_request([("état", "|1>")], "quantum:<état|état>"), "--states")["text"] == "1"
assert data(state_request([], "1+1"), "--states")["text"] == "2"
assert data(state_request([("Bell", "[1;\n0;0;1]/sqrt(2)")], "quantum:<Bell|Bell>"), "--states")["text"] == "1"
assert data(state_request([("Bell", "[1;\r\n0;0;1]/sqrt(2)")], "quantum:<Bell|Bell>"), "--states")["text"] == "1"
# Definitions belong to one request and never silently normalize a vector.
assert "qketstate" in data("quantum:|Bell>")["text"]
for invalid_definitions in [
    [("Bell", "|Phi+>"), ("Bell", "|0>")],
    [("after CZ", "CZ|Bell>"), ("Bell", "|Phi+>")],
    [("Bell", "|after CZ>"), ("after CZ", "|Bell>")],
    [("Bell", "|Bell>")], [("Bell", "|missing>")],
    [("Bell", "1")], [("Bell", "[1,0;0,1]")],
    [("Bell", "[infinity;0]")], [("Bell", "[undefined;0]")],
    [("0", "|1>")], [("Phi+", "|0>")], [("GHZ", "|0>")], [("today", "|0>")],
    [(" Bell", "|0>")], [("Bell ", "|0>")], [("bad\nname", "|0>")],
    [("bad|name", "|0>")], [("bad\x00name", "|0>")],
    [("Bell", "|0>\x00ignored")],
    [("a" * 129, "|0>")], [("Bell", "x" * 32769)],
    [("state" + str(i), "|0>") for i in range(33)],
]:
    assert run(state_request(invalid_definitions, "1"), "--states", success=False).stdout == b""
for malformed in [
    "", "QSTATES2\n0\n1", "QSTATES1\n-1\n1", "QSTATES1\n0",
    "QSTATES1\n999999999999999999\n1", "QSTATES1\n1\n4\n8\nBell",
    "QSTATES1\n1\n0\n1\n01", "QSTATES1\n0\n",
    "QSTATES1\n0\n" + "x" * 32769, "x" * 1100001,
    "QSTATES1\n0\n1\x002",
]:
    assert run(malformed, "--states", success=False).stdout == b""
print(f"PASS: {checks} worker process checks")
