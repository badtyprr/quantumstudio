"""Independent finite examples for the phase-estimation lesson's Windows text."""
from fractions import Fraction


def check_lesson(verify):
    def value(rows, bindings, expected):
        for n in rows:
            verify(n, bindings, True, str(expected))

    def relation(rows, bindings, expected):
        for n in rows:
            verify(n, bindings, expected)

    for bit in (0, 1):
        for n, label in [(79, "a_1"), (98, "a_1"), (93, "a_0"), (99, "a_0"),
                         (260, "b"), (270, "u"), (271, "v")]:
            value([n], [(label, bit)], bit)
    for n, bit in [(46, 0), (47, 1), (48, 1), (49, 0)]:
        value([n], [], f"basis({bit},2)")
    for n, label in [(89, "pi_1"), (146, "ψ"), (249, "|y>")]:
        for ket in ("|0>", "|->"):
            value([n], [(label, ket)], ket)
    for n, left, right in [(141, "ψ", "|y>"), (318, "ψ", "|y>"),
                           (241, "|x>", "|a>"), (255, "|x>", "|a>"), (276, "|x>", "|a>"),
                           (256, "|b>", "|y>"), (277, "|b>", "|y>")]:
        for i, j in [(0, 1), (1, 0)]:
            value([n], [(left, f"basis({i},2)"), (right, f"basis({j},2)")], f"basis({2*i+j},4)")

    for theta, phase in [("0", "1"), ("1/4", "i"), ("1/2", "-1"), ("3/4", "-i")]:
        f = Fraction(theta)
        value([58], [("θ", theta)], theta)
        value([68, 101], [("θ", theta)], 2*f)
        value([51], [("θ", theta)], f"P(2*pi*({theta}))*|+>")
        for sign in ("", "-"):
            pair = [("λ", f"{sign}({phase})"), ("θ", theta)]
            relation([20, 64, 92], pair, not sign)
            relation([66], pair, True)
        relation([66], [("λ", f"2*({phase})"), ("θ", theta)], False)
    for n in [61, 65, 299, 309]:
        for k in ([2] if n in (61, 65) else [1, 2, 3]):
            bindings = [("U", "X")] + ([("k", k)] if n in (299, 309) else [])
            value([n], bindings, "X" if k % 2 else "X*X")

    for width in (2, 3):
        size = 2**width
        ref = [("m", width)]
        for n, expected in [(245, size//2), (291, width//2), (304, size-1)]:
            value([n], ref, expected)
        for n, threshold in [(222, 2), (229, 2), (240, 2), (284, 2)]:
            for m in (threshold-1, threshold, threshold+1):
                relation([n], [("m", m)], m >= threshold)
        for n, target in [(228, 5), (238, 1), (282, 1), (314, 2), (360, 2), (394, 3), (395, 4)]:
            for m in (target, target+1):
                relation([n], [("m", m)], m == target)
        for y in (0, size-1):
            for offset in (-1, 0, 1, 2, 3):
                theta = Fraction(2*y+offset, 2*size)
                data = ref + [("y", y), ("θ", str(theta))]
                delta = abs(theta-Fraction(y, size))
                relation([315, 333], data, delta == 0)
                relation([335], data, delta != 0)
                relation([345, 354], data, delta <= Fraction(1, 2*size))
                relation([355], data, abs(offset) <= 1)
                relation([364], data, Fraction(1, size) <= delta <= Fraction(1, 2))
                relation([370], data, True)
            for turn in (-3,-1,1,3):
                theta = Fraction(4*y+turn,4*size)
                phase = ref + [("y",y), ("θ",str(theta))]
                relation([355], phase, abs(turn) == 1)
                relation([370], phase, True)
            value([350], ref+[("y", y)], Fraction(y-1, size))
            value([351], ref+[("y", y)], Fraction(y+1, size))
            value([365], ref+[("z", y)], Fraction(y, size))
        relation([370], ref+[("y",size//2), ("θ",str(Fraction(1,4*size)))], True)
        for z in (-1, 0, size//2-1, size//2, size-1, size):
            for n, label, limit in [(226, "y", size//2), (242, "x", size//2), (268, "u", size),
                                    (316, "y", size), (344, "y", size), (363, "y", size)]:
                relation([n], ref+[(label, z)], 0 <= z < limit)
        for a,b in [(0,1), (1,0), (2,1), (0,-1)]:
            relation([263, 273], [("a", a), ("b", b)], a in (0,1) and b in (0,1))
        for x,y in [(0, size//2-1), (size//2, 0), (0,-1)]:
            relation([264,274], ref+[("x", x), ("y", y)], 0 <= x < size//2 and 0 <= y < size//2)
    for z in (-1, 0, 2, 3, 4):
        relation([104], [("x", z)], 0 <= z <= 3)
        relation([109,117,136,140], [("y", z)], 0 <= z <= 3)
        value([150,152], [("y", z)], Fraction(z,4))
        for theta in (Fraction(z,4), Fraction(1,8)):
            pair = [("θ", str(theta)), ("y", z)]
            relation([108,138,139], pair, theta == Fraction(z,4))
            relation([110,144], [("θ", str(theta))], theta in {Fraction(i,4) for i in range(4)})
            relation([324], [("θ", str(theta))], 0 <= theta < 1)
    for p in ("0", "1/4", "1/2", "1"):
        relation([334], [("p_y", p)], p == "1")
        relation([374], [("p_y", p)], Fraction(p) <= Fraction(1,4))
    value([340], [], "pi/2")
    value([361], [], "4/pi^2")

    for dim, root in [(2, "-1"), (3, "(-1+i*sqrt(3))/2"), (4, "i")]:
        base = [("N", dim)]
        roots = [("ω_N", root)] + base
        value([170], [("ω_N", root)], root)
        value([174], base, f"2*pi/{dim}")
        value([175], base, Fraction(1,dim))
        value([185], base, f"1/sqrt({dim})")
        value([193,216], base, f"fourier({dim})")
        for candidate in (root, "2"):
            relation([172,210], [("ω_N", candidate)]+base, candidate == root)
        for y,z in [(0,0), (0,1), (dim-1,0)]:
            indices = [("y", y), ("z", z)]
            relation([196], [("y", y)], y == 0)
            relation([197], base+[("y", y)], y == dim-1)
            relation([203], indices, y == z)
            relation([207], indices, y != z)
            relation([211], roots+indices, True)
            relation([212], roots+indices, y != z)
            alpha = f"exp(2*pi*i*({y-z})/{dim})"
            for candidate, ok in [(alpha, True), ("2", False)]:
                relation([202], [("α", candidate)]+roots+indices, ok)
            if y != z:
                for column in (y,z):
                    states = [("φ_z", f"fourier({dim})*basis({z},{dim})"),
                              ("φ_y", f"fourier({dim})*basis({column},{dim})")]
                    relation([209], states+roots+indices, column == y)
    for alpha in ("0", "1", "i"):
        relation([204], [("α", alpha)], alpha == "1")
        relation([208], [("α", alpha)], alpha != "1")
    value([192], [], "H")
    for width in (2,3):
        size = 2**width
        ref = [("m", width)]
        value([293], ref, f"fourier({size})")
        for n, angle in [(232, f"pi/{size//2}"), (234, "pi/2")]:
            for sign in ("", "-"):
                relation([n], [("α", f"{sign}({angle})")] + (ref if n == 232 else []), not sign)
        for y in (0,1,size-1):
            root = f"exp(2*pi*i/{size})"
            value([248], ref + [(f"ω_{size}",root),("y", y)], f"exp(2*pi*i*{y}/{size})")
        for b in (0,1):
            for root in (f"exp(2*pi*i/{size})", "2"):
                relation([266], ref+[(f"ω_{size}",root),("x",1),("b",b)], root != "2" or b == 0)
        count = width**2
        value([280], [("s_m", count)], count)
        value([285], ref+[(f"s_{width-1}", count)], count)
        for total in (count, count+1):
            relation([289], [("s_m", total)] + ref + [(f"s_{width-1}", (width-1)**2)], total == count)
    for n in (31,32,33):
        relation([254], [("N", n)], n == 32)
    for count in (0,1):
        relation([283], [("s_1", count)], count == 1)
    for value_theta in ("1/4", "3/8", "1/2"):
        relation([159], [("θ", value_theta)], value_theta == "3/8")


def check_structured(inventory, records, exact):
    """Verify grouped rows separately and use the lesson width for unlabeled basis indices."""
    import re

    checks = {}

    def record(n, form, case):
        checks.setdefault(inventory["rows"][n-1]["id"], {}).setdefault(form, []).append(case)

    for n in (25, 121, 164, 231, 272, 278, 279, 292, 295):
        row = records[inventory["rows"][n-1]["id"]]
        for form in ("display", "copy", "second_copy"):
            text = row[form]

            def expect(expr, bindings, expected, part=1):
                for name, value in bindings:
                    expr = f"replace(({expr}),{name},({value}))"
                result = exact(expr)
                assert result == str(expected), (n, form, part, bindings, expected, result)
                record(n, form, dict(part=part, bindings=bindings, expected=expected))

            if n in (25, 272, 279):
                if form == "display":
                    parts = [re.sub(r"^\d+\.\s+", "", x) for x in text.split("\n\n")]
                else:
                    assert text.startswith(r"\begin{gathered}") and text.endswith(r"\end{gathered}")
                    parts = text.removeprefix(r"\begin{gathered}").removesuffix(r"\end{gathered}").split(r"\\")
                assert len(parts) == 2
                for index, expr in enumerate(parts):
                    if n == 25:
                        for phase, probs in [("0", ("1","0")), ("1/4", ("1/2","1/2")), ("1/2", ("0","1"))]:
                            for p in (probs[index], "1/4"):
                                expect(expr, [(f"p_{index}", p), ("θ", phase)], int(p == probs[index]), index+1)
                    elif n == 272:
                        for x, bit in [(0,1), (1,0), (1,1)]:
                            bindings = [("x", x), ("a", bit)] if index == 0 else [("m",2), ("y",x), ("b",bit)]
                            correct = 2*x+bit if index == 0 else 2*bit+x
                            for offset in (0,1):
                                expect(expr, bindings+[(("v" if index else "u"),correct+offset)], 1-offset,index+1)
                    else:
                        # Specify the two-qubit result register from the lesson. A symbolic
                        # integer index alone carries no dimension in either Windows form.
                        if form == "display":
                            assert expr.endswith("⟩ (dimension unresolved)")
                            expr = expr.replace("⟩ (dimension unresolved)", "⟩_4")
                        else:
                            assert expr.count("qcomputationalket(") == 1 and expr.endswith("),4)")
                            expr = expr.replace("qcomputationalket(", "qbasis(")[:-4]+",4),4)"
                        labels = ("x","a") if index == 0 else ("b","y")
                        for high, low in [(0,1), (1,0), (1,1)]:
                            for flip in (0,1):
                                bindings = [(f"|{labels[0]}>",f"basis({high^flip},2)"),
                                            (f"|{labels[1]}>",f"basis({low},2)"),
                                            (labels[0],high), (labels[1],low)]
                                if index:
                                    bindings.append(("m",2))
                                expect(expr, bindings, 1-flip,index+1)
            elif n == 121:
                states = [(f"φ_{i}", f"fourier(4)*basis({i},4)") for i in range(4)]
                for column, member in [(ket, True) for _, ket in states] + [("basis(0,4)", False)]:
                    expect(f"({column}) ∈ ({text})", states, int(member))
            elif n in (164, 292):
                # Big-O describes a family. The displayed exponent identifies the order.
                assert text == ("O(m^2)" if form == "display" else "qbigorder(qpower('m',2))")
                record(n, form, dict(expected="quadratic order in m"))
            elif n == 278:
                if form == "display":
                    assert text == "{0, …, 2^m − 1} (integer endpoints)"
                    record(n, form, dict(expected="integer range from zero through 2^m-1"))
                else:
                    for width in (2,3):
                        for y in (-1,0,2**width-1,2**width):
                            expect(f"({y}) ∈ ({text})", [("m",width)], int(0 <= y < 2**width))
            else:
                for gate in ("X","Z"):
                    expect(f"(({text}) = ({gate}))", [("P_α",gate)], 1)
    return checks
