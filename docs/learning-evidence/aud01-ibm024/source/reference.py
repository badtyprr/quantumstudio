"""Independent finite IBM024 references; no calculator, SDK or media access."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE_SHA = '554cc9694595ec167fb501776310e6bfdfe0a87a5c638d2c79ba8a4fdf09bbcd'


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def binary(n):
    if n == 0:
        return '0'
    digits = []
    while n:
        n, bit = divmod(n, 2)
        digits.append(str(bit))
    return ''.join(reversed(digits))


def ripple(a, b):
    carry = 0
    output = []
    for x, y in zip(reversed(a), reversed(b)):
        x, y = int(x), int(y)
        output.append(str(x ^ y ^ carry))
        carry = (x & y) | (x & carry) | (y & carry)
    return str(carry) + ''.join(reversed(output))


def main():
    check(hashlib.sha256((ROOT / 'source.ipynb').read_bytes()).hexdigest() == SOURCE_SHA,
          'source hash mismatch')
    rows = []
    original_binary = ['0', '1', '10', '11', '100', '101', '110', '111', '1000']
    original_lengths = [1, 1, 2, 2, 3, 3, 3, 3, 4]
    original_unary = ['', '0', '00', '000', '0000', '00000', '000000', '0000000', '00000000']
    original_lex = ['', '0', '1', '00', '01', '10', '11', '000', '001']
    for n in range(9):
        actual = (binary(n), len(binary(n)), '0' * n, binary(n + 1)[1:])
        expected = (original_binary[n], original_lengths[n], original_unary[n], original_lex[n])
        check(actual == expected, ('original table', n))
        rows.append({'n': n, 'binary': actual[0], 'length': actual[1],
                     'unary': actual[2], 'lexicographic': actual[3]})

    additions = []
    for a in range(16):
        for b in range(16):
            left, right = format(a, '04b'), format(b, '04b')
            actual, expected = ripple(left, right), format(a + b, '05b')
            check(actual == expected and len(actual) == 5, ('ripple', a, b))
            additions.append({'a': left, 'b': right, 'result': actual})

    lengths = [{'j': None, 'delta': None, 'n': 0, 'length': len(binary(0))}]
    check(lengths[0]['length'] == 1, 'zero length')
    for j in range(1, 33):
        for delta in (-1, 0, 1):
            n = 2 ** j + delta
            length = len(binary(n))
            # Exact inequalities uniquely characterize canonical positive length.
            check(2 ** (length - 1) <= n < 2 ** length, ('binary length', j, delta))
            lengths.append({'j': j, 'delta': delta, 'n': n, 'length': length})

    divisions = []
    for n in range(-16, 17):
        for m in range(-8, 9):
            if m == 0:
                continue
            magnitude_q, remainder = divmod(n, abs(m))
            quotient = magnitude_q if m > 0 else -magnitude_q
            # Independent bounded search for the unique contract-satisfying pair.
            # Every quotient in this declared domain has magnitude <=16.
            candidates = [(q, n - q * m) for q in range(-32, 33)
                          if 0 <= n - q * m < abs(m)]
            check(candidates == [(quotient, remainder)], ('division', n, m))
            divisions.append({'n': n, 'm': m, 'q': quotient, 'r': remainder})

    powers = []
    for n in range(-8, 9):
        for k in range(9):
            if n == 0 and k == 0:
                continue
            for m in range(1, 10):
                product = 1
                for _ in range(k):
                    product *= n
                actual = product % m
                expected = pow(n, k, m)
                check(actual == expected and 0 <= actual < m, ('modular power', n, k, m))
                powers.append({'n': n, 'k': k, 'm': m, 'r': actual})

    results = {
        'status': 'all declared independent Python reference comparisons passed',
        'source_sha256': SOURCE_SHA,
        'reference_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'source_cell_id': '5c5b90e6',
        'arithmetic': 'exact integers; no numerical tolerance',
        'limitations': ['No native calculator, SDK, GUI, media, circuit wiring or gate-count validation.',
                       'No whole-source, unbounded-family, uniformity or complexity acceptance.',
                       'Extended cases are authored adaptations, not additional original examples.',
                       'Empty string stored as JSON empty string, not numeric zero.',
                       '0^0 omitted because original convention is ambiguous.'],
        'groups': {
            'original_encoding_rows': {'classification': 'transcription of nine original table rows; inferred lex extension used only to check these rows', 'source_offsets': [1847, 2818], 'count': len(rows), 'cases': rows},
            'four_bit_addition': {'classification': 'authored exhaustive finite adaptation of source four-bit illustration', 'source_offsets': [18538, 18568, 20439], 'count': len(additions), 'oracle': 'bitwise ripple carry vs independent integer addition and fixed-width formatting', 'cases': additions},
            'binary_length': {'classification': 'authored zero plus j=1..32, delta=-1,0,1 boundary occurrences; repeated values retained', 'source_offsets': [4004, 4112], 'count': len(lengths), 'distinct_inputs': len({x['n'] for x in lengths}), 'oracle': 'repeated division encoding vs exact power-of-two interval', 'cases': lengths},
            'signed_division': {'classification': 'authored N=-16..16, M=-8..8 excluding zero', 'source_offsets': [24317, 24468], 'count': len(divisions), 'oracle': 'sign-adjusted positive-divisor divmod vs unique bounded quotient search', 'cases': divisions},
            'modular_exponentiation': {'classification': 'authored N=-8..8, K=0..8, M=1..9 excluding N=K=0', 'source_offsets': [25364, 25527], 'count': len(powers), 'oracle': 'repeated full integer multiplication then remainder vs three-argument pow', 'cases': powers}
        }
    }
    (ROOT / 'reference-results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({k: v['count'] for k, v in results['groups'].items()}))


if __name__ == '__main__':
    main()
