"""Replay the IBM-032 Grover search operator and its source equations."""
from fractions import Fraction

from replay_oracle_lesson import replay_lesson


def mode(i):
    if i in (14, 16):
        return "bitword:"
    if i in (4, 5, 55, 57):
        return "oracles:"
    return ""


def matrix(d, entry):
    return f"matrix({d},{d},[" + ",".join(str(entry(r,c)) for r in range(d) for c in range(d)) + "])"


def phase(d, mask):
    return matrix(d, lambda r,c: (1-2*((mask >> c) & 1)) if r == c else 0)


def cases():
    for n in range(1, 5):
        d = 2**n
        zeros = f"matrix({d},1,[1," + ",".join("0" for _ in range(d-1)) + "])"
        yield 31, [("n", n)], zeros
        all_nonzero = (1 << d) - 2
        for x in range(d):
            word = f"qbitlabel({x},{n})"
            yield 14, [("x", word), ("n", n)], "1"
            for matches in (True, False):
                mask = all_nonzero if matches else all_nonzero ^ (1 << x)
                yield 16, [('"Z_OR"', phase(d,mask)), ("x", word), ("n", n)], str(int(matches))

    # All two-bit predicates, including no marked word and multiple marked words.
    for mask in range(16):
        signs = [1-2*((mask >> x) & 1) for x in range(4)]
        oracle = phase(4,mask)
        graph = "qset(vector(" + ",".join(f"qtuple(vector(qbitlabel({x},2),{(mask >> x) & 1}))" for x in range(4)) + "))"
        for x in range(4):
            bindings = [("f", graph), ("x", f"qbitlabel({x},2)")]
            for matches in (True, False):
                supplied = oracle if matches else phase(4,mask ^ (1 << x))
                yield 4, bindings + [('"Z_f"', supplied)], str(int(matches))
            for i, predicate in ((55, 1), (57, 0)):
                yield i, bindings, str(int((mask >> x) & 1 == predicate))
        # Reflection about the uniform state has entries 2/N - delta(r,c).
        for overall_sign in (1, -1):
            grover = matrix(4, lambda r,c: overall_sign*signs[c]*(Fraction(1,2)-int(r==c)))
            yield 34, [("n", 2), ('"Z_f"', oracle), ('"Z_OR"', phase(4,14)), ("G", grover)], str(int(overall_sign == 1))


if __name__ == "__main__":
    replay_lesson(__doc__, "ibm032-inventory.json", 59, mode, cases)
