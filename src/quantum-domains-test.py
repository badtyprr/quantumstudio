#!/usr/bin/env python3
"""DEV-10 equality fixtures; references/adaptations in learning-evidence/DEV-10.md."""
import json
import subprocess
import sys

worker = sys.argv[1]
checks = 0

def evaluate(expression):
    global checks
    result = subprocess.run([worker, '--json'], input=('quantum: '+expression).encode(), capture_output=True, timeout=30)
    assert result.returncode == 0, (expression, result.stderr.decode())
    checks += 1
    return json.loads(result.stdout)

for flags in ['']:
    for expression in ['member(x,S)', 'member(x,vector(y))',
                       'cardinality(vector(x,y))', 'sumset(k,vector(x,y),k)']:
        value = evaluate(expression)
        assert value['text'] not in ['0', '1', '2', 'x + y'], (expression, value)
        # Serialization is executable, and retains the same unresolved condition.
        copied = evaluate(value['copy_text'])
        assert copied == value, (expression, value, copied)
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
