"""Finite QB015 mathematical audit; never imports AutoQASM or calls a provider."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import subprocess

SOURCE_SHA = 'b7b1ed883412dc54375ae4fbbae533dde6a14782077d12d0a8d50865c34dddfd'

def walsh(signs):
    result = list(signs)
    step = 1
    while step < len(result):
        for start in range(0, len(result), 2*step):
            for i in range(start, start+step):
                a, b = result[i], result[i+step]
                result[i], result[i+step] = a+b, a-b
        step *= 2
    return result

def circuit_control(balanced):
    # Authored integer-amplitude interpretation of source cells11/18; qubit0
    # is the low bit. Ten Hadamards give the common denominator sqrt(2)^10=32.
    state = [0]*32
    state[16] = 1
    def hadamard(q):
        for i in range(32):
            if not i & (1 << q):
                j = i | (1 << q)
                a, b = state[i], state[j]
                state[i], state[j] = a+b, a-b
    for q in range(5):
        hadamard(q)
    if balanced:
        updated = [0]*32
        for i, amplitude in enumerate(state):
            updated[i ^ 16 if i & 8 else i] = amplitude
        state = updated
    for q in range(5):
        hadamard(q)
    expected = 24 if balanced else 16
    assert state[expected] == 32 and sum(x*x for x in state) == 1024
    return dict(balanced=balanced, basis_index=expected, ancilla_bit=1,
                measured_data_index=expected & 15, measured_width=4,
                convention='authored little-endian integer basis; not provider result-string order')

def worker_check(worker, expression, expected, environment):
    records = []
    for mode in ('exact', 'copy', 'approximate'):
        entry = expression if mode != 'copy' else records[0]['response']['copy_text']
        command = [str(worker), '--json'] + (['--approx'] if mode == 'approximate' else [])
        result = subprocess.run(command, input=entry.encode(), capture_output=True,
                                env=environment, timeout=30, check=True)
        data = json.loads(result.stdout)
        if mode == 'approximate':
            assert abs(float(data['text'].replace('−', '-'))-float(expected)) < 1e-12
        else:
            actual = Fraction(data['copy_text'].replace('∕', '/').replace('−', '-').replace(' ', ''))
            assert not data['approximate'] and actual == expected, (entry, data, expected)
        records.append(dict(mode=mode, input=entry, response=data, stderr=result.stderr.decode('utf-8')))
    return dict(source_cell=4 if expression.startswith('2*2^') else 3,
                input_kind='authored scalar instantiation or derived counterexample; not original TeX',
                expression=expression, expected=str(expected), executions=records)

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--worker', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    raw = args.source.read_bytes()
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA
    notebook = json.loads(raw)
    assert len(notebook['cells']) == 23
    args.output.mkdir(parents=True, exist_ok=False)
    environment = dict(os.environ, QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent/'data'))
    detailed, summaries, scalar_fixtures = [], [], []
    for n in range(1, 5):
        size = 1 << n
        histogram = Counter()
        balanced_tables = 0
        choices = itertools.chain(((), tuple(range(size))), itertools.combinations(range(size), size//2))
        for ones in choices:
            truth = [0]*size
            for i in ones:
                truth[i] = 1
            signs = [1-2*f for f in truth]
            transformed = walsh(signs)
            # Independently check the transform against the defining character sum.
            direct = [sum(signs[x] * (-1 if (x & y).bit_count() % 2 else 1)
                          for x in range(size)) for y in range(size)]
            assert transformed == direct
            assert sum(a*a for a in transformed) == size*size
            constant = len(ones) in (0, size)
            assert transformed[0]**2 == (size*size if constant else 0)
            if not constant:
                balanced_tables += 1
                first_difference = next(i+1 for i in range(1, size) if truth[i] != truth[0])
                histogram[first_difference] += 1
            detailed.append(dict(n=n, truth=''.join(map(str, truth)), walsh=transformed,
                                 zero_probability=int(constant)))
        assert balanced_tables == math.comb(size, size//2)
        assert max(histogram) == size//2+1
        exhaustion = Fraction(histogram[size//2+1], balanced_tables)
        assert exhaustion == Fraction(2, math.comb(size, size//2))
        literal_norm = Fraction(2*size, size+1)
        assert literal_norm != 1
        summaries.append(dict(n=n, balanced_tables=balanced_tables, constant_tables=2,
                              total_tables=balanced_tables+2, query_histogram=dict(histogram),
                              worst_queries=size//2+1, worst_query_probability=str(exhaustion),
                              source_stated_worst_probability=str(Fraction(1, 2**(n-1))),
                              literal_psi2_norm_squared=str(literal_norm), corrected_norm_squared='1'))
        scalar_fixtures.extend([(f'2*2^{n}/(2^{n}+1)', literal_norm),
                                (f'2*2^{n}/2^({n}+1)', Fraction(1)),
                                (f'2/binomial({size},{size//2})', exhaustion)])
        for k in range(1, min(size, 5)+1):
            same_without = Fraction(2*math.comb(size//2,k), math.comb(size,k)) if k <= size//2 else Fraction(0)
            same_with = Fraction(1, 2**(k-1))
            scalar_fixtures.append((f'1-2^(1-{k})', 1-same_with))
            if k <= size//2:
                scalar_fixtures.append((f'2*binomial({size//2},{k})/binomial({size},{k})', same_without))
    worker_results = [worker_check(args.worker, expr, value, environment) for expr, value in scalar_fixtures]
    source = dict(sha256=SOURCE_SHA, cells=[dict(index=i, type=c['cell_type'],
        sha256=hashlib.sha256(''.join(c['source']).encode()).hexdigest()) for i,c in enumerate(notebook['cells'])])
    report = dict(source=source, scope='exhaustive promised truth tables n1..4 and authored scalar circuit controls; not AutoQASM execution',
                  summaries=summaries, total_truth_tables=len(detailed), circuit_controls=[circuit_control(False), circuit_control(True)],
                  worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                  worker_cases=len(worker_results), worker_requests=3*len(worker_results), worker_results=worker_results,
                  source_code_executed=False, provider_jobs_submitted=False)
    for name, value in [('results.json', report), ('truth-tables.json', detailed)]:
        (args.output/name).write_bytes((json.dumps(value, indent=2)+'\n').encode())
    print(json.dumps(dict(truth_tables=len(detailed), worker_requests=3*len(worker_results), source_code_executed=False)))

if __name__ == '__main__':
    main()
