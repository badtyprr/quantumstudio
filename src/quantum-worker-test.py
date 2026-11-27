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


# Coefficients indexed by a bound pair form the image over its product domain.
coefficients=data(r"quantum:$\{\alpha_{ab}:(a,b)\in\Sigma\times\Gamma\}$")["copy_text"]
assert data("quantum:"+coefficients)["copy_text"]==coefficients
table="qset(vector(qtuple(vector(qtuple(vector(3,7)),i)),qtuple(vector(qtuple(vector(5,7)),i))))"
assigned=f'replace(replace(replace(({coefficients}),"α",{table}),"Σ",qset(vector(3,5))),"Γ",qset(vector(7)))'
assert data("quantum:"+assigned)["copy_text"]=="qset(vector(i))"

# A word over finite alphabets preserves position and repeated symbols.
# Binding the same set label supplies its cardinality and its uniform ket.
set_state = data(r"quantum:$\sqrt{\vert A_0\vert}\vert A_0\rangle$")["copy_text"]
support = "qset(vector(qbitlabel(0,2),qbitlabel(3,2)))"
assert data(f'quantum:replace(({set_state}),"A_0",{support})')["copy_text"] == "matrix(4,1,[1,0,0,1])"
empty_state = run('quantum:replace(qketstate("S"),"S",qset(vector()))', "--json", success=False)
assert b"nonempty set" in empty_state.stderr
for symbol in (r"\emptyset", r"\varnothing", "∅"):
    condition = data(f"quantum:$A_0 = {symbol}$")["copy_text"]
    assert data(f'quantum:replace(({condition}),"A_0",qset(vector()))')["copy_text"] == "1"
    assert data(f'quantum:replace(({condition}),"A_0",qset(vector(0)))')["copy_text"] == "0"
assert data(r"quantum:sets:$a_{11}\cdots a_9$")["copy_text"] == 'qtuple(vector("a_11","a_10","a_9"))'
assert data(r"quantum:sets:$a_1\ldots a_3$")["copy_text"] == 'qtuple(vector("a_1","a_2","a_3"))'
run(r"quantum:sets:$a_{11}\cdots b_9$","--json",success=False)

# Each overlap conjugates its bra independently, including at width one.
overlaps = data(r"quantum:$\langle a_{n-1}\vert b_{n-1}\rangle\cdots\langle a_0\vert b_0\rangle$")["copy_text"]
assert data(f'quantum:replace(replace(replace(({overlaps}),"a_0",[0;i]),"b_0",[0;2]),n,1)')["copy_text"] == "−2i"
assert data(f'quantum:replace(replace(replace(({overlaps}),n,1),"a_0",[0;i]),"b_0",[2;0])')["copy_text"] == "0"

# Tensor columns run through the inner coordinate before changing blocks.
tensor_rows = r"x_0 y_0\\\vdots\\x_0 y_k\\\vdots\\x_m y_0\\\vdots\\x_m y_k"
tensor_display = r"$$\begin{pmatrix}" + tensor_rows + r"\end{pmatrix}$$"
block = data("quantum:" + tensor_display)["copy_text"]
for name,value in [("k","1"),("m","1"),("x_0","1"),("x_1","2"),("y_0","3"),("y_1","4")]:
    block = f'replace(({block}),"{name}",{value})'
assert data("quantum:" + block)["copy_text"] == "matrix(4,1,[3,4,6,8])"
assert b"indexed column" in run("quantum:" + tensor_display.replace("x_m y_k","x_m y_j"),"--json",success=False).stderr

# Printed alphabet order supplies the row and column coordinates.
assert data("quantum:basislabels([3,1,2]):|1>")["cells"] == [["0"],["1"],["0"]]
assert data("quantum:basislabels([1,2,3],[0,1]):<3,1|")["copy_text"] == "vector(0,0,0,0,0,1)"
assert data("quantum:basislabels([1,2]):|0>_2")["cells"] == [["1"],["0"]]
assert data("quantum:basislabels([[3,1]],basislabels([[0,1]],|1>)+|3>)")["cells"] == [["1"],["1"]]
for invalid in ["basislabels([1,1]):|1>","basislabels([01,1]):|1>","basislabels([1,2]):|3>",
                "basislabels([0,1],[0,1]):|0>"]:
    run("quantum:" + invalid,"--json",success=False)

# Register subscripts label the identity factors, including register zero.
identities = r"\mathbb{I}_{n-1}\otimes\cdots\otimes\mathbb{I}_0"
series = data("quantum:$" + identities + "$")["copy_text"]
identity = data(f'quantum:replace(replace(replace(({series}),"dim_1",3),n,2),"dim_0",2)')
assert identity["cells"] == [[str(int(row==column)) for column in range(6)] for row in range(6)]
gram = r"(V_{n-1}^{\dagger} V_{n-1})\otimes\cdots\otimes(V_0^{\dagger} V_0)"
test = data("quantum:$" + gram + "=" + identities + "$")["copy_text"]
for scale, expected in [(1,"1"),(2,"0")]:
    # The 3-by-2 isometry has a two-dimensional input space.
    expr = f'replace(replace(({test}),n,1),"V_0",[1,0;0,{scale};0,0])'
    assert data("quantum:" + expr)["copy_text"] == expected

# A binary control can select an operation on a three-dimensional target.
controlled_definition = r"CU=\vert 0\rangle\langle 0\vert\otimes\mathbb{I}_{\mathsf{R}}+\vert 1\rangle\langle 1\vert\otimes U"
target_matrix = "[0,1,0;0,0,i;1,0,0]"
for formula, expected in [(controlled_definition,"1"),(controlled_definition.replace("+","-"),"0"),
                          (controlled_definition.replace(r"\langle 0",r"\langle 1"),"0")]:
    relation = data("quantum:$$" + formula + ".$$")["copy_text"]
    assert data("quantum:" + relation)["copy_text"] == relation
    assert data(f'quantum:replace(({relation}),"U",{target_matrix})')["copy_text"] == expected
controlled = data("quantum:qregistercontrol(" + target_matrix + ")")
assert controlled["cells"] == [
    ["1","0","0","0","0","0"], ["0","1","0","0","0","0"], ["0","0","1","0","0","0"],
    ["0","0","0","0","1","0"], ["0","0","0","0","0","i"], ["0","0","0","1","0","0"]]
assert b"square matrix" in run("quantum:qregistercontrol([1,0,0;0,1,0])","--json",success=False).stderr

# An ellipsis between operator products pairs corresponding list entries.
operator_list = data(r"quantum:$N_0\ldots,N_{n-1}$")["copy_text"]
assert operator_list == data(r"quantum:$N_0,\ldots,N_{n-1}$")["copy_text"]
products = data(r"quantum:$M_0 N_0,\ldots,M_{n-1} N_{n-1}$")["copy_text"]
assignments = [("M_0","[0,1;1,0]"),("N_0","[1,0;0,-1]"),("M_1","[1,2;0,1]"),("N_1","[2,0;3,1]")]
for width_first in (True,False):
    expr = f"replace(({products}),n,2)" if width_first else products
    for key, value in assignments:
        expr = f'replace(({expr}),"{key}",{value})'
    if not width_first:
        expr = f"replace(({expr}),n,2)"
    assert data("quantum:" + expr)["copy_text"] == "vector(matrix(2,2,[0,−1,1,0]),matrix(2,2,[8,2,3,1]))"

# A product of norms checks normalization after the state factors are bound.
norm_series = r"\bigl\|\vert \psi_{n-1}\rangle\bigl\|\cdots\bigl\|\vert \psi_0\rangle\bigr\|"
tensor_norm = r"\bigl\|\vert \psi_{n-1}\rangle\otimes\cdots\otimes\vert \psi_0\rangle\bigr\|"
norm_chain = data("quantum:$$" + tensor_norm + "=" + norm_series + "=1^n=1.$$")["copy_text"]
separate_norms = data("quantum:$" + norm_series + "$")["copy_text"]
for high, low, product, normalized in [("2*i", "1/2", "1", "1"), ("3*i", "2", "6", "0"), ("0", "2", "0", "0")]:
    for expr, expected in [(separate_norms,product),(norm_chain,normalized)]:
        bound = f'replace(replace(replace(({expr}),"ψ_0",[{low};0;0]),"ψ_1",[0;{high}]),n,2)'
        assert data("quantum:" + bound)["copy_text"] == expected

# The shared-domain declaration and equivalent nonempty Cartesian power
# both retain every alphabet, including those hidden by the ellipsis.
for formula in [r"\Sigma_0=\Sigma_1=\cdots=\Sigma_9=\{0,1\}",
                r"\Sigma_9\times\Sigma_8\times\cdots\times\Sigma_0=\{0,1\}^{10}."]:
    shared = data("quantum:$$" + formula + "$$")["copy_text"]
    assert len(shared) < 250 and data("quantum:" + shared)["copy_text"] == shared
    for middle, answer in [(1, "1"), (2, "0")]:
        bound = shared
        for i in range(10):
            bound = f'replace(({bound}),"Σ_{i}",qset(vector(0,{middle if i == 4 else 1})))'
        assert data("quantum:" + bound)["copy_text"] == answer

builder = r"\bigl\{(a_1,\ldots,a_n)\,:\,a_1\in\Gamma_1,\:\ldots,\:a_n\in\Gamma_n\bigr\}."
product = r"\Sigma_1\times\cdots\times\Sigma_n"
comparison = data("quantum:$$" + product + "=" + builder + "$$")["copy_text"]
for last, answer in [(7, "1"), (8, "0")]:
    bound = f"replace(({comparison}),n,2)"
    for name, value in [("Σ_1",3),("Γ_1",3),("Σ_2",7),("Γ_2",last)]:
        bound = f'replace(({bound}),"{name}",qset(vector({value})))'
    assert data("quantum:" + bound)["copy_text"] == answer

# Coordinate membership does not require constructing all 4096 tuples.
binary_domains = ",".join(["qset(vector(0,1))"]*12)
axes = f"qcartesianseries(vector({binary_domains}),0)"
for entry, answer in [(1,"1"),(2,"0")]:
    coordinates = ",".join(["0"]*11+[str(entry)])
    assert data(f"quantum:qmember(qtuple(vector({coordinates})),{axes})")["copy_text"] == answer
outcomes = data(r"quantum:$c,d\in\Gamma$")["copy_text"]
assert data(f'quantum:replace(replace(replace(({outcomes}),"Γ",qset(vector(3,7))),"c",7),"d",3)')["copy_text"] == "1"

# A comma in a function call stays inside the basis index.
ordered_basis = data(r"quantum:$\vert(a,c)\rangle$")["copy_text"]
assert data(f'quantum:replace(replace(({ordered_basis}),"a",[0;i]),"c",[0;1;0])')["cells"] == [["0"],["0"],["0"],["0"],["i"],["0"]]
assert data(r"quantum:$\vert(mod(3,2))\rangle_2$")["cells"] == [["0"],["1"]]

# Fixed-width outcome lists keep their order and leading zeros.
assert data(r"quantum:$10,00,10$")["copy_text"] == "qtuple(vector(qbitlabel(2,2),qbitlabel(0,2),qbitlabel(2,2)))"
assert data(r"quantum:$(2,0),\;(1,0)$")["copy_text"] == "qtuple(vector(qtuple(vector(2,0)),qtuple(vector(1,0))))"
binary_alphabet = data("quantum:qbitstrings(10)")
assert binary_alphabet["copy_text"] == "qbitstrings(10)"
assert binary_alphabet["display_text"] == r"\{0000000000, 0000000001, …, 1111111111\}"
assert data("quantum:"+binary_alphabet["copy_text"]) == binary_alphabet
assert data("quantum:qsetimage(qbitlabel(j,8),qindexrange(0,127),j)")["copy_text"].startswith("qset(vector(qbitlabel(0,8),")

# The higher numbered subsystem is the first tensor axis.
ordered_suits = data(r"quantum:$\vert\clubsuit\rangle_0\vert\heartsuit\rangle_{2}$")["copy_text"]
assert data(f'quantum:replace(replace(({ordered_suits}),"♣",qbasis(1,2)),"♡",qbasis(0,3))')["cells"] == [["0"],["1"],["0"],["0"],["0"],["0"]]

# Keep the square root of a product of projection sums until both states
# are known, even when the dimensions were supplied first.
def squared_projection_sum(state, width):
    projection = f'qmul(qdag(qketstate("k")),qnamedket("{state}"))'
    domain = "qset(vector("+",".join(map(str,range(width)))+"))"
    return f'qsumset(qpower(qbars({projection}),2),{domain},"k")'

left_sum = squared_projection_sum("φ",2)
right_sum = squared_projection_sum("ψ",3)
deferred_root = data(f"quantum:qsqrt(qadjacent({left_sum},{right_sum}))")["copy_text"]
assert data(f'quantum:replace(replace(({deferred_root}),"φ",[0;2*i]),"ψ",[0;0;3])')["copy_text"] == "6"

# Each Cartesian coordinate ranges over its own finite set.
pair_sum = data(r"quantum:$\sum_{(a,b)\in\Sigma\times\Gamma}{10a+b}$")["copy_text"]
assert data(f'quantum:replace(replace(({pair_sum}),"Σ",qset(vector(3,5))),"Γ",qset(vector(2,7,8)))')["copy_text"] == "274"
assert b"distinct coordinate" in run(r"quantum:$\sum_{(a,a)\in\Sigma\times\Gamma}{a}$","--json",success=False).stderr

# A per-factor adjoint must conjugate and transpose the supplied operator.
adjoints = data(r"quantum:$M_{n-1}^{\dagger}\otimes\cdots\otimes M_0^{\dagger}$")["copy_text"]
assert data(f'quantum:replace(replace(({adjoints}),"M_0",[0,i;1,0]),n,1)')["copy_text"] == "matrix(2,2,[0,1,−i,0])"

# Bind unequal state vectors before the register width. The phase and
# its position distinguish descending from ascending tensor order.
ket_series = data(r"quantum:$\vert \psi_{n-1}\rangle\otimes\cdots\otimes\vert \psi_0\rangle$")["copy_text"]
assert data(f'quantum:replace(replace(replace(({ket_series}),"ψ_0",[1;0]),"ψ_1",[0;i]),n,2)')["cells"] == [["0"],["0"],["i"],["0"]]
assert b"column vector" in run("quantum:qindexedket([1,0;0,1])","--json",success=False).stderr

# Prose separates complete state expressions and preserves their order.
state_list = data(r"quantum:$$\vert 1\rangle,\quad\text{and}\quad -\vert 0\rangle.$$")
ordered = data(r"quantum:\begin{gathered}\vert 1\rangle\\-\vert 0\rangle\end{gathered}")
assert state_list == ordered == data("quantum:"+state_list["copy_text"])
assert data(r"quantum:$\vert 1\rangle = \vert 1\rangle;\;$")["copy_text"] == "1"
assert data(r"quantum:$[1,2;3,4]$")["cells"] == [["1","2"],["3","4"]]

# The first coordinate belongs to the first printed alphabet, including
# when indices count down. Set literals can be supplied before the width.
alphabets = data(r"quantum:$\Sigma_{n-1}\times\cdots\times\Sigma_0$")["copy_text"]
assert data("quantum:"+alphabets)["copy_text"] == alphabets
pairs = f'quantum:replace(replace(replace(({alphabets}),"Σ_0",qset(vector(2,3))),"Σ_1",qset(vector(7))),n,2)'
assert data(pairs)["copy_text"] == "qset(vector(qtuple(vector(7,2)),qtuple(vector(7,3))))"
member = data(r"quantum:$(a,b)\in\Sigma\times\Gamma$")["copy_text"]
pauli_channel = data(r"quantum:$\Phi(\rho) = p_I I\rho I + p_X X\rho X+p_Y Y \rho Y + p_Z Z \rho Z$")["copy_text"]
for gate in "IXYZ":
    mixture = pauli_channel
    for label in "IXYZ":
        mixture = f'replace(({mixture}),"p_{label}",{int(label == gate)})'
    mixture = f'replace(({mixture}),"ρ",[2/3,(1-i)/6;(1+i)/6,1/3])'
    for actual in (gate, "X" if gate == "I" else "I"):
        assert data(f'quantum:replace(({mixture}),"Φ",vector({actual}))')["copy_text"] == str(int(actual == gate))
channel_end = data(r"quantum:$\Phi(\rho,t\to1)$")["copy_text"]
rotation = "vector([cos(pi*t/2),-sin(pi*t/2);sin(pi*t/2),cos(pi*t/2)])"
assert data(f'quantum:replace(replace(({channel_end}),"ρ",[1,0;0,0]),"Φ",{rotation})')["copy_text"] == "matrix(2,2,[0,0,0,1])"
for formula, result in [(r"\lim_{x\to0^{-}}{\frac{|x|}{x}}","−1"),
                        (r"\lim_{x\to0^+}{\frac{|x|}{x}}","1"),
                        (r"\lim_{x\to3}{\lim_{p\to x}{p+1}}","4")]:
    assert data("quantum:$"+formula+"$")["copy_text"] == result
assert b"approach arrow" in run(r"quantum:$\lim_{x=0}{x}$","--json",success=False).stderr
identity_list = data(r"quantum:$\mathbb{I}_{n-1},\ldots,\mathbb{I}_0$")["copy_text"]
assert data(f'quantum:replace(replace(replace(({identity_list}),n,2),"dim_1",2),"dim_0",3)')["copy_text"] == "vector(matrix(2,2,[1,0,0,1]),matrix(3,3,[1,0,0,0,1,0,0,0,1]))"
assert b"dimensions" in run(f'quantum:replace(replace(({identity_list}),n,1),"dim_0",0)',"--json",success=False).stderr
shift = data(r"quantum:$\sum_{j=0}^{2}\vert(j-1)\bmod 3\rangle\langle j\vert$")
assert shift["copy_text"] == "matrix(3,3,[0,1,0,0,0,1,1,0,0])"
assert data(r"quantum:$\{0,1\}\times\{3\}$")["copy_text"] == "qset(vector(qtuple(vector(0,3)),qtuple(vector(1,3))))"
assert data(r"quantum:$\{0\}×\{1\}×\{3\}$")["copy_text"] == "qset(vector(qtuple(vector(0,1,3))))"
assert data(f'quantum:replace(replace(replace(replace(({member}),"Σ",qset(vector(3))),"Γ",qset(vector(9))),"a",3),"b",9)')["copy_text"] == "1"
assert data("quantum:qcartesianseries(vector(qset(vector(1)),qset(vector())),1)")["copy_text"] == "qset(vector())"
assert b"32 tuple coordinates" in run("quantum:qcartesianseries(qindexedentries('A_',0,32,vector()),1)","--json",success=False).stderr

for literal, register, outcome in [(r"$\mathsf{X}=1$", "X", "1"),
                                   (r"$\mathsf{Y}=b$", "Y", "'b'")]:
    comparison = data("quantum:"+literal)["copy_text"]
    assert comparison == f"('{register}')==({outcome})"
    for observed in (0,1):
        bound = f'replace(({comparison}),"{register}",{observed})'
        if outcome == "'b'":
            bound = f'replace(({bound}),"b",1)'
        assert data("quantum:"+bound)["copy_text"] == str(observed)

# Joint events keep the system order. Conditional probabilities divide by
# the marginal of the system after the bar, including on rectangular tables.
event = data(r"quantum:$\operatorname{Pr}(\mathsf{Y}=b\mid\mathsf{X}=a)$")
assert event["display_text"] == "Pr(Y = b | X = a)"
assert data("quantum:"+event["copy_text"]) == event
for expr, expected in [("qjointprob([1/8,1/4,1/8;1/4,0,1/4],0,1)", "1 ∕ 4"),
                       ("qconditionalprob([1/8,1/4,1/8;1/4,0,1/4],0,1)", "1 ∕ 2"),
                       ("qconditionalprob(matrix(1,2,[1/4,3/4]),0,1)", "3 ∕ 4"),
                       ("qconditionalprob(matrix(2,1,[1/4,3/4]),1,0)", "1")]:
    assert data("quantum:"+expr)["copy_text"] == expected
for expr, diagnostic in [("qconditionalprob([0,0;1,0],0,0)", b"probability zero"),
                         ("qjointprob([1,1;0,0],0,0)", b"sum to one"),
                         ("qjointprob([1/2,1;0,-1/2],0,0)", b"between zero and one"),
                         ("qjointprob([0,0;0,1],0,2)", b"outside"),
                         ("qjointprob([0,0;0,1],0,1/2)", b"nonnegative integer")]:
    assert diagnostic in run("quantum:"+expr, "--json", success=False).stderr
summed = data(r"quantum:$\sum_{c\in\Gamma}\operatorname{Pr}((\mathsf{X},\mathsf{Y})=(a,c))$")["copy_text"]
bound = f'replace(replace(replace(({summed}),"X,Y",[1/8,3/8;1/4,1/4]),"Γ",qset(vector(0,1))),"a",0)'
assert data("quantum:"+bound)["copy_text"] == "1 ∕ 2"

# A tuple with descending indices keeps its order and substitution history.
reverse = data(r"quantum:$(a_{n-1},\ldots,a_0)$")["copy_text"]
assert data("quantum:" + reverse)["copy_text"] == reverse
assert data(f'quantum:replace(replace(({reverse}),"a_1",7),n,3)')["copy_text"] == 'qtuple(vector("a_2",7,"a_0"))'
for first, last, expected in [(12,9,range(12,8,-1)), (9,12,range(9,13))]:
    source = rf"quantum:$(a_{{{first}}},\ldots,a_{{{last}}})$"
    assert data(source)["copy_text"] == "qtuple(vector(" + ",".join(f'"a_{i}"' for i in expected) + "))"
run(r"quantum:$(a_{n-1},\ldots,b_0)$", "--json", success=False)

# A free matrix name remains bindable anywhere in an equality chain.
for expression in ("R=H*S*H=H*S*H", "H*S*H=R=H*S*H", "H*S*H=H*S*H=R"):
    chain = data("quantum:" + expression)["copy_text"]
    assert chain.startswith("qequalchain(") and data("quantum:" + chain)["copy_text"] == chain
    for operator, truth in [("H*S*H", "1"), ("X", "0")]:
        assert data(f"quantum:replace(({chain}),'R',{operator})")["copy_text"] == truth

# Numeric basis transitions obtain their dimensions from the bound operator.
transitions = r"$$A \vert 0\rangle = \vert 1\rangle,\quad A \vert 1\rangle = \vert 2\rangle,\quad\text{and}\quad A \vert 2\rangle = \vert 0\rangle$$"
transition = data("quantum:" + transitions)
copied = transition["copy_text"]
assert transition["display_text"] == "A|0⟩ = |1⟩, A|1⟩ = |2⟩, A|2⟩ = |0⟩"
assert data("quantum:" + copied) == transition
for matrix, truth in [("matrix(3,3,[0,0,1,1,0,0,0,1,0])", "1"),
                      ("identity(3)", "0"), ("matrix(4,3,[0,0,1,1,0,0,0,1,0,0,0,0])", "1")]:
    assert data(f"quantum:replace({copied},'A',{matrix})")["copy_text"] == truth
assert b"indices" in run(f"quantum:replace({copied},'A',identity(2))", "--json", success=False).stderr
single_transition = data(r"quantum:$B \vert 2\rangle = \vert 0\rangle$")
assert single_transition["display_text"] == "B|2⟩ = |0⟩"
assert data(f"quantum:replace({single_transition['copy_text']},'B',matrix(1,3,[0,0,1]))")["copy_text"] == "1"
assert b"explicit dimension" in run("quantum:|2>", "--json", success=False).stderr

# A displayed list of matrices can use prose before its last item.
matrix_rows = [r"\begin{pmatrix}1&0\\0&0\end{pmatrix}", r"\begin{pmatrix}2&3\\4&5\end{pmatrix}"]
matrix_list = r"$$" + r",\quad\text{and}\quad".join(matrix_rows) + ".$$"
expected_rows = data(r"quantum:\begin{gathered}" + r"\\".join(matrix_rows) + r"\end{gathered}")
assert data("quantum:" + matrix_list) == expected_rows
assert data("quantum:" + matrix_list.replace(",", "")) == expected_rows
assert data("quantum:" + expected_rows["copy_text"]) == expected_rows
assert data("quantum:$$" + "+".join(matrix_rows) + "$$")["cells"] == [["3", "3"], ["4", "5"]]

nested_matrix = matrix_rows[1].replace("2&", r"\operatorname{Tr}(" + matrix_rows[0] + ")&")
nested_copy = data(r"quantum:$$" + nested_matrix + r",\quad" + matrix_rows[0] + "$$")["copy_text"]
assert nested_copy == data(r"quantum:\begin{gathered}" + nested_matrix + r"\\" + matrix_rows[0] + r"\end{gathered}")["copy_text"]

# The weights and both sides of each projector share the same endpoint.
spectral = r"$$M = w_0 |v_0><v_0| + \cdots + w_{n-1} |v_{n-1}><v_{n-1}|$$"
for extent, count, bound in [("n-1", "n", "2"), ("k+1", '"k"', "0"), ("i+1", '"i"', "0"), ("i", '"i"', "1"), ("c", '"c"', "1")]:
    copied = data("quantum:" + spectral.replace("n-1", extent))["copy_text"]
    assert "qspectralsum" in copied and data("quantum:" + copied)["copy_text"] == copied
    expr = copied
    for symbol, value in [('"w_0"', "3"), ('"v_0"', "|+i>"), (count, bound),
                          ('"w_1"', "1"), ('"v_1"', "|-i>")]:
        expr = f"replace(({expr}),{symbol},{value})"
    for candidate, truth in [("[2,-i;i,2]", "1"), ("[2,i;-i,2]", "0")]:
        assert data(f'quantum:replace(({expr}),"M",{candidate})')["copy_text"] == truth
run("quantum:" + spectral.replace("><v_{n-1}", "><v_{n+1}"), "--json", success=False)

traced = r"$$w_0 \operatorname{Tr}(|v_0><v_0|) + \cdots + w_{n-1} \operatorname{Tr}(|v_{n-1}><v_{n-1}|)$$"
trace_copy = data("quantum:" + traced)["copy_text"]
assert "qspectraltracesum(" in trace_copy and data("quantum:" + trace_copy)["copy_text"] == trace_copy
for symbol, value in [('n', '2'), ('"w_0"', '3'), ('"w_1"', '1'), ('"v_0"', '2*|+i>'), ('"v_1"', '|-i>')]:
    trace_copy = f'replace(({trace_copy}),{symbol},{value})'
assert data("quantum:" + trace_copy)["copy_text"] == "13"
short_trace = traced.replace(r"\operatorname{Tr}", r"\mathrm{tr}")
mixed_dimension = data("quantum:" + short_trace)["copy_text"]
for symbol, value in [('n', '2'), ('"w_0"', '3'), ('"w_1"', '1'), ('"v_0"', '|00>'), ('"v_1"', '|0>')]:
    mixed_dimension = f'replace(({mixed_dimension}),{symbol},{value})'
assert data("quantum:" + mixed_dimension)["copy_text"] == "4"
for limit, bound in [("i", "1"), ("i+1", "0")]:
    series = data(r"quantum:$$w_0 + \cdots + w_{" + limit + "}$$")["copy_text"]
    assert data(f'quantum:replace(replace(replace(({series}),"i",{bound}),"w_0",3),"w_1",1)')["copy_text"] == "4"
run("quantum:" + traced.replace(r"\operatorname{Tr}(|v_{n-1}><v_{n-1}|)", "|v_{n-1}><v_{n-1}|"),
    "--json", success=False)

# An XOR of one bit contributes a scalar phase to the difference of basis kets.
phase_state = r"\vert 0\oplus a\rangle-\vert 1\oplus a\rangle"
signed_state = r"(-1)^a\bigl(\vert 0\rangle-\vert 1\rangle\bigr)"
for sign, truth in [("", "1"), ("-", "0")]:
    phase = data("quantum:$" + sign + signed_state + "=" + phase_state + "$")["copy_text"]
    assert data("quantum:" + phase)["copy_text"] == phase
    for bit in (0, 1):
        assert data(f'quantum:replace(({phase}),"a",qbitlabel({bit},1))')["copy_text"] == truth
run(f'quantum:replace(({phase}),"a",qbitlabel(1,2))', "--json", success=False)
assert data("quantum:$2^ a (3)$")["copy_text"] == data("quantum:$3 \\cdot 2^{a}$")["copy_text"]
assert data("quantum:$2^{a(3)}$")["copy_text"] != data("quantum:$2^a(3)$")["copy_text"]

# Descending words retain the place values and the explicitly printed bits.
word_range = data(r"quantum:bitword:$x_{n-1}\ldots x_1 x_0$")["copy_text"]
assert data("quantum:" + word_range)["copy_text"] == word_range
word_input = f"replace(({word_range}),n,3)"
for index, bit in [(2, 0), (0, 1), (1, 0)]:
    word_input = f'replace(({word_input}),"x_{index}",{bit})'
assert data("quantum:" + word_input)["copy_text"] == "qbitlabel(1,3)"
run(f"quantum:replace(({word_range}),n,1)", "--json", success=False)
run(r"quantum:bitword:$x_4\cdots x_2 x_0$", "--json", success=False)
run(r"quantum:bitword:$x_4\cdots y_0$", "--json", success=False)
range_query = data(r"quantum:oracles:$f(x_{1}\cdots x_0)=1$")["copy_text"]
range_query = f'replace(replace(({range_query}),"x_0",1),"x_1",0)'
assert data(f'quantum:replace(({range_query}),"f",qset(vector(qtuple(vector(qbitlabel(1,2),1)))) )')["copy_text"] == "1"

# A register declaration scopes the word inside the oracle argument.
phase_sum = data(r"quantum:oracles:$\sum_{x_1\cdots x_0 \in \Sigma^2} f(x_1\cdots x_0)$")["copy_text"]
truth_table = "qset(vector(" + ",".join(
    f"qtuple(vector(qbitlabel({i},2),{int(i != 0)}))" for i in range(4)
) + "))"
assert data(f'quantum:replace(({phase_sum}),"f",{truth_table})')["copy_text"] == "3"

nested_phase = data(
    r"quantum:oracles:$\sum_{x_{n-1}\cdots x_0\in\Sigma^n}"
    r"\sum_{y_{n-1}\cdots y_0\in\Sigma^n}"
    r"(-1)^{f(x_{n-1}\cdots x_0)+x_{n-1}y_{n-1}+\cdots+x_0y_0}$"
)["copy_text"]
assert data(f'quantum:replace(replace(({nested_phase}),"f",{truth_table}),n,2)')["copy_text"] == "4"

# Superscripts in an oracle sample list name successive samples, including repeats.
sample_queries = data(r"quantum:oracles:$f(x^1),\ldots,f(x^k)$")["copy_text"]
assert data("quantum:" + sample_queries)["copy_text"] == sample_queries
sample_input = f'replace(({sample_queries}),"f",{truth_table})'
for key, value in [("x^2", "qbitlabel(0,2)"), ("k", "3"),
                   ("x^1", "qbitlabel(3,2)"), ("x^3", "qbitlabel(3,2)")]:
    sample_input = f'replace(({sample_input}),"{key}",{value})'
assert data("quantum:" + sample_input)["copy_text"] == "qtuple(vector(1,0,1))"
run(f'quantum:replace(({sample_queries}),"k",0)', "--json", success=False)
run(r"quantum:oracles:$f(x^1),\ldots,g(x^k)$", "--json", success=False)

expanded_dot = data(r"quantum:bitword:$a_1 b_1 \oplus \cdots \oplus a_0 b_0$")["copy_text"]
assert data("quantum:" + expanded_dot)["copy_text"] == expanded_dot
for key, value in [("a_1", 1), ("a_0", 1), ("b_1", 1), ("b_0", 1)]:
    expanded_dot = f'replace(({expanded_dot}),"{key}",{value})'
assert data("quantum:" + expanded_dot)["copy_text"] == "0"
run(r"quantum:bitword:$a_1 b_1 \oplus \cdots \oplus a_0 c_0$", "--json", success=False)

parity_cases = (
    r"quantum:bitword:$\begin{cases}5 & a_{{1}} b_1 + \cdots + a_0 b_0 \text{ is odd}\\"
    r"7 & a_1 b_1 + \cdots + a_0 b_0 \text{ is even}\end{cases}$"
)
parity_copy = data(parity_cases)["copy_text"]
for last_bit, expected in [(0, "7"), (1, "5")]:
    expr = parity_copy
    for key, value in [("a_1", 1), ("b_1", 0), ("a_0", 1), ("b_0", last_bit)]:
        expr = f'replace(({expr}),"{key}",{value})'
    assert data("quantum:" + expr)["copy_text"] == expected
run(parity_cases.replace("is odd", "is prime"), "--json", success=False)

component_xor = data(
    r"quantum:bitword:$(a_0 \oplus b_0)c_0 \oplus \cdots \oplus (a_0 \oplus b_0)c_0$"
)["copy_text"]
for key, value in [("a_0", 1), ("b_0", 0), ("c_0", 1)]:
    component_xor = f'replace(({component_xor}),"{key}",{value})'
assert data("quantum:" + component_xor)["copy_text"] == "1"
run(r"quantum:bitword:$(a_1 \oplus b_1)c_1 \oplus \cdots \oplus (a_0 \oplus d_0)c_0$",
    "--json", success=False)

promise_cases = data(
    r"quantum:oracles:$\begin{cases}1 & \text{if $f$ is constant}\\"
    r"0 & \text{if $f$ is balanced}\end{cases}$"
)["copy_text"]
balanced_graph = truth_table.replace("qbitlabel(1,2),1", "qbitlabel(1,2),0")
assert data(f'quantum:replace(({promise_cases}),"f",{balanced_graph})')["copy_text"] == "0"
run(f'quantum:replace(({promise_cases}),"f",{truth_table})', "--json", success=False)
run("quantum:qconstantoracle(qset(vector(qtuple(vector(qbitlabel(1,2),0)))))", "--json", success=False)

aligned_hadamards = data(
    r"quantum:oracles:$\begin{aligned} & H^{\otimes 2}\vert x_1 x_0\rangle\\"
    r"&=\bigl(H\vert x_1\rangle\bigr)\otimes\cdots\otimes\bigl(H\vert x_0\rangle\bigr)\\"
    r"&=H^{\otimes 2}\vert x_1 x_0\rangle\end{aligned}$"
)["copy_text"]
assert data(f'quantum:replace(replace(({aligned_hadamards}),"x_1",0),"x_0",1)')["copy_text"] == "1"
assert data(r"quantum:oracles:$\sum_{a\in\Sigma}(-1)^a$")["copy_text"] == "0"

zero_word = data(r"quantum:bitword:$0^n$")["copy_text"]
assert data(f"quantum:replace(({zero_word}),n,4)")["copy_text"] == "qbitlabel(0,4)"
assert data("quantum:$0^4$")["copy_text"] == "0"
word_equality = data(r"quantum:bitword:$s\oplus y = 0^n$")["copy_text"]
for y_value, expected in [(2, "1"), (0, "0")]:
    expr = f'replace(replace(replace(({word_equality}),n,3),"s",qbitlabel(2,3)),y,qbitlabel({y_value},3))'
    assert data("quantum:" + expr)["copy_text"] == expected

bit_action = data(r"quantum:bitword:$H\vert a\rangle=(\vert0\rangle+(-1)^a\vert1\rangle)/\sqrt{2}$")["copy_text"]
for bit in ["0", "1", "qbitlabel(0,1)", "qbitlabel(1,1)"]:
    assert data(f'quantum:replace(({bit_action}),"a",{bit})')["copy_text"] == "1"
phase_product = data(r"quantum:bitword:$(-1)^{ab}$")["copy_text"]
assert data(f'quantum:replace(replace(({phase_product}),"a",qbitlabel(1,1)),"b",1)')["copy_text"] == "−1"
run(f'quantum:replace(replace(({phase_product}),"a",1),"b",qbitlabel(1,2))', "--json", success=False)

repeated_input = data(r"quantum:$X^{\otimes n}\vert1\cdots1\rangle$")["copy_text"]
assert "register width" not in repeated_input
assert data(f"quantum:replace(({repeated_input}),n,2)")["copy_text"] == "matrix(4,1,[1,0,0,0])"
assert "register width" in data(r"quantum:$U^{\otimes n}\vert1\cdots1\rangle$")["copy_text"]
explicit_width = data(r"quantum:$X^{\otimes n}\vert1^{\otimes m}\rangle$")["copy_text"]
run(f'quantum:replace(replace(({explicit_width}),n,2),"m",1)', "--json", success=False)

word_tuple = data("quantum:bitword:$(001$, $1$, and $001)$")["copy_text"]
assert word_tuple == "qtuple(vector(qbitlabel(1,3),qbitlabel(1,1),qbitlabel(1,3)))"
assert data("quantum:" + word_tuple)["copy_text"] == word_tuple
run("quantum:bitword:$(001$", "--json", success=False)
run("quantum:bitword:$(001$, and $1$, $10)$", "--json", success=False)

# A probability function in Set notation maps each observed word to its weight.
prob_lookup = data("quantum:sets:$p(y)$")["copy_text"]
assert prob_lookup == "qfiniteapply('p',y)"
distribution = "qset(vector(qtuple(vector(qbitlabel(0,1),1/4)),qtuple(vector(qbitlabel(1,1),3/4))))"
for outcome, weight in enumerate(("1/4", "3/4")):
    bound = prob_lookup.replace("'p'", distribution).replace(",y)", f",qbitlabel({outcome},1))")
    assert data(f"quantum:({bound})-({weight})")["copy_text"] == "0"
assert data("quantum:$p(y)$")["copy_text"] == "'p'y"
assert data("quantum:sets:$p(x,y)$")["copy_text"] == "qprobabilitycall(x,y)"

# Simon's post-processing uses matrix multiplication over the two-element field.
assert data("quantum:gf2:$M v$")["copy_text"] == "qgf2mul('M','v')"
assert data("quantum:gf2:A B C")["copy_text"] == "qgf2mul(qgf2mul('A','B'),'C')"
binary_product = "matrix(2,3,[0,1,1,1,0,0]) * matrix(3,1,[0,1,1])"
assert data("quantum:gf2:" + binary_product)["cells"] == [["0"], ["0"]]
assert data("quantum:" + binary_product)["cells"] == [["2"], ["0"]]
run("quantum:gf2:M matrix(2,1,[0,2])", "--json", success=False)

# The encoding table uses epsilon for the zero-length binary word.
for empty in (r"$\varepsilon$", r"$\epsilon$", "ε"):
    assert data("quantum:bitword:" + empty)["copy_text"] == "qbitlabel(0,0)"
assert data(r"quantum:bitword:$\epsilon \oplus \varepsilon$")["copy_text"] == "qbitlabel(0,0)"
assert data(r"quantum:$\varepsilon$")["copy_text"] == "'ε'"
assert data(r"quantum:bitword:$\epsilon_1$")["copy_text"] == '"ε_1"'

# Set notation keeps the index of a circuit family available for substitution.
family_size = data(r"quantum:sets:$t(n)=\operatorname{size}(C_n)$")["copy_text"]
for count, expected in ((73, "1"), (31, "0")):
    bound = f"replace(replace(replace(({family_size}),n,4),size(C_4),73),t(4),{count})"
    assert data("quantum:" + bound)["copy_text"] == expected
assert data("quantum:sets:replace(B_{k},k,7)")["copy_text"] == '"B_7"'
assert data("quantum:C_n")["copy_text"] == '"C_n"'

# A binary-oracle query and its surrounding predicate share the same search variable.
search_graph = "qset(vector(qtuple(vector(qbitlabel(0,1),0)),qtuple(vector(qbitlabel(1,1),1))))"
for search_symbol in "nxyz":
    query = data(f"quantum:oracles:$f({search_symbol})=1$")["copy_text"]
    for index in range(2):
        bound = f"replace(replace(({query}),f,{search_graph}),{search_symbol},bitstring({index},1))"
        assert data("quantum:" + bound)["copy_text"] == str(index)
xor_ket = data(r"quantum:bitword:$\vert a \oplus f(x)\rangle$")["copy_text"]
assert data(f"quantum:replace(replace(replace(({xor_ket}),a,1),f,{search_graph}),x,bitstring(1,1))")["cells"] == [["1"], ["0"]]

# The Grover diffusion oracle takes the OR of all bits in its input word.
word_or = data(r"quantum:bitword:$\mathrm{OR}(x)$")["copy_text"]
assert word_or == "qwordor(x)"
for bits, expected in (("000", "0"), ("001", "1"), ("110", "1")):
    assert data(f"quantum:replace({word_or},x,bitstring(\"{bits}\"))")["copy_text"] == expected
    assert data(f"quantum:bitword:OR({bits})")["copy_text"] == expected
assert data("quantum:qwordor(qbitlabel(0,0))")["copy_text"] == "0"
run("quantum:bitword:OR([1,2])", "--json", success=False)
run("quantum:bitword:OR(1,0)", "--json", success=False)
phase_action = data(r"quantum:oracles:$Z_f\vert x\rangle = (-1)^{f(x)}\vert x\rangle$")["copy_text"]
phase_probe = f'replace(replace(replace(({phase_action}),f,{search_graph}),x,bitstring(1,1)),"Z_f",Z)'
assert data("quantum:" + phase_probe)["copy_text"] == "1"

# In Set notation the same bare S names the set and the uniform ket's label.
pair_set = "qset(vector(bitstring(0,2),bitstring(3,2)))"
assert data(f"quantum:sets:replace(S,S,{pair_set})")["copy_text"] == data("quantum:"+pair_set)["copy_text"]
uniform_pair = data(f"quantum:sets:replace(|S>,S,{pair_set})")["copy_text"]
assert data(f"quantum:norm(({uniform_pair})-(basis(0,4)+basis(3,4))/sqrt(2))")["copy_text"] == "0"
assert data("quantum:sets:S*|1>")["cells"] == [["0"], ["i"]]
assert data("quantum:sets:S^1")["copy_text"] == "qunitcircle()"

# Tensor powers inside a ket label and between repeated gates share the
# same register-width rules as explicit tensor powers.
zero_register = data(r"quantum:$\vert 0^{\otimes n}\rangle$")["copy_text"]
assert data(f"quantum:replace(({zero_register}),n,2)")["copy_text"] == "matrix(4,1,[1,0,0,0])"
assert data(r"quantum:$\bra{1^{\otimes 2}}$")["copy_text"] == "vector(0,0,0,1)"
assert data(r"quantum:$\ket{0^{\otimes 2}\otimes 1}$")["copy_text"] == "matrix(8,1,[0,1,0,0,0,0,0,0])"
gate_series = data(r"quantum:$H\otimes\cdots\otimes H$")["copy_text"]
assert data("quantum:" + gate_series)["copy_text"] == gate_series
assert data(f'quantum:replace(({gate_series}),"register width",2)=H@H')["copy_text"] == "1"
run(r"quantum:$H\otimes\cdots\otimes X$", "--json", success=False)
run(r"quantum:$\ket{1^{\otimes -1}}$", "--json", success=False)

# A centered dot inside XOR can still become parity or an ordinary product.
distributive = data(r"quantum:$(s\cdot x)\oplus(y\cdot x)=(s\oplus y)\cdot x$")["copy_text"]
assert data("quantum:" + distributive)["copy_text"] == distributive
for values, truth in [(("qbitlabel(1,2)", "qbitlabel(2,2)", "qbitlabel(3,2)"), "1"),
                      (("1", "2", "3"), "0")]:
    expr = distributive
    for symbol, value in zip(('"s"', 'y', 'x'), values):
        expr = f"replace(({expr}),{symbol},{value})"
    assert data("quantum:" + expr)["copy_text"] == truth
run(r"quantum:$(s\cdot x)\oplus(-1)$", "--json", success=False)

# Binary oracles keep a query until a truth table and a word are supplied.
alphabet_sum = r"\sum_{x\in(\Sigma)^1}"
identity_graph = "qset(vector(qtuple(vector(qbitlabel(0,1),0)),qtuple(vector(qbitlabel(1,1),1))))"
for index in ("x", "c", "i", "e"):
    total = data("quantum:oracles:$" + alphabet_sum.replace("x", index) + f"f({index})$")["copy_text"]
    assert data(f'quantum:replace(({total}),"f",{identity_graph})')["copy_text"] == "1"
nested = data("quantum:oracles:$" + alphabet_sum + r"\bigl(f(x)+" + alphabet_sum + r"f(x)\bigr)$")["copy_text"]
assert data(f'quantum:replace(({nested}),"f",{identity_graph})')["copy_text"] == "3"
free_key = data("quantum:oracles:$" + alphabet_sum + 'f("x")$')["copy_text"]
assert data(f'quantum:replace(replace(({free_key}),"f",{identity_graph}),"x",qbitlabel(1,1))')["copy_text"] == "2"
oracle_graph = 'qset(vector(qtuple(vector(qbitlabel(1,2),1)),qtuple(vector(qbitlabel(1,1),0))))'
for oracle in "fgh":
    query = data(f"quantum:oracles:{oracle}(c)")["copy_text"]
    assert data("quantum:" + query)["copy_text"] == query
    for width, expected in [(1, "0"), (2, "1")]:
        bound = f'replace(replace(({query}),"{oracle}",{oracle_graph}),"c",qbitlabel(1,{width}))'
        assert data("quantum:" + bound)["copy_text"] == expected
    literal = data(f"quantum:oracles:{oracle}((01))")["copy_text"]
    assert data(f'quantum:replace(({literal}),"{oracle}",{oracle_graph})')["copy_text"] == "1"
for bad_query in ("f(2)", "f(-1)", "f(0,1)", "h()"):
    run("quantum:oracles:" + bad_query, "--json", success=False)
bad_output = 'qset(vector(qtuple(vector(qbitlabel(1,2),qbitlabel(1,2)))))'
run(f'quantum:replace(({literal}),"h",{bad_output})', "--json", success=False)
assert "qgraphapply" not in data("quantum:f(0)")["copy_text"]

# Binary-word mode concatenates oracle outputs in source order.
word = data("quantum:bitword:$f(0)f(1)$")["copy_text"]
assert data("quantum:" + word)["copy_text"] == word
graph = 'qset(vector(qtuple(vector(qbitlabel(0,1),1)),qtuple(vector(qbitlabel(1,1),0))))'
assert data(f'quantum:replace(({word}),"f",{graph})')["copy_text"] == "qbitlabel(2,2)"
assert data("quantum:bitword:$h((01))$")["copy_text"].count("qbitlabel(1,2)") == 1
run("quantum:bitword:$g(2)g(1)$", "--json", success=False)
run(f'quantum:replace(({word}),"f",{graph.replace(",1))", ",2))", 1)})', "--json", success=False)

# In a one-bit XOR identity, a shared Pauli exponent is the same bit.
bit_ket = r"\vert b\oplus (c)\rangle"
for pauli in [r"(X^c)\vert b\rangle", r"X^c\cdot\vert b\rangle", r"X^c(\vert b\rangle)"]:
    controlled_flip = data("quantum:$" + pauli + "=" + bit_ket + "$")["copy_text"]
    assert data("quantum:" + controlled_flip)["copy_text"] == controlled_flip
    assert data(f'quantum:replace(replace(({controlled_flip}),"b",0),"c",qbitlabel(1,1))')["copy_text"] == "1"
run(f'quantum:replace(({controlled_flip}),"c",qbitlabel(0,2))', "--json", success=False)
run(f'quantum:replace(({controlled_flip}),"c",1/2)', "--json", success=False)
assert "qcontrolbit" not in data(r"quantum:$X^{c}\vert b\rangle$")["copy_text"]

# The unindexed identity takes its dimension from the ket on its right.
identity_ket = data(r"quantum:$\mathbb{I}\vert b\rangle$")["copy_text"]
assert data(f'quantum:replace(({identity_ket}),"b",[0;0;1])')["copy_text"] == "matrix(3,1,[0,0,1])"
assert data(r"quantum:$\vert b\rangle=\mathbb{I}\vert b\rangle$")["copy_text"] == "1"
assert data(r"quantum:$\mathbb{I}\vert 01\rangle$")["copy_text"] == "matrix(4,1,[0,1,0,0])"
negated_bit = data(r"quantum:$\vert\neg b\rangle$")["copy_text"]
assert data(r"quantum:$\vert\neg{b}\rangle$")["copy_text"] == negated_bit
assert data(f'quantum:replace(({negated_bit}),"b",qbitlabel(1,1))')["copy_text"] == "matrix(2,1,[1,0])"
assert data(r"quantum:$\vert\neg 0\rangle$")["copy_text"] == "matrix(2,1,[0,1])"
run(r"quantum:$\vert\neg 2\rangle$", "--json", success=False)

# Inside a ket XOR, f(01) queries a two-bit key. Its Boolean output flips one bit.
oracle_xor = data(r"quantum:$\vert 1 \oplus f(01)\rangle$")["copy_text"]
assert "qgraphapply('f',qbitlabel(1,2))" in oracle_xor
assert data(r"quantum:$\vert 1 \oplus f((01))\rangle$")["copy_text"] == oracle_xor
run(r"quantum:$\vert 1 \oplus f(0.0)\rangle$", "--json", success=False)
assert data("quantum:" + oracle_xor)["copy_text"] == oracle_xor
one_key = "qset(vector(qtuple(vector(qbitlabel(1,2),1))))"
assert data(f'quantum:replace(({oracle_xor}),"f",{one_key})')["copy_text"] == "matrix(2,1,[1,0])"
assert data("quantum:qoplus(0,qbitlabel(1,1))")["copy_text"] == "qbitlabel(1,1)"
width_copy = data("quantum:qoplus(1,qbitlabel(0,n))")["copy_text"]
assert data(f"quantum:replace(({width_copy}),n,1)")["copy_text"] == "qbitlabel(1,1)"
run("quantum:qoplus(qbitlabel(0,2),1)", "--json", success=False)
run("quantum:qoplus(qbitlabel(0,1),2)", "--json", success=False)

# The two Deutsch tables retain entries and leading zero bits through Copy.
oracle_table = r"\begin{array}{c|c} a & f_2(a) \\ \hline 0 & 0 \\ 1 & 1 \end{array}"
strut = r"\rule[-10mm]{0mm}{10mm}"
tables = data("quantum:$" + strut + oracle_table + r"\qquad" + oracle_table + "$")["copy_text"]
assert data(f"quantum:element(element(({tables}),2),3,2)")["copy_text"] == "1"
word_table = r"\begin{array}{cc}\mathsf{function}&\mathsf{string}\\\hline f_{7}&001\end{array}"
words = data("quantum:$" + word_table + "$")["copy_text"]
assert data("quantum:" + words)["copy_text"] == words
assert data(f"quantum:element(({words}),2,2)")["copy_text"] == "qbitlabel(1,3)"
spaced_header = word_table.replace(r"\mathsf{", r"\mathsf {").replace("f_{7}", "f_{12}")
assert '"f_12"' in data("quantum:$" + spaced_header + "$")["copy_text"]
run("quantum:$" + word_table.replace("f_{7}", "f_12") + "$", "--json", success=False)
run("quantum:$" + word_table.replace("001", "021") + "$", "--json", success=False)
run("quantum:$" + strut.replace("{0mm}", "{2mm}") + oracle_table + "$", "--json", success=False)

# A parenthesized Deutsch state remains the operand of the whole indexed oracle.
oracle_action = data(r"quantum:$U_f\bigl(\vert 0\rangle\bigr)$")["copy_text"]
assert data("quantum:" + oracle_action)["copy_text"] == oracle_action
assert data(f'quantum:replace(({oracle_action}),"U_f",X)')["copy_text"] == "matrix(2,1,[0,1])"
assert data('quantum:replace(U_f((2|0>)),"U_f",X)')["copy_text"] == "matrix(2,1,[0,2])"
assert "qoperatorref" not in data("quantum:U_f(|-1|)")["copy_text"]
ket_action = data(r"quantum:$V_{g}(\vert\psi\rangle)$")["copy_text"]
assert data(f'''quantum:replace(replace(({ket_action}),'ψ',[0;1]),"V_g",Y)''')["copy_text"] == "matrix(2,1,[−i,0])"

# IBM-016 defines F as root fidelity. Its square for this pair is 3/4.
fidelity = data(r"quantum:$\operatorname{F}\bigl(\rho,\sigma\bigr)$")["copy_text"]
assert "qrootfidelity(" in fidelity and data("quantum:" + fidelity)["copy_text"] == fidelity
resolved_fidelity = f'replace(replace(({fidelity}),"ρ",[3/4,0;0,1/4]),"σ",[1,0;0,0])'
assert data("quantum:" + resolved_fidelity)["copy_text"] == "√(3) ∕ 2"
pending_state = data("quantum:qrootfidelity([x,0;0,1-x],[1,0;0,0])")["copy_text"]
assert data(f"quantum:replace(({pending_state}),x,3/4)")["copy_text"] == "√(3) ∕ 2"
run('quantum:qrootfidelity("ρ",[-1,0;0,2])', "--json", success=False)
run('quantum:qrootfidelity([1,0;0,∞],"σ")', "--json", success=False)
assert data(r"quantum:$\operatorname{F}(x)$")["copy_text"] == data(r"quantum:$F(x)$")["copy_text"]
norm_identity = data(r"quantum:$\operatorname{F}(\rho,\sigma)=\bigl\|\sqrt{\sigma}\sqrt{\rho}\bigr\|_1.$")["copy_text"]
assert data(f'quantum:replace(replace(({norm_identity}),"ρ",[3/4,0;0,1/4]),"σ",[1,0;0,0])')["copy_text"] == "1"

# Preserve an unresolved norm and bind the whole following radical to Tr.
norm_definition = r"""$$
\| M \|_1 = \operatorname{Tr}\sqrt{M^{\dagger} M},
$$"""
norm_copy = data("quantum:" + norm_definition)["copy_text"]
assert "qtrace(qsqrt(" in norm_copy and data("quantum:" + norm_copy)["copy_text"] == norm_copy
assert data(f'quantum:replace(({norm_copy}),"M",[0,2i;1,0])')["copy_text"] == "1"
distance = data(r"quantum:$\frac{1}{2}\|\rho-\sigma\|_1$")["copy_text"]
assert data(f'quantum:replace(replace(({distance}),"σ",[1/2,0;0,1/2]),"ρ",[1,0;0,0])')["copy_text"] == "1 ∕ 2"
for column in ("matrix(2,1,[3,4])", "matrix(1,1,[2i])"):
    assert data(f'quantum:replace(({norm_copy}),"M",{column})')["copy_text"] == "1"
powered_root = r"quantum:\operatorname{Tr}\sqrt{\begin{pmatrix}4&0\\0&9\end{pmatrix}}^2"
assert data(powered_root)["copy_text"] == "13"
entry_norm = data("quantum:qschatten([x,0;0,0],1)")["copy_text"]
assert data(f"quantum:replace(({entry_norm}),x,-3)")["copy_text"] == "3"
run("quantum:qtrace(qsqrt(4))", "--json", success=False)
run('quantum:qschatten("M",0)', "--json", success=False)

# Conjugate each amplitude while retaining the original column orientation.
for label in ("u", "v"):
    ket_list = r"$\vert \overline{@_0} \rangle,\ldots,\vert \overline{@_{n-1}}\rangle$".replace("@", label)
    copied = data("quantum:" + ket_list)["copy_text"]
    expr = copied
    for key, value in [("n", "2"), (f'"{label}_1"', "matrix(2,1,[4i/5,3/5])"), (f'"{label}_0"', "matrix(2,1,[3/5,4i/5])")]:
        expr = data(f"quantum:replace(({expr}),{key},{value})")["copy_text"]
    expected = data("quantum:vector(matrix(2,1,[3/5,-4i/5]),matrix(2,1,[-4i/5,3/5]))")["copy_text"]
    assert expr == expected and data("quantum:" + expr)["copy_text"] == expr
    bad = f'replace(replace(({copied}),n,1),"{label}_0",[1,0;0,1])'
    assert b"column states" in run("quantum:" + bad, "--json", success=False).stderr

shorthand = r"\ket{\overline{u_{0}}},\ldots,\ket{\overline{u_{n-1}}}"
whole = r"\overline{\ket{u_0}},\ldots,\overline{\ket{u_{n-1}}}"
assert data("quantum:" + shorthand)["copy_text"] == data("quantum:" + whole)["copy_text"]
extended = data("quantum:" + shorthand.replace(r",\ldots", r",\ket{\overline{u_1}},\ldots"))["copy_text"]
assert b"displayed states" in run(f"quantum:replace(({extended}),n,1)", "--json", success=False).stderr

# Each Born probability pairs one indexed effect with the same density.
born_source = r"""$$
\bigl(\operatorname{Tr}(P_0 \rho),\ldots,\operatorname{Tr}(P_{m-1} \rho)\bigr)
$$"""
born_copy = data("quantum:" + born_source)["copy_text"]
assert "qindexedproducttraces" in born_copy and data("quantum:" + born_copy)["copy_text"] == born_copy
for density, expected in [("[2,-i;i,2]/4", "vector(3 ∕ 4,1 ∕ 4)"), ("[2,i;-i,2]/4", "vector(1 ∕ 4,3 ∕ 4)")]:
    bound = born_copy
    for key, value in [('"P_1"', "[1,i;-i,1]/2"), ('"m"', "2"), ('"ρ"', density), ('"P_0"', "[1,-i;i,1]/2")]:
        bound = f"replace(({bound}),{key},{value})"
    assert data("quantum:" + bound)["copy_text"] == expected
for product in (r" \cdot ", " * "):
    explicit = born_source.replace(r" \rho", product + r"\rho")
    assert data("quantum:" + explicit)["copy_text"] == born_copy
for left, right, expected in [("matrix(1,1,[2])", "matrix(1,1,[3])", "vector(6)"),
                              ("matrix(2,1,[1,2])", "matrix(1,2,[2,3])", "vector(8)")]:
    bound = f'replace(replace(replace(({born_copy}),"m",1),"P_0",{left}),"ρ",{right})'
    assert data("quantum:" + bound)["copy_text"] == expected
bad_shape = f'replace(replace(replace(({born_copy}),"m",1),"P_0",[1,0;0,1]),"ρ",vector(x,y))'
assert b"square matrix" in run("quantum:" + bad_shape, "--json", success=False).stderr
run("quantum:" + born_source.replace(r"P_{m-1} \rho", r"P_{m-1} \sigma"), "--json", success=False)

# Both endpoints must apply the same operation to the same indexed family.
for displayed, expected in [
    (r"$P_0^{T},\ldots,P_{m-1}^{T}$", "vector(matrix(2,2,[1,i,−i,1]),matrix(2,2,[4,0,0,9]))"),
    (r"$\sqrt{P_0},\ldots,\sqrt{P_{m-1}}$", "vector(matrix(2,2,[1,0,0,0]),matrix(2,2,[2,0,0,3]))"),
]:
    mapped = data("quantum:" + displayed)["copy_text"]
    first = "[1,-i;i,1]" if "qindexedtransposes" in mapped else "[1,0;0,0]"
    for key, value in [('"P_1"', "[4,0;0,9]"), ('"m"', "2"), ('"P_0"', first)]:
        mapped = data(f"quantum:replace(({mapped}),{key},{value})")["copy_text"]
    assert mapped == expected and data("quantum:" + mapped)["copy_text"] == mapped
for symbol in ("i", "c"):
    extent = r"quantum:$\sqrt{P_0},\ldots,\sqrt{P_{" + symbol + r"-1}}$"
    single = data(extent)["copy_text"]
    for value, expected in [("4", "vector(2)"), ("[4,0;0,9]", "vector(matrix(2,2,[2,0,0,3]))")]:
        bound = data(f'quantum:replace(replace(({single}),"P_0",{value}),"{symbol}",1)')["copy_text"]
        assert bound == expected and data("quantum:" + bound)["copy_text"] == bound
run(r"quantum:$\sqrt{P_2},\ldots,\sqrt{P_1}$", "--json", success=False)
run(r"quantum:$\sqrt{P_0},\ldots,Q_{m-1}^{T}$", "--json", success=False)

# Keep the complex conjugate until the last named amplitude is assigned.
amplitude_matrix = r"""\begin{pmatrix}
\alpha_0 \overline{\alpha_0} & \alpha_0 \overline{\alpha_1} & \cdots & \alpha_0 \overline{\alpha_{n-1}}\\[1mm]
\alpha_1 \overline{\alpha_0} & \alpha_1 \overline{\alpha_1} & \cdots & \alpha_1 \overline{\alpha_{n-1}}\\[1mm]
\vdots & \vdots & \ddots & \vdots\\[1mm]
\alpha_{n-1} \overline{\alpha_0} & \alpha_{n-1} \overline{\alpha_1} & \cdots & \alpha_{n-1} \overline{\alpha_{n-1}}
\end{pmatrix}"""
amplitude_copy = data("quantum:" + amplitude_matrix)["copy_text"]
squared = amplitude_matrix.replace(r"\alpha_0 \overline{\alpha_0}", r"\vert\alpha_0\vert^{2}")
assert data("quantum:" + squared.replace(r"\overline{", r"\overline {"))["copy_text"] == amplitude_copy
amplitudes = amplitude_copy
for key, value in [("n", "3"), ('"α_0"', "1"), ('"α_1"', "i"), ('"α_2"', "0")]:
    amplitudes = data(f"quantum:replace(({amplitudes}),{key},{value})")["copy_text"]
assert amplitudes == "matrix(3,3,[1,−i,0,i,1,0,0,0,0])"
for coefficient in ("[1;0]", "[x;0]", "vector(x,0)"):
    invalid = f'quantum:replace(replace(({amplitude_copy}),n,3),"α_0",{coefficient})'
    assert b"scalar coefficients" in run(invalid, "--json", success=False).stderr
run("quantum:" + amplitude_matrix.replace(r"\alpha_0 \overline{\alpha_1}", r"\alpha_1 \overline{\alpha_0}"), "--json", success=False)

# A zero-based weighted projector sum and its displayed diagonal matrix.
diagonal_density = r"""$$
\rho = \sum_{a = 0}^{n-1} p_a \vert a\rangle \langle a \vert
= \begin{pmatrix}
p_0 & 0 & \cdots & 0\\
0 & p_1 & \ddots & \vdots\\
\vdots & \ddots & \ddots & 0\\
0 & \cdots & 0 & p_{n-1}
\end{pmatrix}.
$$"""
diagonal_copy = data("quantum:" + diagonal_density)["copy_text"]
assert "qindexeddiagonal(" in diagonal_copy and data("quantum:" + diagonal_copy)["copy_text"] == diagonal_copy
for matrix, expected in [("[1/2,0,0;0,1/3,0;0,0,1/6]", "1"), ("[1/3,0,0;0,1/2,0;0,0,1/6]", "0")]:
    expression = diagonal_copy
    for key, value in [('"p_2"', "1/6"), ('"ρ"', matrix), ("n", "3"), ('"p_1"', "1/3"), ('"p_0"', "1/2")]:
        expression = f"replace(({expression}),{key},{value})"
    assert data("quantum:" + expression)["copy_text"] == expected
diagonal_matrix = diagonal_density.split("= ")[-1].split(r"\end{pmatrix}")[0] + r"\end{pmatrix}"
for bound in ("i", "c"):
    symbolic = data("quantum:" + diagonal_matrix.replace("n-1", bound + "-1"))["copy_text"]
    bound_matrix = data(f'quantum:replace(({symbolic}),"{bound}",3)')["copy_text"]
    assert bound_matrix == 'matrix(3,3,["p_0",0,0,0,"p_1",0,0,0,"p_2"])'
projector_sum = diagonal_density.split("=", 1)[1].split("= " + diagonal_matrix)[0].strip()
for identity in (projector_sum + "=" + diagonal_matrix, diagonal_matrix + "=" + projector_sum):
    expression = data("quantum:" + identity)["copy_text"]
    for key, value in [('"p_1"', "1/3"), ("n", "3")]:
        expression = f"replace(({expression}),{key},{value})"
    assert data("quantum:" + expression)["copy_text"] == "1"
run("quantum:" + diagonal_density.replace("0 & p_1", "1 & p_1"), "--json", success=False)

# A qualification limits the points at which a displayed equation is defined.
for interval, allowed, excluded in [("[0,1)", "0", "1"), ("(0,1]", "1", "0")]:
    qualified = r"quantum:$$x^2=x\qquad\text{(for $x \in " + interval + "$)}$$"
    copied = data(qualified)["copy_text"]
    assert data("quantum:" + copied)["copy_text"] == copied
    assert data(f"quantum:replace(({copied}),x,{allowed})")["copy_text"] == "1"
    assert data(f"quantum:replace(({copied}),x,1/2)")["copy_text"] == "0"
    rejected = run(f"quantum:replace(({copied}),x,{excluded})", "--json", success=False)
    assert b"undefined" in rejected.stderr and not rejected.stdout

for parameter in ("i", "c", "H"):
    equation = "$$" + parameter + r"+1\quad\text{(for $" + parameter + r" \in [0,1)$)}$$"
    copied = data("quantum:" + equation)["copy_text"]
    assert data(f'quantum:replace(({copied}),"{parameter}",0)')["copy_text"] == "1"
assert b"two endpoints" in run(r"quantum:$$x\quad\text{(for $x \in [0,1,2]$)}$$", "--json", success=False).stderr

# A textbook equation uses grouped digits. Commas in function calls and
# between complete equations retain their existing meanings.
for literal, integer in [("1,000,000", 1000000), ("-12,345", -12345), ("+987,654", 987654)]:
    equation = data(f"quantum:$N = {literal}$")["copy_text"]
    for value, truth in [(integer, "1"), (integer + 1, "0")]:
        assert data(f"quantum:replace(({equation}),N,{value})")["copy_text"] == truth
assert data("quantum:vector(1=1,234,567)")["copy_text"] == "vector(1,234,567)"
assert data("quantum:1=1,000=0")["copy_text"] == "1"
for malformed in ("1,00,000", "1234,567", "1,2345", "1,234,"):
    run("quantum:N=" + malformed, "--json", success=False)

# IBM-009 and IBM-012 specify only the first block column of U.
block_column = r"""U=\begin{pmatrix}
A_{0} & \fbox{?} & \cdots & \fbox{?} \\[1mm]
A_{1} & \fbox{?} & \cdots & \fbox{?} \\[1mm]
\vdots & \vdots & \ddots & \vdots \\[1mm]
A_{N-1} & \fbox{?} & \cdots & \fbox{?}
\end{pmatrix}"""
for count in ("N", "m"):
    copied = data("quantum:" + block_column.replace("N", count))["copy_text"]
    assert data("quantum:" + copied)["copy_text"] == copied
    bound = f"replace(replace(replace(({copied}),{count},2),A_0,[1,0;0,0]),A_1,[0,0;0,1])"
    for completion, expected in [("[1,0,0,0;0,0,1,0;0,0,0,1;0,1,0,0]", "1"),
                                 ("[1,0,0,0;0,0,0,1;0,0,1,0;0,1,0,0]", "1"),
                                 ("[0,0,0,0;0,0,1,0;0,0,0,1;0,1,0,0]", "0")]:
        assert data(f"quantum:replace(({bound}),U,{completion})")["copy_text"] == expected
spaced = block_column.replace("{0}", "{ 0 }").replace("{1}", "{1 }")
assert data("quantum:" + spaced)["copy_text"] == data("quantum:" + block_column)["copy_text"]
for last in ("2", "n"):
    braced = block_column.replace("{N-1}", "{" + last + "}")
    bare = braced.replace("{0}", "0").replace("{1}", "1").replace("{" + last + "}", last)
    assert data("quantum:" + braced)["copy_text"] == data("quantum:" + bare)["copy_text"]
for invalid_label in ("A_{2}", "B_{1}"):
    run("quantum:" + block_column.replace("A_{1}", invalid_label), "--json", success=False)

# IBM-012 M042 specifies principal square roots in the first block column.
measurement_column = block_column.replace("A_{0}", r"\sqrt{P_0}").replace(
    "A_{1}", r"\sqrt{P_1}").replace("A_{N-1}", r"\sqrt{P_{m-1}}")
measurement_copy = data("quantum:" + measurement_column)["copy_text"]
assert data("quantum:" + measurement_copy)["copy_text"] == measurement_copy
assert data("quantum:" + measurement_column.replace(r"\sqrt{", r"\sqrt {"))["copy_text"] == measurement_copy
scalar_effects = f"replace(replace(replace(({measurement_copy}),m,2),P_0,matrix(1,1,[9/25])),P_1,matrix(1,1,[16/25]))"
assert data(f"quantum:replace(({scalar_effects}),U,[3,-4;4,3]/5)")["copy_text"] == "1"
assert data(f"quantum:replace(({scalar_effects}),U,[-3,-4;4,3]/5)")["copy_text"] == "0"
effects = f"replace(replace(replace(({measurement_copy}),m,2),P_0,[1/2,-7/50;-7/50,1/2]),P_1,[1/2,7/50;7/50,1/2])"
for candidate, expected in [
    ("[7/10,-1/10,-7/10,-1/10;-1/10,7/10,-1/10,-7/10;7/10,1/10,7/10,-1/10;1/10,7/10,-1/10,7/10]", "1"),
    ("[7/10,-1/10,0,0;-1/10,7/10,0,0;7/10,1/10,0,0;1/10,7/10,0,0]", "1"),
    ("[7/10,-1/10,1,0;-1/10,7/10,0,1;7/10,1/10,0,0;1/10,7/10,0,0]", "1"),
    # Negating the first root leaves its square unchanged.
    ("[-7/10,1/10,0,0;1/10,-7/10,0,0;7/10,1/10,0,0;1/10,7/10,0,0]", "0"),
    ("[1/2,-7/50,0,0;-7/50,1/2,0,0;1/2,7/50,0,0;7/50,1/2,0,0]", "0"),
]:
    assert data(f"quantum:replace(({effects}),U,{candidate})")["copy_text"] == expected
run("quantum:" + measurement_column.replace(r"\sqrt{P_1}", "P_1"), "--json", success=False)

# The double sum in the measurement dilation uses the first index for
# block rows and the second for block columns. Its middle matrix stays free.
measurement_sum = r"\sum_{a,b=0}^{m-1} \vert a\rangle \langle b \vert \otimes \sqrt{P_a} \rho \sqrt{P_b}"
state_equation = r"\sigma = U (\vert 0\rangle \langle 0 \vert \otimes \rho) U^{\dagger} = " + measurement_sum
bell_density = "[1,0,0,1;0,0,0,0;0,0,0,0;1,0,0,1]/2"
assignments = [("P_1", "[0,0;0,1]"), ("m", "2"), ("U", "[1,0,0,0;0,0,1,0;0,0,0,1;0,1,0,0]"),
               ("ρ", "[1,1;1,1]/2"), ("P_0", "[1,0;0,0]")]
copied_state = data("quantum:" + state_equation)["copy_text"]
assert data("quantum:" + copied_state)["copy_text"] == copied_state
for equation, order in [(state_equation, assignments), (copied_state, reversed(assignments))]:
    for label, value in order:
        equation = f'replace(({equation}),"{label}",{value})'
    for value, truth in [(bell_density, "1"), ("[1,0,0,0;0,0,0,0;0,0,0,0;0,0,0,0]", "0")]:
        assert data(f'quantum:replace(({equation}),"σ",{value})')["copy_text"] == truth
# A three-outcome measurement initializes the first of three two-dimensional
# blocks. A unitary permutation carries the first two columns to rows 0 and 3.
for dim, unitary, sigma, effect_values in [
    (1, "[1,0;0,1]", "[1,1;1,1]/2", ["[1,0;0,1]"]),
    (3, "[1,0,0,0,0,0;0,0,0,1,0,0;0,0,1,0,0,0;0,1,0,0,0,0;0,0,0,0,1,0;0,0,0,0,0,1]",
     "[1,0,0,1,0,0;0,0,0,0,0,0;0,0,0,0,0,0;1,0,0,1,0,0;0,0,0,0,0,0;0,0,0,0,0,0]/2",
     ["[1,0;0,0]", "[0,0;0,1]", "[0,0;0,0]"]),
]:
    equation = copied_state
    for index, effect in enumerate(effect_values):
        equation = f'replace(({equation}),"P_{index}",{effect})'
    for label, val in [("m", dim), ("U", unitary), ("ρ", "[1,1;1,1]/2"), ("σ", sigma)]:
        equation = f'replace(({equation}),"{label}",{val})'
    assert data("quantum:" + equation)["copy_text"] == "1"
for fixed in [r"U (\vert 0\rangle_{2}\langle 0\vert_{2}\otimes\rho)",
              r"U ([1;0][1,0]\otimes\rho)"]:
    assert "qinitialdensity" not in data("quantum:" + fixed)["copy_text"]
for projector in ["|0><0|", "(|0><0|)", "|0>*<0|"]:
    applied = data("quantum:U (" + projector + " @ ρ)")["copy_text"]
    assert "qinitialdensity" in applied
    rectangular = f'replace(replace(({applied}),"ρ",[0;1]),"U",[1,0,0,0;0,1,0,0;0,0,1,0;0,0,0,1])'
    assert data("quantum:" + rectangular)["copy_text"] == "matrix(4,2,[0,0,1,0,0,0,0,0])"
# Applying the two diagonal roots to (1,i)/sqrt(2) gives the column
# (3,5i,4,0)/sqrt(50). Its outer product distinguishes the row and column indices.
complex_output = f'replace(replace(replace(replace(({measurement_sum}),"P_0",[9/25,0;0,1]),"P_1",[16/25,0;0,0]),"ρ",[1,-i;i,1]/2),"m",2)'
complex_expected = "[9,-15i,12,0;15i,25,20i,0;12,-20i,16,0;0,0,0,0]/50"
assert data(f"quantum:({complex_output})=({complex_expected})")["copy_text"] == "1"
single_outcome = f'replace(replace(replace(({measurement_sum}),"P_0",[1,0;0,1]),"m",1),"ρ",[0,0;0,1])'
assert data("quantum:" + single_outcome)["copy_text"] == "matrix(2,2,[0,0,0,1])"
for altered in [measurement_sum.replace("P_b", "P_a"), measurement_sum.replace("P_b", "Q_b"),
                measurement_sum.replace(r"\rho", "a"), measurement_sum.replace(r"\langle b", r"\langle a")]:
    assert "qmeasurementblocks" not in data("quantum:" + altered)["copy_text"]

# IBM-012 M062. Only the specified row and column survive the zero padding.
measurement_row = r"""\begin{pmatrix}
\sqrt{P_0} & \sqrt{P_1} & \cdots & \sqrt{P_{m-1}} \\[1mm]
\fbox{?} & \fbox{?} & \cdots & \fbox{?} \\[1mm]
\vdots & \vdots & \ddots & \vdots\\[1mm]
\fbox{?} & \fbox{?} & \cdots & \fbox{?}
\end{pmatrix}"""
corner_density = r"""\begin{pmatrix}
\rho & 0 & \cdots & 0 \\[1mm]
0 & 0 & \cdots & 0 \\[1mm]
\vdots & \vdots & \ddots & \vdots\\[1mm]
0 & 0 & \cdots & 0
\end{pmatrix}"""
expanded_blocks = r"""\begin{pmatrix}
\sqrt{P_0}\rho\sqrt{P_0} & \cdots & \sqrt{P_0}\rho\sqrt{P_{m-1}} \\[1mm]
\vdots & \ddots & \vdots\\[1mm]
\sqrt{P_{m-1}}\rho\sqrt{P_0} & \cdots & \sqrt{P_{m-1}}\rho\sqrt{P_{m-1}}
\end{pmatrix}"""
open_column = measurement_column.removeprefix("U=")
measurement_product = open_column + corner_density + measurement_row
grouped_product = open_column + "(" + corner_density + measurement_row + ")"
assert data("quantum:" + grouped_product)["copy_text"] == data("quantum:" + measurement_product)["copy_text"]
braced_corners = expanded_blocks.replace("P_0", "P_{ 0 }")
assert data("quantum:" + braced_corners)["copy_text"] == data("quantum:" + expanded_blocks)["copy_text"]
block_equation = r"\sigma =" + measurement_product + " = " + expanded_blocks
block_copy = data("quantum:" + block_equation)["copy_text"]
assert data("quantum:" + block_copy)["copy_text"] == block_copy
for expr in (block_equation, block_copy):
    for label, val in [("P_1", "[16/25,0;0,0]"), ("ρ", "[1,-i;i,1]/2"), ("m", "2"), ("P_0", "[9/25,0;0,1]")]:
        expr = f'replace(({expr}),"{label}",{val})'
    for state, truth in [(complex_expected, "1"), (complex_expected.replace("-15i", "15i"), "0")]:
        assert data(f'quantum:replace(({expr}),"σ",{state})')["copy_text"] == truth
row_match = "U=(" + measurement_row + ")"
for label, val in [("m", "2"), ("P_0", "[1,-i;i,1]/2"), ("P_1", "[1,i;-i,1]/2")]:
    row_match = f'replace(({row_match}),"{label}",{val})'
for completion, truth in [("[1,-i,1,i;i,1,-i,1;0,0,0,0;0,0,0,0]/2", "1"),
                          ("[1,i,1,-i;-i,1,i,1;0,0,0,0;0,0,0,0]/2", "0")]:
    assert data(f'quantum:replace(({row_match}),"U",{completion})')["copy_text"] == truth
distinct = open_column + corner_density + measurement_row.replace("P_", "Q_")
for label, val in [("m", "2"), ("ρ", "[1,0;0,0]"), ("P_0", "[1,0;0,0]"), ("P_1", "[0,0;0,1]"),
                   ("Q_0", "[0,0;0,1]"), ("Q_1", "[1,0;0,0]")]:
    distinct = f'replace(({distinct}),"{label}",{val})'
assert data("quantum:" + distinct)["copy_text"] == "matrix(4,4,[0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0])"
for incorrect in [corner_density.replace("0 & 0", "0 & 1"), measurement_row.replace(r"\ddots", r"\cdots"),
                  expanded_blocks.replace("P_{m-1}", "Q_{m-1}", 1)]:
    run("quantum:" + incorrect, "--json", success=False)

# A ket followed by a bra on the right of a tensor forms a matrix unit.
# Its row belongs to the ket and its column to the bra, even for complex states.
for ket_state, bra_state, output in [
    ("|0>", "<1|", "[0,1,0,0;0,0,0,0;0,0,0,0;0,0,0,0]"),
    ("|1>", "<0|", "[0,0,0,0;1,0,0,0;0,0,0,0;0,0,0,0]"),
    ("|+i>", "<+i|", "[1,-i,0,0;i,1,0,0;0,0,0,0;0,0,0,0]/2"),
]:
    tensor_unit = f"|0><0| @ {ket_state}{bra_state}"
    assert data(f"quantum:({tensor_unit})=({output})")["copy_text"] == "1"
    assert data(f"quantum:({tensor_unit})=tensor(|0><0|,({ket_state}{bra_state}))")["copy_text"] == "1"
for unit in ("(|0>)<1|", "|0>(<1|)", "((|0>))((<1|))"):
    assert data(f"quantum:(I @ {unit})=tensor(I,(|0><1|))")["copy_text"] == "1"
assert data("quantum:(I @ (2|0>)<1|)=2*tensor(I,(|0><1|))")["copy_text"] == "1"
assert data("quantum:(I @ (|0>+|1>)<1|)=tensor(I,([1;1]*[0,1]))")["copy_text"] == "1"
named_unit = data("quantum:I @ (2|0>)<ψ|")["copy_text"]
assert data("quantum:" + named_unit)["copy_text"] == named_unit
assigned_unit = f'replace(({named_unit}),qnamedket("ψ"),|1>)'
assert data(f"quantum:({assigned_unit})=2*tensor(I,(|0><1|))")["copy_text"] == "1"
assert data("quantum:(I @ 2|0><1|)=2*tensor(I,(|0><1|))")["copy_text"] == "1"
assert data("quantum:(H @ H |00>)=([1;1;1;1]/2)")["copy_text"] == "1"

diagonal_series = r"A_{0,0}+A_{1,1}+\cdots+A_{n-1,n-1}"
diagonal_copy = data("quantum:" + diagonal_series)["copy_text"]
assert data("quantum:" + diagonal_copy)["copy_text"] == diagonal_copy
for dim in (2, 3, 4):
    entries = "+".join(f'"A_{i},{i}"' for i in range(dim))
    assert data(f"quantum:replace(({diagonal_copy}),n,{dim})=({entries})")["copy_text"] == "1"
assert data(r"quantum:\operatorname{Tr}\begin{pmatrix}1&i\\2&3i\end{pmatrix}=1+3i")["copy_text"] == "1"
assert data(f'quantum:replace(({diagonal_copy}),n,2)=("A_0,0"+"A_1,1"+1)')["copy_text"] == "0"

assert data("quantum:" + diagonal_series.replace("n-1,n-1", "n - 1,n-1"))["copy_text"] == diagonal_copy
assert data(r"quantum:\operatorname{Tr}\begin{pmatrix}1&2\\3&4\end{pmatrix}^2")["copy_text"] == "29"
bound_entry = data(f'quantum:replace(({diagonal_copy}),"A_0,0","A_1,1")')["copy_text"]
assert data("quantum:" + bound_entry)["copy_text"] == bound_entry
assert data(f'quantum:replace(replace(({bound_entry}),"A_1,1",2),n,2)')["copy_text"] == "4"
for malformed in (diagonal_series.replace("1,1", "1,0"), "3-" + diagonal_series):
    run("quantum:" + malformed, "--json", success=False)
for dim in (1, 1025):
    run(f"quantum:replace(({diagonal_copy}),n,{dim})", "--json", success=False)

counted_product = r"\rho \otimes \rho \otimes \cdots \otimes \rho \quad \text{($N$ times)}"
counted_copy = data("quantum:" + counted_product)["copy_text"]
assert data("quantum:" + counted_copy)["copy_text"] == counted_copy
assert data(r"quantum:\rho^{\otimes N}=" + counted_product)["copy_text"] == "1"
for count_name in ("c", "i", "X"):
    annotated = counted_product.replace("$N$", f"${count_name}$")
    assert data(r"quantum:\rho^{\otimes " + count_name + "}=" + annotated)["copy_text"] == "1"
    held = data("quantum:" + annotated)["copy_text"]
    assert data(f'quantum:replace(replace(({held}),"ρ",X),"{count_name}",2)=tensor(X,X)')["copy_text"] == "1"
counted_matrix = f'replace(({counted_copy}),"ρ",[0,1;1,0])'
for count, product in ((1, "X"), (2, "tensor(X,X)"), (3, "tensor(X,tensor(X,X))")):
    assert data(f"quantum:replace(({counted_matrix}),N,{count})=({product})")["copy_text"] == "1"
assert data(f"quantum:replace(({counted_matrix}),N,2)=tensor(X,I)")["copy_text"] == "0"
run("quantum:" + counted_product.replace(r"\cdots \otimes \rho", r"\cdots \otimes X"), "--json", success=False)
run(f"quantum:replace(({counted_matrix}),N,-1)", "--json", success=False)

for angle in (r"\pi=180^{\circ}", r"2\pi=360^\circ", r"\cos(60^{\circ})=1/2",
              r"\frac{1}{30^{\circ}}=6/\pi", r"(40+5)^{\circ}=\pi/4", r"\cos 60^\circ=1/2", r"\sin^{2} -30^{\circ}=1/4"):
    assert data("quantum:" + angle)["copy_text"] == "1"
assert data(r"quantum:\pi=90^{\circ}")["copy_text"] == "0"

matrix_unit = r"\vert 0\rangle\langle 1\vert"
for channel_tex, name in [(r"\Delta", "Δ"), (r"\Lambda", "Λ"), (r"\Phi", "Φ"), (r"\Delta_{3}", "Δ_3"), (r"\Delta_{m}", "Δ_m")]:
    action = data("quantum:" + channel_tex + r"\bigl(" + matrix_unit + r"\bigr)")["copy_text"]
    assert data(f'quantum:replace(({action}),"{name}",vector(X))=[0,0;1,0]')["copy_text"] == "1"
    choi = data(f"quantum:J({channel_tex})")["copy_text"]
    assert data(f'quantum:replace(({choi}),"{name}",vector([1,0]))=[1,0;0,0]')["copy_text"] == "1"

dimensioned = data(r"quantum:\Phi(\vert 2\rangle_{3}\langle 0\vert_{3})")["copy_text"]
assert data(f'quantum:replace(({dimensioned}),"Φ",vector(identity(3)))=[0,0,0;0,0,0;1,0,0]')["copy_text"] == "1"
summed = data(r"quantum:\sum_{a=0}^{1}\Phi_a(\vert a\rangle\langle a\vert)")["copy_text"]
assert data(f'quantum:replace(replace(({summed}),"Φ_0",vector(I)),"Φ_1",vector(X))=[2,0;0,0]')["copy_text"] == "1"
symbolic_unit = data(r"quantum:\Phi(\vert a\rangle\langle b\vert)")["copy_text"]
for assigned in (f'replace(replace(replace(({symbolic_unit}),"a",0),"b",1),"Φ",vector(X))',
                 f'replace(replace(replace(({symbolic_unit}),"Φ",vector(X)),"a",0),"b",1)'):
    assert data(f"quantum:({assigned})=[0,0;1,0]")["copy_text"] == "1"
assert data(r"quantum:J(\Lambda)J(\Delta)")["copy_text"] == data(r"quantum:J(\Lambda) J(\Delta)")["copy_text"]

# Both textbook declarations name c as a column index.
for literal in (r"$c = 0,\ldots,n-1$", r"$c\in\{0,\ldots,n-1\}$"):
    column_index = data("quantum:" + literal)["copy_text"]
    assert data("quantum:" + column_index)["copy_text"] == column_index
    for index, expected in [(-1, "0"), (0, "1"), (2, "1"), (3, "0")]:
        assert data(f'quantum:replace(replace(({column_index}),n,3),"c",{index})')["copy_text"] == expected
assert "299792458" in data("quantum:c")["copy_text"]

for heading in (r"\cdot", "·", "*", "+"):
    table = r"\begin{array}{c|c}" + heading + r" & 0\\\hline 0 & 0\end{array}"
    copied = data("quantum:" + table)["copy_text"]
    label = "+" if heading == "+" else "·"
    assert copied == f"matrix(2,2,['{label}','0',0,0])"
    assert data("quantum:" + copied)["copy_text"] == copied

exponent_domain = data(r"quantum:$k = 2, 4, 8, \ldots, 2^{m-1}$")["copy_text"]
assert data("quantum:" + exponent_domain)["copy_text"] == exponent_domain
for width, exponent, expected in [(1, 2, 0), (2, 2, 1), (4, 3, 0), (4, 8, 1), (4, 16, 0)]:
    bound = f'replace(replace(({exponent_domain}),"m",{width}),"k",{exponent})'
    assert data("quantum:" + bound)["copy_text"] == str(expected)
named_bound = data(r"quantum:$j=2,4,8,\cdots,2^e$")["copy_text"]
assert data(f'quantum:replace(replace(({named_bound}),"e",4),"j",16)')["copy_text"] == "1"
run(r"quantum:$k=2,4,9,\ldots,2^{m-1}$", success=False)
power_list = r"$a^2,a^4,\ldots a^{2^{m-1}}\in\mathbb{Z}_N^{\ast}$"
for formula, base, width, expected in [(power_list, 5, 4, 1), (power_list, 3, 4, 0),
                                       (power_list, 3, 1, 1), (power_list.replace(r"^{\ast}", ""), 3, 4, 1)]:
    copied = data("quantum:" + formula)["copy_text"]
    assert data("quantum:" + copied)["copy_text"] == copied
    bound = f'replace(replace(replace(({copied}),"N",21),"a",{base}),"m",{width})'
    assert data("quantum:" + bound)["copy_text"] == str(expected)
for formula in (power_list, power_list.replace(r"^{\ast}", "")):
    copied = data("quantum:" + formula)["copy_text"]
    empty = f'replace(replace(({copied}),"m",1),"a",2)'
    for invalid in (0, -1):
        result = run(f'quantum:replace(({empty}),"N",{invalid})', success=False)
        assert b"positive exact integer" in result.stderr

for formula, expected in [(r"\log(8)", "3"), (r"\log_{3}(27)", "3"), (r"\ln(1)", "0"),
                          (r"\lfloor\log(7/8)\rfloor", "−1"), (r"\log 2^3", "3"),
                          (r"\log_3 3^4", "4"), (r"(\log 8)^2", "9")]:
    assert data("quantum:binarylogs:"+formula)["copy_text"] == expected
assert data(r"quantum:\lfloor\log(8)\rfloor")["copy_text"] == "2"
assert data(r"quantum:$2^4\equiv1$ $(\textrm{mod } 5)$")["copy_text"] == "1"
assert data(r"quantum:$2^4\equiv1$ $\pmod{7}$")["copy_text"] == "0"
run(r"quantum:$2^4\equiv1$ and $\pmod{5}$",success=False)
for separator in ("\n\n","\r\n  \r\n"):
    run(r"quantum:$2^4\equiv1$"+separator+r"$\pmod{5}$",success=False)
split_copy = data(r"quantum:$a^r\equiv1$"+ "\r\n" +r"$\pmod{N}$")["copy_text"]
assert data("quantum:"+split_copy)["copy_text"] == split_copy
run("quantum:qstepvalue(y ← 3,qbinarylog(vector(x,2)))", success=False)
assert data("quantum:qstepvalue(y ← 3,qbinarylog(x))")["copy_text"] == "3"

residue_action = r"M_a\vert x\rangle=\vert ax\rangle\quad\text{(for each $x\in\mathbb{Z}_N$)}"
residue_copy = data("quantum:"+residue_action)["copy_text"]
assert data("quantum:"+residue_copy)["copy_text"] == residue_copy
for a,n in ((2,3),(2,5),(4,15)):
    matrix = data(f'quantum:replace(replace(({residue_copy}),"N",{n}),"a",{a})')["copy_text"]
    cells = [str(int(target==a*source%n)) for target in range(n) for source in range(n)]
    assert matrix == f"matrix({n},{n},["+",".join(cells)+"])"
run("quantum:qresiduemultiplier(3,15)",success=False)
run("quantum:qresiduemultiplier(a,65)",success=False)
run("quantum:qresiduemultiplier(a,a)",success=False)
uniform_orbit = r"\vert\psi_0\rangle=\frac{|1\rangle+|a\rangle+\cdots+|a^{r-1}\rangle}{\sqrt{r}}"
orbit_copy = data("quantum:modpowers:"+uniform_orbit)["copy_text"]
assert orbit_copy == "qorbitket('a','N','r',0)"
assert data("quantum:norm(qorbitket(2,15,4,1)-(basis(1,15)-i*basis(2,15)-basis(4,15)+i*basis(8,15))/2)")["copy_text"] == "0"
run("quantum:qorbitket(2,15,8,0)",success=False)
run("quantum:qorbitket(3,15,r,0)",success=False)
for impossible in ("a,a,r,1","a,N,r,r","a,5,r,4","2,15,r,4","1,N,2,0","a,15,7,0"):
    run("quantum:qorbitket("+impossible+")",success=False)
assert data("quantum:qorbitket(2,15,r,3)")["copy_text"] == "qorbitket(2,15,'r',3)"
definition = r"f_a(x)=\begin{cases}ax\;(\textrm{mod}\;N)&0\leq x<N\\x&N\leq x<2^n\end{cases}"
graph = data("quantum:"+definition)["copy_text"]
assert graph == "qregistermultipliergraph('a','N','n')"
for x, expected in ((0,0),(2,4),(3,0),(6,6),(15,15)):
    probe = data(f"quantum:qfiniteapply({graph},{x})")["copy_text"]
    assert data(f'quantum:replace(replace(replace(({probe}),"n",4),"a",2),"N",6)')["copy_text"] == str(expected)
run("quantum:qregistermultiplier(2,6,n)",success=False)
run("quantum:qregistermultipliergraph(a,9,3)",success=False)
run("quantum:qregistermultipliergraph(4,N,2)",success=False)
run("quantum:qregistermultiplier(62,N,2)",success=False)
for op,image in (("qregisterxoraction",2),("qregisterinversexoraction",3)):
    actual=data(f"quantum:{op}(qregistermultipliergraph(2,5,3),1,4)")["copy_text"]
    expected=data(f"quantum:qstateaction(qbasis(12,64),qbasis({8+(4^image)},64))")["copy_text"]
    assert actual==expected and data("quantum:"+actual)["copy_text"]==expected
run("quantum:qregisterinversexoraction(qregistermultipliergraph(2,6,3),0,0)",success=False)
run("quantum:qregisterxoraction(qregistermultipliergraph(a,N,2),4,y)",success=False)
for op in ("qregisterinversexoraction","qregisteruncompute"):
    labels = "x,y" if op.endswith("action") else "x"
    for graph in ("2,6,n","0,N,n"):
        run(f"quantum:{op}(qregistermultipliergraph({graph}),{labels})",success=False)
for width in (3,5,6):
    dim=1<<width
    labels=(3*dim,3*dim+1,dim+3,dim)
    edges=[f"qstateaction(qbasis({u},{dim*dim}),qbasis({v},{dim*dim}))" for u,v in zip(labels,labels[1:])]
    trace=data(f"quantum:qregisteruncompute(qregistermultipliergraph(2,5,{width}),3)")["copy_text"]
    assert trace==data("quantum:vector("+",".join(edges)+",1)")["copy_text"]
    assert trace==data("quantum:"+trace)["copy_text"]

encoding_table = r"\begin{gathered}0\mapsto 000\\1\mapsto 001\\\vdots\\5\mapsto 101\end{gathered}"
encoding_copy = data("quantum:"+encoding_table)["copy_text"]
encoding_pairs = [f"qtuple(vector({j},qbitlabel({j},3)))" for j in range(6)]
assert encoding_copy == "qset(vector("+",".join(encoding_pairs)+"))"
assert data("quantum:"+encoding_copy)["copy_text"] == encoding_copy
large_graph = encoding_table.replace("000", "0000000000").replace("001\\","0000000001\\").replace("5\\mapsto 101","1023\\mapsto 1111111111")
large_copy = data("quantum:"+large_graph)["copy_text"]
assert large_copy == "qsetimage(qtuple(vector(j,qbitlabel(j,10))),qindexrange(0,1023),j)"
assert data("quantum:"+large_copy)["copy_text"] == large_copy
for inconsistent in (encoding_table.replace("101","100"), encoding_table.replace("001","01"),
                     encoding_table.replace("1\\mapsto","2\\mapsto")):
    run("quantum:"+inconsistent, success=False)

action_table = r"\begin{array}{cc}M_2|2\rangle=|0\rangle&M_2|0\rangle=|1\rangle\\M_2|3\rangle=|3\rangle&M_2|1\rangle=|2\rangle\end{array}"
action_matrix = data("quantum:"+action_table)["copy_text"]
assert action_matrix == "matrix(4,4,[0,0,1,0,1,0,0,0,0,1,0,0,0,0,0,1])"
assert data("quantum:"+action_matrix)["copy_text"] == action_matrix
run(r"quantum:\begin{array}{c}X|0\rangle=|0\rangle\\X|1\rangle=|1\rangle\end{array}", success=False)
run("quantum:"+action_table.replace(r"M_2|2\rangle", r"M_2|1\rangle"), success=False)
run("quantum:"+action_table.replace(r"=|3\rangle", r"=|4\rangle"), success=False)

printed_pair = data(r"quantum:$$a^{r/2}-1\;(\textrm{mod}\; N)\quad\text{and}\quad a^{r/2}+1\;(\textrm{mod}\; N).$$")["copy_text"]
order_grid = r"\begin{array}{cc}8^{2}=1&2^{6}=1\\[1mm]5^6=1&20^2=1\end{array}"
order_copy = data("quantum:modpowers:"+order_grid)["copy_text"]
assert data("quantum:modpowers:"+order_copy)["copy_text"] == order_copy
for modulus in (2, 7, 11, 21, 22):
    results = [str(int(pow(a, r, modulus) == 1 % modulus)) for a,r in ((8,2),(2,6),(5,6),(20,2))]
    assert data(f'quantum:replace(({order_copy}),"modulus",{modulus})')["copy_text"] == "matrix(2,2,["+",".join(results)+"])"
run(f'quantum:replace(({order_copy}),"modulus",0)', success=False)
run("quantum:"+order_grid, success=False)
identity_grid = r"\begin{array}{cc}2^2=4&5^2=25\\2^1=2&3^1=3\end{array}"
identity_copy = data("quantum:modpowers:"+identity_grid)["copy_text"]
assert data(f'quantum:replace(({identity_copy}),"modulus",7)')["copy_text"] == "matrix(2,2,[1,1,1,1])"
run(f'quantum:replace(({identity_copy}),"modulus",0)', success=False)
assert data("quantum:"+printed_pair)["copy_text"] == printed_pair
for base, expected in [(14,"vector(13,0)"), (0,"vector(14,1)")]:
    bound = f'replace(replace(replace(({printed_pair}),"r",2),"a",{base}),"N",15)'
    assert data("quantum:"+bound)["copy_text"] == expected
assert data(r"quantum:$2^4\;(\textrm{mod}\;15)=1$")["copy_text"] == "1"
assert data(r"quantum:$2^4\;(\mathrm{mod}\;15)=16$")["copy_text"] == "0"
for postfix in (r"$2=7(\mathrm{mod}\;5)$", r"$(7(\textrm{mod}\;5))=2$",
                r"7(\mathrm{mod}\;5)=2 or 1", r"$2+5(\mathrm{mod}\;5)=2$"):
    assert data("quantum:"+postfix)["copy_text"] == "1"

for equation, modulus, expected in [(r"5^2=1", "6", 1), (r"5^2=1", "7", 0),
                                    (r"3+5=1", "7", 1), (r"2^8=4^4", "{21}", 1)]:
    annotated = equation + r"\quad\text{(working within $\mathbb{Z}_" + modulus + "$)}"
    assert data("quantum:" + annotated)["copy_text"] == str(expected)
run(r"quantum:5^2=1=7\quad\text{(working within $\mathbb{Z}_6$)}", success=False)
for equation, modulus in [(r"(1=7)", "6"), (r"2^{-1}=4", "7"), (r"1/5=5", "6"),
                          (r"2^{2^3}=4", "6")]:
    assert data("quantum:"+equation+r"\quad\text{(working within $\mathbb{Z}_"+modulus+"$)}")["copy_text"] == "1"
for equation in ("1/2=1/2", "0/2=0", "1 or 7=0", "7=0 or 1"):
    run("quantum:"+equation+r"\quad\text{(working within $\mathbb{Z}_6$)}", success=False)

modular = data(r"quantum:modpowers:$b = a^k \in \mathbb{Z}_N^{\ast}$")["copy_text"]
assert data("quantum:"+modular)["copy_text"] == modular
for candidate, expected in [(4,1), (25,0)]:
    expr = f'replace(replace(replace(replace(({modular}),"k",2),"a",5),"N",21),"b",{candidate})'
    assert data("quantum:"+expr)["copy_text"] == str(expected)
assert data(r"quantum:modpowers:$17 = 5^{-1}\in\mathbb{Z}_{21}$")["copy_text"] == "1"
for formula in (r"$(2+3)^2\in\mathbb{Z}_{21}$", r"$4=5^{1+1}\in\mathbb{Z}_{7*3}$",
                r"$4=4=5^{2+0}\in\mathbb{Z}_{21}^{\ast}$", r"$5^2,5^4\in\mathbb{Z}_{21}^{\ast}$"):
    assert data("quantum:modpowers:"+formula)["copy_text"] == "1"
assert data(r"quantum:$5^2\in\mathbb{Z}_{21}$")["copy_text"] == "0"
assert data("quantum:qmodpower(2,1000000000,21)")["copy_text"] == str(pow(2,1000000000,21))
for source, modulus, expected in ((r"$3 \cdot 5 = 1$",7,"1"),(r"$3 \cdot 5 = 1$",6,"0"),
                                  ("$ab=1$",21,"1"),("$a^{-1}$",21,"17")):
    form=data("quantum:modpowers:"+source)["copy_text"]
    assert data("quantum:"+form)["copy_text"]==form
    bound=f'replace(replace(replace(({form}),"a",5),"b",17),"modulus",{modulus})'
    assert data("quantum:"+bound)["copy_text"]==expected
assert data(r"quantum:$3 \cdot 5 = 1$")["copy_text"]=="0"
for source in ("(3*5)=1","3*(5)=1","(3*5=1)",r"1=3\times 5","3·5=(1)"):
    form=data("quantum:modpowers:"+source)["copy_text"]
    assert data(f'quantum:replace(({form}),"modulus",7)')["copy_text"]=="1"
for source in ("5^-1","(5)^(-1)",r"(5^{-1})"):
    form=data("quantum:modpowers:"+source)["copy_text"]
    assert data(f'quantum:replace(({form}),"modulus",7)')["copy_text"]=="3"
for source in ("pi=1","π=1",r"\pi=1"):
    assert data("quantum:modpowers:"+source)["copy_text"]=="0"
for source,expected in (("5⁻¹","3"),("(2+3)^{-1}","3"),("3*5=8","1"),("2+3*5=3","1"),
                        ("(a)b=1","1"),("a(b)=1","1"),("(a)(b)=1","1"),("3(5)=1","1")):
    form=data("quantum:modpowers:"+source)["copy_text"]
    bound=f'replace(replace(replace(({form}),"modulus",7),"a",3),"b",5)'
    assert data("quantum:"+bound)["copy_text"]==expected
for invalid in ("qmodpower(2,-1,4)", "qmodpower(1,2,0)", "qmodpower(1/2,2,7)"):
    run("quantum:"+invalid, success=False)

# Preserve the product inside the reciprocal in the phase-recovery bound.
fraction_bound = r"$\left\vert\frac{y}{2^m}-\frac{1}{r}\right\vert<\frac{1}{2r(r+1)}$"
copied = data("quantum:"+fraction_bound)["copy_text"]
assert data("quantum:"+copied)["copy_text"] == copied
for numerator, expected in [(4, "1"), (5, "0")]:
    expr = f'replace(replace(replace(({copied}),"m",3),"r",2),y,{numerator})'
    assert data("quantum:"+expr)["copy_text"] == expected

# Copying a deferred ordered product preserves its factors and matrix entries.
for expression in (r"$X|\psi(t_0)\rangle$", r"$e^{-i\epsilon Z_j Z_{j+1}}$"):
    copied = data("quantum:"+expression)["copy_text"]
    assert data("quantum:"+copied)["copy_text"] == copied

# Bind the frequency after copying. A half turn gives distinct eigenphases.
for generator, expected in (("", "-i"), ("Z", "(-i)*Z"), ("X", "(-i)*X"), ("Y", "(-i)*Y")):
    phase = data(r"quantum:$e^{-i"+generator+r"\omega_B t/2}$")["copy_text"]
    phase = phase.replace('"ω_B"', "2").replace("'t'", "(pi/2)")
    assert data(f"quantum:qcompare(({phase}),({expected}),4)")["copy_text"] == "1"

mapping = data(r"quantum:$|a\rangle|0\rangle \mapsto |a\rangle|a\rangle$")["copy_text"]
assert data("quantum:"+mapping)["copy_text"] == mapping
parameters = data("quantum:$[[n,n-2,2]]$")["copy_text"]
assert parameters.startswith("vector(") and data("quantum:"+parameters)["copy_text"] == parameters

fidelity = data(r"quantum:$$F(p,q)=(\sum_i \sqrt{p_i\,q_i})^2$$")["copy_text"]
assert data("quantum:"+fidelity)["copy_text"] == fidelity
# For p=(1,0) and q=(1/4,3/4) the squared classical fidelity is 1/4.
for value, truth in (("1/4", "1"), ("1/2", "0")):
    graph = f"qset(vector(qtuple(vector(qtuple(vector(7,8)),{value}))))"
    relation = fidelity.replace("'F'",graph).replace("'p'","7").replace("'q'","8")
    relation = relation.replace('"indexset_i"', "qset(vector(0,1))")
    concrete = data("quantum:"+relation)["copy_text"]
    for label, weight in (("p_0","1"), ("p_1","0"), ("q_0","1/4"), ("q_1","3/4")):
        concrete = concrete.replace('"'+label+'"',"("+weight+")")
    assert data("quantum:"+concrete)["copy_text"] == truth

for observable,state,expected in (("Z","|0>","1"),("X","|0>","0"),("Y","|1>","0"),
                                  ("Z","matrix(2,2,[1/4,0,0,3/4])","-1/2")):
    average = data(r"quantum:$\langle "+observable+r"\rangle_\text{ideal}$")["copy_text"]
    assert data("quantum:"+average)["copy_text"] == average
    bound = average.replace('qoperatorref("ideal state")', state)
    assert data(f"quantum:qcompare({bound},{expected},4)")["copy_text"] == "1"

# The physical constant retains its units through Copy and cancels in Ht/hbar.
propagator = data(r"quantum:$e^{-iHt/\hbar}$")["copy_text"]
assert data("quantum:"+propagator)["copy_text"] == propagator
for gate in ("X","Z"):
    bound = propagator.replace("'H'",gate).replace("'t'","(hbar*pi/2)")
    assert data(f"quantum:qcompare({bound},(-i)*{gate},4)")["copy_text"] == "1"
assert data(r"quantum:$\mu s$")["copy_text"] == data('quantum:qphysicalunit("s","")/1000000')["copy_text"]

# Logical complements used as equation operands survive Copy and re-entry.
for spelling in (r"$g(x)=\neg f(x)$","g(x)=!f(x)"):
    predicate = data("quantum:"+spelling)["copy_text"]
    copied = data("quantum:"+predicate)["copy_text"]
    for f in (0,1):
        for g in (0,1):
            bound = f"replace(replace(({copied}),f(x),{f}),g(x),{g})"
            assert data("quantum:"+bound)["copy_text"] == str(int(g == 1-f))
assert data("quantum:not 1=2")["copy_text"] == "1"
assert data("quantum:1!=2")["copy_text"] == "1"

# A bare gate letter in an integer range can be bound after Copy.
held_range = data(r"quantum:$\{1,\ldots,T\}$")["copy_text"]
assert data("quantum:"+held_range)["copy_text"] == held_range
for endpoint, expected in [(3,"qset(vector(1,2,3))"),(1,"qset(vector(1))"),(0,"qset(vector())")]:
    assert data(f'quantum:replace({held_range},"T",{endpoint})')["copy_text"] == expected
assert data('quantum:replace(indexrange(X,2),"X",1)')["copy_text"] == "qset(vector(1,2))"
assert data("quantum:T")["rows"] == 2

# Cardinalities are scalar matrix entries even before the set is supplied.
bars_matrix = data(r"quantum:$\begin{pmatrix}\vert A_0\vert & 1 \\ 0 & 1\end{pmatrix}$")
assert (bars_matrix["rows"], bars_matrix["columns"]) == (2,2)
assert data(f'quantum:replace(({bars_matrix["copy_text"]}),qbars("A_0"),3)')["cells"] == data("quantum:[3,1;0,1]")["cells"]

# Two-argument probability calls keep ordered scalar inputs through Copy.
prob = data("quantum:p(N,s)")
assert prob["display_text"] == "p(N, s)" and not prob["cells"]
assert data("quantum:"+prob["copy_text"])["copy_text"] == prob["copy_text"]
assert data("quantum:p(1+1,4)=p(2,4)")["copy_text"] == "1"
assert data("quantum:p(2,1)")["copy_text"] != data("quantum:p(1,2)")["copy_text"]
bound = data(r"quantum:$p(N,s) \geq 1 - \frac{s}{N}$")["copy_text"]
for probability, expected in [("3/4", "1"), ("2/3", "0")]:
    predicate = f"replace(replace(replace(({bound}),p(N,s),{probability}),N,16),s,4)"
    assert data("quantum:"+predicate)["copy_text"] == expected
assert "qcostcall(" in data("quantum:cost(p(N,s))")["copy_text"]
assert data("quantum:p(x)")["copy_text"] == data("quantum:p*x")["copy_text"]

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

# A brace-delimited basis is a set in its stated dimension.
basis_source = r"$\{\vert 0\rangle,\ldots,\vert N-1\rangle\}$"
basis_copy = data("quantum:"+basis_source)["copy_text"]
for dimension in (1, 3, 15, 128):
    concrete = data(f'quantum:replace(({basis_copy}),"N",{dimension})')["copy_text"]
    assert len(concrete) < 32768
    assert data(f"quantum:cardinality({concrete})")["copy_text"] == str(dimension)
    assert data(f"quantum:basis(0,{dimension}) ∈ {concrete}")["copy_text"] == "1"
assert data("quantum:basis(0,16) ∈ basisset(15)")["copy_text"] == "0"
assert data("quantum:qset(vector(basis(1,3),basis(0,3)))")["copy_text"] != "basisset(2)"

# Re-entering the displayed bound must keep c bindable.
display_bound = data(r"quantum:$b,c\geq 2$")["display_text"]
for y, expected in [(1,"0"),(2,"1")]:
    assert data(f'quantum:replace(replace(({display_bound}),"b",2),"c",{y})')["copy_text"] == expected

# A leading list shares the ordering relation and keeps factor names bindable.
for expr, expected in [(r"$b,c\geq 2$", (1,0,0)), (r"$s,j\geq 2$", (1,0,0))]:
    first,second=expr[1],expr[3]
    result=data("quantum:"+expr)["copy_text"]
    for (x,y),value in zip(((2,3),(1,3),(2,1)),expected):
        assert data(f'quantum:replace(replace(({result}),"{first}",{x}),"{second}",{y})')["copy_text"]==str(value)
for bound in ("-2","N"):
    shared=data("quantum:b,c>="+bound)["copy_text"]
    predicate=f'replace(replace(({shared}),"b",3),"c",-3)'
    if bound=="N":
        predicate=f'replace(({predicate}),"N",2)'
    assert data("quantum:"+predicate)["copy_text"]=="0"
for expr,value in (("1,2,3<4",1),("1,2,3<3",0),("1,2<=2",1),("3,2>2",0),("max(1,2)",2)):
    assert data("quantum:"+expr)["copy_text"]==str(value)

# Compare the two full operands in the specified residue class.
for formula, expected in (
    (r"$3 \cdot 5 \equiv 1 \; (\textrm{mod } 7)$", "1"),
    (r"$3+5\equiv5-4\pmod{7}$", "1"),
    (r"$-2\equiv5\;(\mathrm{mod}\;7)$", "1"),
    (r"$-2\equiv4\pmod{7}$", "0"),
    (r"$(3\equiv1\pmod{2})+(4\equiv1\pmod{2})$", "1"),
):
    assert data("quantum:"+formula)["copy_text"] == expected
for formula in (r"$3\equiv1$", r"$3\equiv1\pmod{}$", r"$3\equiv1\pmod{0}$"):
    run("quantum:"+formula, "--json", success=False)

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
    ("1/3≈((0.33))", "1"), ("1/3≈(0.330)", "0"), ("(1+i)/3≈(0.33+0.33i)", "1"),
    ("qestimatewithin(1≈(3/2),1/2)", "1"), ("qestimatewithin(1≈(3/2),49/100)", "0"),
    ("qestimatewithin(1=2≈(2/1),10)", "0"), ("qestimatewithin(2=2≈(2/1),0)", "1"),
    (r"qstepvalue(T \leftarrow \lceil \frac{5}{4}T\rceil,8)", "10"),
    ("qstepvalue(T ← T(T+1),3)", "12"), ("qstepvalue(x ← 3,9)", "3"),
    ("1=±1=O(n)", "1"), ("1=±1=O(0)", "0"),
    ("1=±1=±1", "1"), ("-1=±1=±1", "1"), ("1=±1=±(-1)", "0"),
    ("-1=±2+1=±2+1", "1"), ("3=1±2=1±2", "1"),
    ("|0> = ± |0>", "1"), ("-|0> = ± |0>", "1"), ("|1> = ± |0>", "0"),
    ("N^(1/3)=O(sqrt(N))", "1"), ("N^(2/3)=O(sqrt(N))", "0"),
    ("sqrt(N*m)=O(N+m)", "1"), ("sqrt(N)=O(sqrt(n))", "0"),
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
for delimiters in ("$","$$"):
    formula=delimiters+"m = O(n)"+delimiters
    for width,expected in (("2*n+1","1"),("n^2","0")):
        assert data(f'quantum:replace(({formula}),"m",{width})')["copy_text"]==expected
run('quantum:replace(($m = O(n)),"m",2*n+1)',success=False)
decimal_range=data(r"quantum:$0, 1, \ldots, 1023$")["copy_text"]
assert decimal_range=="vector("+",".join(map(str,range(1024)))+")"
assert data("quantum:"+decimal_range)["copy_text"]==decimal_range
signed_entries=[str(i if i%2 else -i) for i in range(640)]
signed_copy=data("quantum:vector("+", ".join(signed_entries)+")")["copy_text"]
assert data("quantum:"+signed_copy)["copy_text"]==signed_copy
run(r"quantum:$0, 1, \ldots, 1024$",success=False)
quantified = r"$z\cdot x = 0$ for every string $x\in\Sigma^n$"
copied = data("quantum:"+quantified)["copy_text"]
assert copied=="qallbitdot('z','n',0)" and data("quantum:"+copied)["copy_text"]==copied
for word,truth in ((0,"1"),(3,"0")):
    assert data(f'quantum:replace(replace(({copied}),"n",4),"z",qbitlabel({word},4))')["copy_text"]==truth
run("quantum:qallbitdot(qbitlabel(0,3),4,0)",success=False)
run("quantum:qallbitdot(qbitlabel(31,m),4,0)",success=False)
assert data("quantum:qallbitdot(0,0,1)")["copy_text"]=="0"
assert data('quantum:1+replace (($m=O(n)$),"m",2*n+1)')["copy_text"]=="2"
assert data('quantum:vector(replace(($m=O(n)$),"m",2*n+1),replace(($m=O(n)$),"m",n^2))')["copy_text"]=="vector(1,0)"
assert data('quantum:replace(replace(($m=O(n)$),"m",n^2),"z",3)')["copy_text"]=="0"
assert data('quantum:replace(($$'+residue_action+'$$),"N",5)')["copy_text"]=="qresiduemultiplier('a',5)"
caption=r"$a^r \equiv 1$ $(\textrm{mod } N)$"
for source in (caption,data("quantum:"+caption)["copy_text"]):
    bound=data('quantum:replace(('+source+'),"N",5)')["copy_text"]
    for power,expected in ((2,"0"),(4,"1")):
        assert data(f'quantum:replace(replace(({bound}),"a",2),"r",{power})')["copy_text"]==expected
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
for expression, expected in [
    (r"\frac{1}{2} |0><0| + \frac{1}{2} |1><1|", "matrix(2,2,[1 ∕ 2,0,0,1 ∕ 2])"),
    ("|0><0| - (1/2) |+><+|", "matrix(2,2,[3 ∕ 4,−1 ∕ 4,−1 ∕ 4,−1 ∕ 4])"),
    ("|0>_2<0|_2 + (1/2)|1>_2<1|_2", "matrix(2,2,[1,0,0,1 ∕ 2])"),
    ("(|0>)<0| + (1/2)|1><1|", "matrix(2,2,[1,0,0,1 ∕ 2])"),
    ("|0>*<0| + (1/2)|1><1|", "matrix(2,2,[1,0,0,1 ∕ 2])"),
    ("|0><0| + (1/2)|1>(<1|)", "matrix(2,2,[1,0,0,1 ∕ 2])"),
    ("|1><0|-Z|0>", "matrix(2,1,[0,−1])"),
    ("<0|-Z|0>", "−1"),
]:
    assert data("quantum:" + expression)["copy_text"] == expected

# The missing operand can receive either ordering of the same labelled axes.
pending_trace = data(r"quantum:\operatorname{Tr}_{\mathsf{B}}(\rho)")["copy_text"]
assert data("quantum:" + pending_trace)["copy_text"] == pending_trace
diagonal = "[1,0,0,0;0,2,0,0;0,0,3,0;0,0,0,4]"
# A grouped textbook register matches a declared whole name first. Otherwise
# the mapped axes provide the individual letters, in any physical order.
group_trace = data(r"quantum:\operatorname{Tr}_{\mathsf{AB}}(ρ)")["copy_text"]
assert data("quantum:" + group_trace)["copy_text"] == group_trace
assert data(r"quantum:\operatorname{Tr}_\mathsf{AB}(ρ)")["copy_text"] == group_trace
assert data(f"quantum:replace(replace({group_trace},AB,0),ρ,{diagonal})")["copy_text"] == "matrix(2,2,[4,0,0,6])"
for word in ("BA", "AA", "ABA", "ABC"):
    source = rf"\operatorname{{Tr}}_{{\mathsf{{{word}}}}}(ρ)"
    saved = data("quantum:" + source)["copy_text"]
    assert data("quantum:" + saved)["copy_text"] == saved
    for expression in (source, saved):
        assert data(f"quantum:replace(replace(({expression}),{word},0),ρ,{diagonal})")["copy_text"] == "matrix(2,2,[4,0,0,6])"
for axes, dimensions, expected in [("[A,B]", "[2,2]", "10"), ("[AB,C]", "[2,2]", "matrix(2,2,[4,0,0,6])"),
                                    ("[B,AB,A]", "[2,1,2]", "matrix(4,4,[1,0,0,0,0,2,0,0,0,0,3,0,0,0,0,4])")]:
    mapping = f"subsystems({diagonal},{axes},{dimensions})"
    assert data(f"quantum:replace({group_trace},ρ,{mapping})")["copy_text"] == expected
assert data(r"quantum:\operatorname{Tr}_{ \mathsf {AB} }(ρ)")["copy_text"] == group_trace
numeric_trace = rf"\operatorname{{Tr}}_{{\mathsf{{AB}}}}({diagonal})"
assert data(f"quantum:replace(replace({numeric_trace},A,1),B,1)")["copy_text"] == "matrix(2,2,[3,0,0,7])"
assert b"Unknown subsystem label" in run(
    f"quantum:replace({group_trace},ρ,subsystems({diagonal},[A,C],[2,2]))","--json",success=False).stderr
for labels, expected in [("[A,B]", "[3,0,0,7]"), ("[B,A]", "[4,0,0,6]")]:
    mapped = f"subsystems({diagonal},{labels},[2,2])"
    expression = f"quantum:replace(({pending_trace}),ρ,{mapped})"
    assert data(expression)["copy_text"] == f"matrix(2,2,{expected})"
# The density matrix between grouped factors must remain a free matrix.
for product, expected in [(r"(X)\rho(Z)", "[3,−4,1,−2]"), (r"(Z)\rho(X)", "[2,1,−4,−3]")]:
    saved = data("quantum:" + product)["copy_text"]
    assert data(f"quantum:replace({saved},ρ,[1,2;3,4])")["copy_text"] == f"matrix(2,2,{expected})"
mapped_ab = f"subsystems({diagonal},[A,B],[2,2])"
colliding = data("quantum:ptrace(B,[B])")["copy_text"]
assert data(f"quantum:replace({colliding},B,{mapped_ab})")["copy_text"] == "matrix(2,2,[3,0,0,7])"
bound_selector = data(f"quantum:replace({pending_trace},B,0)")["copy_text"]
for state, expected in [(mapped_ab, "[3,0,0,7]"), (diagonal, "[4,0,0,6]")]:
    assert data(f"quantum:replace({bound_selector},ρ,{state})")["copy_text"] == f"matrix(2,2,{expected})"
assert b"Duplicate traced subsystem" in run("quantum:ptrace(ρ,[A,A])", "--json", success=False).stderr
assert b"explicit subsystems" in run(
    f"quantum:replace(({pending_trace}),ρ,{diagonal})", "--json", success=False).stderr
assert b"Unknown subsystem label" in run(
    f"quantum:replace(({pending_trace}),ρ,subsystems({diagonal},[A,C],[2,2]))",
    "--json", success=False).stderr

alphabet_power = data(r"quantum:$\Sigma^m$")["copy_text"]
for width in (0, 1, 3, -1):
    words = ",".join(f"qbitlabel({n},{width})" for n in range(2 ** max(width, 0)))
    alphabet = ("Σ", r"\{0,1\}")
    size = ("m", str(width))
    for first, last in [(alphabet, size), (size, alphabet)]:
        value = data(f"quantum:replace(({alphabet_power}),{first[0]},{first[1]})")["copy_text"]
        expression = f"quantum:replace(({value}),{last[0]},{last[1]})"
        if width < 0:
            assert b"nonnegative" in run(expression, "--json", success=False).stderr
        else:
            assert data(expression)["copy_text"] == f"qset(vector({words}))"
    pending = data(f"quantum:replace(({alphabet_power}),m,{width})")["copy_text"]
    assert data(f"quantum:replace(({pending}),Σ,2)=2^({width})")["copy_text"] == "1"
assert data(r"quantum:\{2,3\}^2")["copy_text"] == (
    "qset(vector(qtuple(vector(2,2)),qtuple(vector(2,3)),qtuple(vector(3,2)),qtuple(vector(3,3))))")
run(r"quantum:\{0,1\}^{-1}", "--json", success=False)
# IBM-018 uses the output of a function as the membership probe. The
# graph and its input can be supplied independently after Copy and re-entry.
query_membership = data(r"quantum:$f(x)\in\Sigma^m$")["copy_text"]
assert data("quantum:" + query_membership)["copy_text"] == query_membership
for width, expected in [(3, "1"), (2, "0")]:
    arguments = [("f", word_graph), ("x", "bitstring(1,2)"),
                 ("Σ", r"\{0,1\}"), ("m", str(width))]
    for bindings in (arguments, reversed(arguments)):
        value = query_membership
        for symbol, replacement in bindings:
            value = data(f"quantum:replace(({value}),{symbol},{replacement})")["copy_text"]
        assert value == expected, (width, value)
for first, second in [(("f", word_graph), ("x", "bitstring(y,2)")),
                      (("x", "bitstring(y,2)"), ("f", word_graph))]:
    value = "member(f(x),bitstrings(3))"
    for symbol, replacement in (first, second, ("y", "1")):
        value = data(f"quantum:replace(({value}),{symbol},{replacement})")["copy_text"]
    assert value == "1", value
for invalid_graph in ("42", "[1,2]", "qset(vector(1,2))"):
    run(f"quantum:qmember(qgraphapply({invalid_graph},x),vector(1,2))", "--json", success=False)
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
one_based = r"$$\begin{pmatrix}a_{11}&\cdots&a_{1k}\\\vdots&\ddots&\vdots\\a_{m1}&\cdots&a_{mk}\end{pmatrix}$$"
one_based_copy = data("quantum:"+one_based)["copy_text"]
for spelling in [one_based,one_based.replace("_{11}","_{1, 1}")]:
    assert data("quantum:"+spelling)["copy_text"]==one_based_copy
for key,value in [("a_1,3","i"),("m","1"),("k","3"),("a_1,2","7"),("a_1,1","5")]:
    one_based_copy=f'replace(({one_based_copy}),"{key}",{value})'
assert data("quantum:"+one_based_copy)["copy_text"]=="vector(5,7,i)"
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

for parameter, symbol in [(r"\alpha", '"α"'), ("x", "x"), ("i", '"i"')]:
    for subscript in ["_" + parameter, "_{" + parameter + "}"]:
        equation = (r"$$\vert \psi" + subscript + r"\rangle=\cos(" + parameter +
                    r")|0>+\sin(" + parameter + r")|1>\quad\text{(for $" + parameter + r" \in [0,\pi)$)}$$")
        copied = data("quantum:" + equation)["copy_text"]
        for family, truth in [("cos(t)|0>+sin(t)|1>", "1"), ("|1>", "0")]:
            request = state_request([("ψ(t)", family)], f"quantum:replace(({copied}),{symbol},0)")
            assert data(request, "--states")["copy_text"] == truth

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
for function, expected in [("qasin", ("0", "1", "1", "1")), ("qacos", ("1", "1", "1", "0")),
                           ("qatan", ("1", "1", "0", "0"))]:
    copied = data(f"quantum:{function}('x')>='x'")["copy_text"]
    assert data("quantum:"+copied)["copy_text"] == copied
    for value, truth in zip(("-1/2", "0", "1/2", "1"), expected):
        assert data(f"quantum:replace(({copied}),'x',{value})")["copy_text"] == truth
for estimate in ("|u>≈|u>", "1≈qtuple(vector(1,2))"):
    run(f"quantum:qestimatewithin({estimate},0)", "--json", success=False)
for formula, expected in [
    ("$c$", "'c'"), ("$T$", "'T'"), ("$Z^2-1=(Z+1)(Z-1)$", "1"),
    ("replace(bc^2,vector('b','c'),vector(2,3))", "18"),
    ("replace(bc(b+1),vector('b','c'),vector(2,3))", "18"),
    ("sqrt(9)+cos(0)", "4"),
    ("πb==bπ", "1"), ("2πT==2*pi*T", "1"), (r"$\pi{}b=\pi b$", "1"),
    ("replace(bc_1,vector('b',\"c_1\"),vector(2,3))", "6"),
    ("replace(bc_{1},vector('b',\"c_1\"),vector(2,3))", "6"),
    ("replace(bc2,vector('b','c'),vector(2,3))", "12"),
]:
    copied = data("quantum:scalars:"+formula)["copy_text"]
    assert copied == expected and data("quantum:scalars:"+copied)["copy_text"] == copied
for tolerance in ("-1", "i", "infinity", "[1;2]", "|u>", "qoperatorref('G')", "qtuple(vector(1,2))", "(x ← x+1)"):
    run(f"quantum:qestimatewithin(1≈(3/2),{tolerance})", "--json", success=False)
for invalid_update in (
    "x ← (y ← 1)", "qstepvalue(x ← x+1,[1;2])", "qstepvalue(3,5)",
    "qstepvalue(x ← |u>,2)", "qstepvalue(x ← 3,|u>)", "qstepvalue(x ← {1,2},2)",
    "qstepvalue(x ← x,qoperatorref('G'))", "qstepvalue(x ← x,qscalarupdate('y',2))",
):
    run("quantum:"+invalid_update, "--json", success=False)
print(f"PASS: {checks} worker process checks")
