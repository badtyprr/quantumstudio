"""Verify the IBM-033 Grover analysis formulas and finite rotation identities."""
from fractions import Fraction

from replay_oracle_lesson import replay_lesson


def mode(i):
    return "sets:" if i in (2, 6, 7, 13, 14, 15, 18, 38, 52) else ""


def column(values):
    return "matrix(4,1,[" + ",".join(map(str, values)) + "])"


def bind_together(bindings):
    names, values = zip(*bindings)
    return [("vector("+",".join(names)+")", "vector("+",".join(map(str, values))+")")]


def cases():
    for mask in range(1, 15):
        marked = [(mask >> i) & 1 for i in range(4)]
        count = sum(marked)
        unmarked = [1-b for b in marked]
        a1 = column(marked) + f"/sqrt({count})"
        a0 = column(unmarked) + f"/sqrt({4-count})"
        uniform = column([1]*4) + "/2"
        angle = {1: "pi/6", 2: "pi/4", 3: "pi/3"}[count]
        values = [str((Fraction(1,2) - int(i == j))*(1-2*marked[j]))
                  for i in range(4) for j in range(4)]
        iterate = "matrix(4,4,[" + ",".join(values) + "])"
        common = [("G", iterate), ('"θ"', angle), ('qnamedket("A_0")', a0), ('qnamedket("A_1")', a1)]
        for correct in (True, False):
            state = uniform if correct else "-("+uniform+")"
            initial = [('"u"', state)]
            for t in range(6):
                yield 97, bind_together(common+initial+[("t", t)]), str(int(correct))
            for line in range(3):
                yield (96,line), bind_together(common+initial), str(int(correct))
            for i, label, cardinality in ((83,"A_1",count), (88,"A_0",4-count)):
                theta = angle if correct else angle+"+pi"
                yield i, bind_together([(f'qbars("{label}")', cardinality), ("N",4), ('"θ"',theta)]), str(int(correct))
        basis_set = "qset(vector(" + ",".join(f"qbitlabel({x},2)" for x,b in enumerate(marked) if b) + "))"
        entries = ["0" if not b else {1:"1",2:"1 ∕ √(2)",3:"1 ∕ √(3)"}[count] for b in marked]
        yield 14, [('"S"', basis_set)], column(entries)


if __name__ == "__main__":
    replay_lesson(__doc__, "ibm033-inventory.json", 117, mode, cases)
