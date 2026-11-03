"""Prepare and independently check exact compact GUI clipboard results."""
import json
from pathlib import Path
import runpy
import sys

audit=runpy.run_path(str(Path(__file__).with_name('toric-probe.py')))
evidence=Path(sys.argv[2])
if sys.argv[1]=='prepare':
    selected={'18-qubit-value','exact-Y-phase','stars-dependency','rank','dimension',
              'distance','syndrome-0-Y','logical-0-2','logical-0-1'}
    cases=[case for case in audit['fixtures']()[0] if case['id'] in selected]
    assert len(cases)==len(selected)
    (evidence/'expressions.txt').write_text('\n'.join(c['expression'].removeprefix('quantum:') for c in cases),encoding='utf-8')
    (evidence/'expected.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
elif sys.argv[1]=='verify':
    cases=json.loads((evidence/'expected.json').read_text(encoding='utf-8'))
    for k,case in enumerate(cases):
        actual=(evidence/f'copy-{k}.txt').read_text(encoding='utf-8-sig')
        assert audit['parse_integer_result'](actual)==case['expected'],(case,actual)
    print(f'PASS: {len(cases)} independent exact GUI clipboard comparisons')
else:
    raise ValueError('Expected prepare or verify')
