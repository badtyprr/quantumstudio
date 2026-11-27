"""Verify the phases of the original Grover oracles and their action on word sets."""
from replay_oracle_lesson import replay_lesson


def diagonal(signs):
    return "[" + ";".join(",".join(str(sign if i == j else 0) for j in range(len(signs)))
                          for i, sign in enumerate(signs)) + "]"


def assign(labels, values):
    return [("vector(" + ",".join(labels) + ")", "vector(" + ",".join(values) + ")")]


def cases():
    for f in (0, 1):
        for g in (0, 1):
            yield 37, assign(["f(x)", "g(x)"], [str(f), str(g)]), str(int(f != g))
    for mask in range(16):
        signs = [-1 if mask & (1 << i) else 1 for i in range(4)]
        oracle = diagonal(signs)
        complement = diagonal([-sign for sign in signs])
        for other, expected in ((complement, "1"), (oracle, "0")):
            yield 39, assign(['"Z_f"', '"Z_g"'], [oracle, other]), expected
        # In four dimensions the diffusion matrix has -1/2 on the
        # diagonal and +1/2 elsewhere. Z_f signs each input column.
        iterate = "[" + ";".join(",".join(str(signs[j] * (-1 if i == j else 1))
                                          for j in range(4)) for i in range(4)) + "]/2"
        for supplied, expected in ((oracle, "1"), (complement, "0")):
            yield 31, assign(["G", '"Z_f"', '"Z_OR"', "n"],
                             [iterate, supplied, diagonal([1, -1, -1, -1]), "2"]), expected
        if mask not in (0, 15):
            sets = ["qset(vector(" + ",".join(f"qbitlabel({i},2)" for i in range(4)
                                              if signs[i] == sign) + "))" for sign in (1, -1)]
            for line in (0, 1):
                for gate, expected in ((iterate, "1"), (f"-({iterate})", "0")):
                    yield (70, line), assign(["G", '"N"', '"A_0"', '"A_1"'], [gate, "4", *sets]), expected
        for line, sign in enumerate((1, -1)):
            labels = [f"qbitlabel({i},2)" for i in range(4) if signs[i] == sign]
            if not labels:
                continue
            support = "qset(vector(" + ",".join(labels) + "))"
            for row in (48, 102):
                for supplied, expected in ((oracle, "1"), (complement, "0")):
                    yield (row, line), assign(['"Z_f"', f'"A_{line}"'], [supplied, support]), expected
    for n in range(1, 5):
        size = 2**n
        signs = [1] + [-1] * (size - 1)
        oracle = diagonal(signs)
        for x in range(size):
            flipped = signs.copy()
            flipped[x] *= -1
            for supplied, expected in ((oracle, "1"), (diagonal(flipped), "0")):
                yield 51, assign(['"Z_OR"', "x", "n"], [supplied, f"qbitlabel({x},{n})", str(n)]), expected
        for supplied, expected in ((oracle, "1"), (diagonal([-s for s in signs]), "0")):
            yield 53, assign(['"Z_OR"', '"n"'], [supplied, str(n)]), expected


if __name__ == "__main__":
    replay_lesson(__doc__, "ibm033-inventory.json", 117,
                  lambda i: "sets:" if i in (2, 6, 7, 13, 14, 15, 18, 38, 52) else "", cases)
