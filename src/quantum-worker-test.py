"""Exercise the worker process and JSON contract used by the Windows GUI."""
import json
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

# Indexed column constraints must survive symbolic dimensions and substitution.
for flags in [(), ("--approx",)]:
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
        assert data("quantum: " + first["text"], *flags) == first
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
for expression in [r"\sum_{k=0}^{1024}{|k>}", r"\sum_{k=1}^{2}{|k>}",
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
    [("0", "|1>")], [("Phi+", "|0>")], [("today", "|0>")],
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
