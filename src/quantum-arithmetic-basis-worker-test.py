"""Arithmetic basis dimensions survive ordinary Copy and finite substitution."""

# Unchanged IBM-028-c0-math-275, notebook cell b4addac2.
# Notebook SHA256: 2ff07f29f923364ca6d47b07a36266bebe64e335cce6d50cdeed2d1cbf39af4e.
# The finite parameter/root substitutions below are explicit adaptations.
SOURCE = r'''$$
\begin{aligned}
\mathrm{QFT}_{2^m} \vert 2x + a\rangle
& =
\frac{1}{\sqrt{2^m}}
\sum_{y = 0}^{2^{m-1} - 1}
\sum_{b=0}^1
\omega_{2^m}^{(2x+ a)(2^{m-1}b + y)} \vert b 2^{m-1} + y\rangle\\[2mm]
& =
\frac{1}{\sqrt{2^m}}
\sum_{y = 0}^{2^{m-1} - 1}
\sum_{b=0}^1
(-1)^{ab}
\omega_{2^{m-1}}^{xy}
\omega_{2^m}^{ay}
\vert b 2^{m-1} + y\rangle.
\end{aligned}
$$'''


def check_arithmetic_copy(request):
    initial = request('source', SOURCE)
    copied = request('source-copy', initial['copy_text'], quantum=False)
    stable = request('source-stable', copied['copy_text'], quantum=False)
    assert initial['copy_text'] == copied['copy_text'] == stable['copy_text']
    for value in (initial, copied, stable):
        assert 'qcomputationalket' not in value['copy_text']
        assert 'qequalchain' in value['copy_text']
        assert 'qequalchain' not in value['display_text']
        assert value['approximate'] is False
    witnesses = 0
    for phase, value in [('initial', initial), ('copy', copied)]:
        for m, x, a in [(1, 0, 0), (1, 0, 1), (2, 0, 0), (2, 0, 1), (2, 1, 0), (2, 1, 1)]:
            roots = [("'ω_2'", '-1'), ("'ω_1'", '1')] if m == 1 else [("'ω_4'", 'i'), ("'ω_2'", '-1')]
            expression = value['copy_text']
            for key, replacement in [("'m'", str(m)), ('x', str(x)), ("'a'", str(a))] + roots:
                expression = 'qreplace((' + expression + '),' + key + ',' + replacement + ')'
            response = request(phase + str((m, x, a)), expression, quantum=False)
            assert response['copy_text'] == '1' and response['approximate'] is False, response
            witnesses += 1
    for name, expression, descriptor in [
        ('pending', '|2x+1>', 'qcomputationalket'),
        ('huge', 'fourier(10^12)|2x+1>', 'qadjacent(qfourier('),
    ]:
        initial = request(name, expression)
        copied = request(name + '-copy', initial['copy_text'], quantum=False)
        for value in (initial, copied):
            assert descriptor in value['copy_text'], value
            assert value['rows'] == 0 and value['columns'] == 0 and value['cells'] == [], value
            assert value['approximate'] is False
            if name == 'huge':
                assert 'qbasis(qadd(qadjacent(2,x),1),1000000000000)' in value['copy_text'], value
                assert 'qcomputationalket' not in value['copy_text']
        assert initial['copy_text'] == copied['copy_text']
    return witnesses


if __name__ == '__main__':
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys

    worker = Path(sys.argv[1] if len(sys.argv) > 1 else 'quantum-worker' + ('.exe' if os.name == 'nt' else '')).resolve()

    def request(name, expression, quantum=True):
        result = subprocess.run([str(worker), '--json'], input=(('quantum:' if quantum else '') + expression).encode('utf-8'), capture_output=True, timeout=60)
        assert len(result.stdout) + len(result.stderr) <= 1048576
        assert result.returncode == 0 and not result.stderr, (name, result.returncode, result.stderr)
        return json.loads(result.stdout)

    print('Arithmetic basis exact witnesses:', check_arithmetic_copy(request))
