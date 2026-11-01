#!/usr/bin/env python3
"""DEV-10 equality fixtures; references/adaptations in learning-evidence/DEV-10.md."""
import json
import os
import subprocess
import sys
from pathlib import Path

worker = str(Path(sys.argv[1] if len(sys.argv)>1 else 'quantum-worker'+('.exe' if os.name=='nt' else '')).resolve())
checks = 0

def evaluate(expression):
    global checks
    result = subprocess.run([worker, '--json']+flags, input=('quantum: '+expression).encode(), capture_output=True, timeout=30)
    assert result.returncode == 0, (expression, result.stderr.decode())
    checks += 1
    return json.loads(result.stdout)

for flags in [[], ['--approx']]:
    for expression in ['member(x,Σ)', 'member(x,vector(y))',
                       'cardinality(vector(x,y))', 'sumset(k,vector(x,y),k)']:
        value = evaluate(expression)
        assert value['text'] not in ['0', '1', '2', 'x + y'], (expression, value)
        # Serialization is executable, and retains the same unresolved condition.
        copied = evaluate(value['copy_text'])
        # Re-entry alpha-renames internal binders; visible meaning must survive.
        assert copied['display_text'] == value['display_text'], (expression, value, copied)
        assert evaluate(copied['copy_text'])['display_text'] == copied['display_text']
        for original in [expression, copied['copy_text']]:
            resolved = evaluate('replace(replace(replace('+original+',x,2),y,2),Σ,vector(2))')
            assert resolved['text'] == ('2' if expression.startswith('sumset') else '1'), (original, resolved)
    for expression, expected in [
        ('replace(member(x,vector(y)),x,y)', '1'),
        ('replace(replace(member(x,vector(y)),x,2),y,3)', '0'),
        ('replace(cardinality(vector(x,y)),y,x)', '1'),
        ('replace(replace(cardinality(vector(x,y)),x,2),y,3)', '2'),
        ('replace(sumset(k,vector(x,y),k),y,x)', 'x'),
        ('member(x,vector(x,y))', '1'),
        ('member(x,vector())', '0'),
        ('cardinality(vector(x))', '1'),
        ('cardinality(vector())', '0'),
        ('cardinality(vector(1,1,2))', '2'),
        ('sumset(sumset(x,vector(0,1),x),vector(2,3),x)', '2'),
    ]:
        assert evaluate(expression)['text'] == expected, expression
print(f'{checks} symbolic domain checks passed')
