"""Replay the original IBM-031 search lesson and exhaust its two-bit search space."""
from replay_oracle_lesson import replay_lesson


def word(value, width):
    return f"qbitlabel({value},{width})"


def table(mask):
    pairs = [f"qtuple(vector({word(x,2)},{(mask >> x) & 1}))" for x in range(4)]
    return "qset(vector(" + ",".join(pairs) + "))"


def oracle_matrix(mask):
    # The target is the high bit in |a⟩|x⟩.
    elements = [str(int(row == (col ^ (((mask >> (col % 4)) & 1) << 2))))
                for row in range(8) for col in range(8)]
    return "matrix(8,8,[" + ",".join(elements) + "])"


def mode(i):
    if i == 24:
        return "bitword:"
    if i in (2, 4, 5, 8, 12, 23, 25, 35, 36, 37, 40, 41, 42, 43):
        return "oracles:"
    return ""


def cases():
    alphabet = "qset(vector(0,1))"
    yield 1, [("Σ", alphabet)], "1"
    yield 1, [("Σ", "qset(vector(0,1,2))")], "0"
    for n in (1, 2, 3):
        yield 10, [("n", n), ("N", 2**n)], "1"
        yield 10, [("n", n), ("N", 2**n-1)], "0"
        domain = "qset(vector(" + ",".join(word(x,n) for x in range(2**n)) + "))"
        yield 12, [("n", n)], domain
        for i in (4, 8, 25, 36, 41):
            name = "z" if i == 41 else "x"
            for width in (n, n+1):
                yield i, [("n", n), (name, word(1,width))], str(int(width == n))
    for a in (0, 1, 2):
        yield 26, [("Σ", alphabet), ("a", a)], str(int(a < 2))
    for mask in range(16):
        f = table(mask)
        for i in (2, 23, 35, 40):
            yield i, [("f", f), ("n", 2), ("Σ", alphabet)], "1"
        for x in range(4):
            flag = (mask >> x) & 1
            for i in (5, 37, 42, 43):
                name = "z" if i == 42 else "x"
                yield i, [("f", f), (name, word(x,2))], str(1-flag if i == 43 else flag)
            # Flipping only this truth-table entry changes both target transitions.
            for target in (0, 1):
                for matches in (True, False):
                    matrix = oracle_matrix(mask if matches else mask ^ (1 << x))
                    yield 24, [('"U_f"', matrix), ("f", f), ("a", target), ("x", word(x,2))], str(int(matches))
    for x in range(4):
        for z in range(4):
            yield 44, [("x", word(x,2)), ("z", word(z,2))], str(int(x != z))


if __name__ == "__main__":
    replay_lesson(__doc__, "ibm031-inventory.json", 45, mode, cases)
