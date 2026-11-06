"""Independent exact mathematics only; does not execute a product or SDK."""
from fractions import Fraction as Q
from itertools import product
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
SOURCE = Path('F:/src/libqalculate/cleanup-audit/math-lane-20261104/ibm021/source.ipynb')
SHA = '2a53c7740281662c4c68fd9b3a9492c3615ea3bbfead3c0d3cce9f2fab698f7a'

def rank(rows):
    pivots = {}
    for value in rows:
        while value:
            bit = value.bit_length()-1
            if bit in pivots:
                value ^= pivots[bit]
            else:
                pivots[bit] = value
                break
    return len(pivots)

def dot(a, b):
    return (a & b).bit_count() % 2

def probability(d, k):
    if k < d:
        return Q(0)
    result = Q(1)
    for i in range(d):
        result *= 1-Q(2**i, 2**k)
    return result

def rank_counts(d, k):
    # Count choices of next row inside/outside the current row span.
    counts = [1] + [0]*d
    for _ in range(k):
        new = [0]*(d+1)
        for r, count in enumerate(counts):
            new[r] += count*2**r
            if r < d:
                new[r+1] += count*(2**d-2**r)
        counts = new
    assert sum(counts) == 2**(d*k)
    return counts

def promise_secrets(table, n, m):
    if len(table) != 2**n or any(type(v) is not int or not 0 <= v < 2**m for v in table):
        return []
    return [s for s in range(2**n) if all((table[x] == table[y]) == (x == y or x^s == y)
            for x in range(2**n) for y in range(2**n))]

def inference(rows, n):
    if any(type(v) is not int or not 0 <= v < 2**n for v in rows):
        raise ValueError('sample outside explicit width')
    kernel = [s for s in range(2**n) if all(dot(s, y) == 0 for y in rows)]
    if len(kernel) == 1:
        state, candidate = 'zero_candidate', 0
    elif len(kernel) == 2:
        state, candidate = 'nonzero_candidate', kernel[1]
    else:
        state, candidate = 'insufficient_rank', None
    return dict(rows=rows, rank=rank(rows), kernel=kernel, state=state, candidate=candidate)

def main():
    raw = SOURCE.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SHA
    notebook = json.loads(raw)
    cell = notebook['cells'][0]
    body = ''.join(cell['source'])
    claim_starts = ["Let's suppose that we run the circuit independently", 'More generally, if we replace',
                    'If we have any probabilistic query algorithm', 'There are two main cases:',
                    "Here's an example of a function taking the form"]
    claims = []
    for number, start in enumerate(claim_starts):
        a = body.index(start)
        b = body.find('\n\n', a)
        if b < 0:
            b = len(body)
        text = body[a:b]
        claims.append(dict(id=f'C{number+1}', start=a, end=b, text=text,
                           sha256=hashlib.sha256(text.encode()).hexdigest()))
    (ROOT/'source-claims.json').write_text(json.dumps(dict(source_sha256=SHA, cell_id=cell['id'],
        offset_unit='Unicode codepoints of joined cell source, end exclusive', claims=claims), indent=2)+'\n')
    table = [19, 5, 5, 19, 26, 1, 1, 26]
    assert promise_secrets(table, 3, 5) == [3]
    probabilities = [sum((Q(sum((-1)**dot(x,y) for x in range(8) if table[x]==z),8)**2
                         for z in range(32)), Q(0)) for y in range(8)]
    assert probabilities == [Q(1,4) if y in [0,3,4,7] else Q(0) for y in range(8)]
    exhaustive = []
    for n in [1, 3]:
        for s in range(2**n):
            support = [y for y in range(2**n) if dot(y,s)==0]
            d = n if s==0 else n-1
            for k in range(5):
                counts = [0]*(d+1)
                for rows in product(support, repeat=k):
                    counts[rank(rows)] += 1
                assert counts == rank_counts(d,k)
                assert Q(counts[d],len(support)**k) == probability(d,k)
                exhaustive.append(dict(n=n,s=s,k=k,counts=counts,total=sum(counts)))
    general = []
    for n in range(1,13):
        for nonzero in [False, True]:
            d = n-int(nonzero)
            for k in range(n+11):
                counts = rank_counts(d,k)
                p = probability(d,k)
                assert p == Q(counts[d],2**(d*k))
                if k>n:
                    assert p >= 1-Q(1,2**(k-n))
                if k==n+10:
                    assert p > Q(999,1000)
                general.append(dict(n=n,nonzero_secret=nonzero,d=d,k=k,p=str(p)))
    cases = [inference(rows,3) for rows in [[],[0,0,0],[4,4,0],[4,3],[3,7,4,0],[4,2,1]]]
    assert [c['state'] for c in cases] == ['insufficient_rank']*3+['nonzero_candidate']*2+['zero_candidate']
    assert cases[3]['candidate']==cases[4]['candidate']==3
    # Same rank-two data under an injective promise is possible: candidate3 then is wrong.
    assert probability(3,2)==0 and inference([4,3],3)['candidate']==3
    invalid_tables = [[0]*8, [5]+table[1:], list(range(8))]
    assert not promise_secrets(invalid_tables[0],3,5)
    assert not promise_secrets(invalid_tables[1],3,5)
    assert not promise_secrets(invalid_tables[2],3,2)
    invalid_rows = [-1,8,True]
    for value in invalid_rows:
        try:
            inference([value],3)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid width accepted')
    receipt = dict(kind='STDLIB_EXACT_REFERENCE_NOT_NATIVE_OR_SDK', source_sha256=SHA,
        script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        original_table=table, distribution=[str(p) for p in probabilities], exhaustive=exhaustive,
        exact_probability_cases=general, inference_controls=cases,
        invalid_promise_controls=invalid_tables, invalid_sample_controls=invalid_rows,
        total_enumerated_sequences=sum(c['total'] for c in exhaustive), status='PASS')
    (ROOT/'reference-results.json').write_text(json.dumps(receipt,indent=2)+'\n')
    print(json.dumps(dict(status='PASS', exhaustive_cases=len(exhaustive),
        sequences=receipt['total_enumerated_sequences'], probability_cases=len(general))))

if __name__ == '__main__':
    main()
