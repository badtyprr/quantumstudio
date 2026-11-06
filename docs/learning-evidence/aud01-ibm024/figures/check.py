"""Authored finite transcription of visually inspected IBM024 Boolean diagrams."""
import hashlib
import itertools
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
def xor(a, b):
    return (a and not b) or (not a and b)
def half(a, b):
    return int(xor(a, b)), a & b
def full(c, a, b):
    s, carry1 = half(a, b)
    out, carry2 = half(c, s)
    return out, carry1 | carry2

rows = []
for a, b in itertools.product(range(2), repeat=2):
    s, c = half(a, b)
    assert int(xor(a, b)) == (a != b)
    assert (s, c) == ((a + b) % 2, (a + b) // 2)
    rows.append({'inputs': [a, b], 'xor': s, 'half_sum_carry': [s, c]})
full_rows = []
for c, a, b in itertools.product(range(2), repeat=3):
    result = full(c, a, b)
    assert result == ((a + b + c) % 2, (a + b + c) // 2)
    full_rows.append({'inputs_c_a_b': [c, a, b], 'sum_carry': result})
addition_rows = []
for a, b in itertools.product(range(16), repeat=2):
    s, c = half(a & 1, b & 1)
    bits = [s]
    for i in range(1, 4):
        s, c = full(c, (a >> i) & 1, (b >> i) & 1)
        bits.append(s)
    bits.append(c)
    output = ''.join(map(str, reversed(bits)))
    assert output == format(a + b, '05b')
    addition_rows.append({'a': format(a, '04b'), 'b': format(b, '04b'), 'output': output})
result = {'scope': 'Authored Boolean wiring model, not original code or calculator execution',
          'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
          'xor_and_half_rows': rows, 'full_rows': full_rows,
          'four_bit_addition_rows': addition_rows,
          'independent_oracle': 'Integer sum modulo/division by2 and Python integer addition with fixed five-bit formatting',
          'exact': True, 'tolerance': None,
          'gate_counts_n4': {'expanded_XOR_with_fanout': 73, 'primitive_XOR_with_fanout': 31, 'primitive_XOR_without_fanout': 17}}
(ROOT / 'check-results.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
print('PASS:4 XOR,4 half-adder,8 full-adder,256 four-bit addition cases; exact')
