"""Frozen finite IBM025 references only; no native/SDK/media execution."""
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = 'ec06bb65c2b394c9d5053a3dcbcf9407972a8fdca1fed4f0de8c357e91a72df7'


def require(condition, label):
    if not condition:
        raise AssertionError(label)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def ccx(a, b, t):
    return a, b, t ^ (a & b)


def stage(vector, mapping):
    output = [0] * len(vector)
    for i, coefficient in enumerate(vector):
        output[mapping(i)] += coefficient
    return output


def main():
    original = (ROOT / 'source.ipynb').read_bytes()
    require(digest(original) == SOURCE_SHA, 'source hash')
    plan = (ROOT / 'research.md').read_bytes()
    require(b'Frozen reference plan (recorded before execution)' in plan, 'plan frozen first')
    source = ''.join(json.loads(original)['cells'][0]['source'])
    literal = source[1727:2023]
    body = literal.split('\\begin{pmatrix}\n', 1)[1].split('\\end{pmatrix}', 1)[0]
    matrix = [[int(v.strip()) for v in row.strip().split('&')]
              for row in body.strip().split('\\\\')]
    require(len(matrix) == 8 and all(len(row) == 8 for row in matrix), 'matrix dimensions')
    require(all(v in (0, 1) for row in matrix for v in row), 'matrix entries')
    cases = {name: [] for name in ['toffoli', 'boolean', 'swap', 'clean_query',
                                  'coherent_query', 'invertible', 'replacement_maps']}
    for i in range(8):
        a, b, t = i & 1, (i >> 1) & 1, i >> 2
        target = i ^ (4 if a and b else 0)
        column = [matrix[r][i] for r in range(8)]
        require(column == [int(r == target) for r in range(8)], ('Toffoli', i))
        require([sum(matrix[r][j] * column[j] for j in range(8)) for r in range(8)]
                == [int(r == i) for r in range(8)], ('involution', i))
        cases['toffoli'].append({'input': i, 'output': target, 'full_column': column})
    for a, b in itertools.product(range(2), repeat=2):
        and_state = ccx(a, b, 0)
        inverted = ccx(a ^ 1, b ^ 1, 0)
        or_state = (inverted[0] ^ 1, inverted[1] ^ 1, inverted[2] ^ 1)
        require(and_state == (a, b, int(bool(a) and bool(b))), 'AND')
        require(or_state == (a, b, int(bool(a) or bool(b))), 'OR')
        cases['boolean'].extend([{'gate': 'AND', 'input': [a, b], 'full_state': and_state},
                                 {'gate': 'OR', 'input': [a, b], 'full_state': or_state}])
    for a in range(2):
        require((a ^ 1) == 1 - a, 'NOT')
        require((a, 0 ^ a) == (a, a), 'FANOUT')
        cases['boolean'].extend([{'gate': 'NOT', 'input': a, 'output': a ^ 1},
                                 {'gate': 'FANOUT', 'input': a, 'output': [a, a]}])
    for a, b in itertools.product(range(2), repeat=2):
        x, y = a, b
        y ^= x
        x ^= y
        y ^= x
        require((x, y) == (b, a), 'SWAP')
        cases['swap'].append({'input': [a, b], 'output': [x, y]})
    for f in itertools.product(range(2), repeat=4):
        def compute(i):
            return i ^ (f[i & 3] << 2)
        def copy(i):
            return i ^ (((i >> 2) & 1) << 3)
        for y, x in itertools.product(range(2), range(4)):
            initial = y * 8 + x
            first = compute(initial)
            second = copy(first)
            final = compute(second)
            expected = (y ^ f[x]) * 8 + x
            require(final == expected and final & 4 == 0, 'clean query')
            cases['clean_query'].append({'f': f, 'x': x, 'y': y,
                                        'stages': [initial, first, second, final]})
        vector = [0] * 16
        for j, coefficient in enumerate([1, -1, 2, -2, 3, -3, 4, -4]):
            vector[(j // 4) * 8 + j % 4] = coefficient
        actual = stage(stage(stage(vector, compute), copy), compute)
        expected = [0] * 16
        for y, x in itertools.product(range(2), range(4)):
            expected[(y ^ f[x]) * 8 + x] = vector[y * 8 + x]
        require(actual == expected, 'coherent query vector')
        require(all(actual[i] == 0 for i in range(16) if i & 4), 'workspace cleanup')
        require(sum(v * v for v in actual) == 60, 'coherent exact norm')
        cases['coherent_query'].append({'f': f, 'input_coefficients': vector,
                                       'output_coefficients': actual, 'normalization_squared': 60})
    for f in itertools.permutations(range(4)):
        inverse = [f.index(y) for y in range(4)]
        for x in range(4):
            low, high = x, 0
            high ^= f[low]
            first = [low, high]
            low ^= inverse[high]
            second = [low, high]
            low, high = high, low
            require((low, high) == (f[x], 0), 'invertible clean replacement')
            cases['invertible'].append({'f': f, 'inverse': inverse, 'x': x,
                                         'stages_low_high': [[x, 0], first, second, [low, high]]})
    unitary_count = 0
    for f in itertools.product(range(4), repeat=4):
        columns = [[int(row == f[col]) for row in range(4)] for col in range(4)]
        gram = [[sum(a * b for a, b in zip(columns[i], columns[j]))
                 for j in range(4)] for i in range(4)]
        unitary = gram == [[int(i == j) for j in range(4)] for i in range(4)]
        require(unitary == (len(set(f)) == 4), 'finite bijective/unitary equivalence')
        unitary_count += int(unitary)
        cases['replacement_maps'].append({'f': f, 'full_columns': columns,
                                           'gram': gram, 'unitary': unitary})
    counts = {k: len(v) for k, v in cases.items()}
    require(list(counts.values()) == [8, 12, 4, 128, 16, 96, 256], 'frozen counts')
    require(unitary_count == 24, '24 permutations')
    result = {'status': 'passed finite independent references only', 'source_sha256': SOURCE_SHA,
              'plan_before_execution_sha256': digest(plan),
              'script_sha256': digest(Path(__file__).read_bytes()), 'counts': counts,
              'total_cases': sum(counts.values()), 'replacement_summary': {'unitary': 24, 'nonunitary': 232},
              'provenance': 'Original Toffoli matrix; all enumerated inputs and other finite constructions authored. Media uninspected.',
              'exactness': 'integer/rational references, no tolerance; coherent coefficients normalized by sqrt(60)',
              'limitations': ['No native/SDK/GUI execution', 'No media acquisition or gate-count claim',
                              'No whole-lesson, arbitrary-family or general-theorem acceptance'], 'cases': cases}
    (ROOT / 'reference-results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'counts': counts, 'total': sum(counts.values()), 'plan_sha256': digest(plan)}))


if __name__ == '__main__':
    main()
