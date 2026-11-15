"""Presentation and unchanged ordinary Copy for deferred indexed expressions.

The bounded worker harness supplies request(name, expression, quantum=True).
"""


def check_display(request):
    cases = [
        ('dot', 'qscalarproductsum("x_","y_",n,vector())', ['∑_', 'x_', 'y_']),
        ('dot-assigned', 'qscalarproductsum("x_","y_",n,vector(0,0,1))', ['component assignments:', 'x_0 = 1']),
        ('series', 'qtensorseries(qbasis(0,2),0,n-1,k,1)', ['⊗_', 'step 1']),
        ('series-history', 'replace(qtensorseries(qbasis(x_k,2),0,n-1,k,1),x_0,1)', ['⊗_', 'body substitutions, in order:']),
        ('wide-domain', 'qbitstrings(64)', ['nonnegative integer width', '64']),
        # Evaluation may simplify this to 2^(n/2); the native printer test
        # separately checks an unevaluated square-root node.
        ('root', 'qsqrt(qpower(2,n))', ['2^', 'n']),
    ]
    outcomes = []
    for name, expression, expected in cases:
        original = request('display-' + name, expression)
        copied = request('display-' + name + '-reentry', original['copy_text'], quantum=False)
        for result in (original, copied):
            text = result['display_text']
            assert all(part in text for part in expected), (name, text)
            assert not any(part in text for part in ('qscalarproductsum', 'qtensorseries', 'qboundtensorseries', 'qbitstrings', 'qsqrt', 'qpower')), (name, text)
        assert original['copy_text'] == copied['copy_text'], name
        assert original['display_text'] == copied['display_text'], name
        outcomes.append(dict(name=name, passed=True, display=original['display_text']))
    return outcomes


if __name__ == '__main__':
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys

    worker = Path(sys.argv[1] if len(sys.argv) > 1 else 'quantum-worker' + ('.exe' if os.name == 'nt' else '')).resolve()

    def request(name, expression, quantum=True):
        result = subprocess.run([str(worker), '--json'], input=(('quantum:' if quantum else '') + expression).encode('utf-8'), capture_output=True, timeout=60)
        assert result.returncode == 0 and not result.stderr, (name, result.returncode, result.stderr)
        assert len(result.stdout) <= 1048576, name
        return json.loads(result.stdout)

    outcomes = check_display(request)
    print('Indexed display worker pairs:', len(outcomes))
