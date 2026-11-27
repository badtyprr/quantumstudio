"""Bind the original IBM-033 state definitions to the two sets of search words."""
from replay_oracle_lesson import replay_lesson


def word_set(indices):
    return "qset(vector(" + ",".join(f"qbitlabel({i},2)" for i in sorted(indices)) + "))"


def cases():
    for mask in range(16):
        marked = {i for i in range(4) if mask & (1 << i)}
        unmarked = set(range(4)) - marked
        for line, indices in enumerate((unmarked, marked)):
            if not indices:
                continue
            domain = word_set(indices)
            yield (8, line), [(f'"A_{line}"', domain)], "1"
            amplitude = {1: "1", 2: "1 ∕ √(2)", 3: "1 ∕ √(3)", 4: "1 ∕ 2"}[len(indices)]
            entries = [amplitude if i in indices else "0" for i in range(4)]
            yield 14, [('"S"', domain)], "matrix(4,1,[" + ",".join(entries) + "])"
        if not marked or not unmarked:
            continue
        angle = {1: "pi/6", 2: "pi/4", 3: "pi/3"}[len(marked)]
        for i in (19, 68, 91):
            labels = ['"A_0"', '"A_1"', '"N"', '"u"']
            for state, expected in (("[1;1;1;1]/2", "1"), ("[1;1;-1;1]/2", "0")):
                values = [word_set(unmarked), word_set(marked), "4", state]
                keys = labels + (['"θ"'] if i == 91 else [])
                if i == 91:
                    values.append(angle)
                yield i, [("vector(" + ",".join(keys) + ")", "vector(" + ",".join(values) + ")")], expected


if __name__ == "__main__":
    replay_lesson(__doc__, "ibm033-inventory.json", 117,
                  lambda i: "sets:" if i in (2, 6, 7, 13, 14, 15, 18, 38, 52) else "", cases)
