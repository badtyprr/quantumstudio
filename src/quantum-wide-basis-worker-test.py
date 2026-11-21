"""Actual ordinary Copy and exact finite witnesses for deferred wide states."""


def check_wide_copy(request, rejected):
    outcomes = []
    for name, expression, descriptor in [
        ('basis', 'qbasis(1024,1025)', 'qbasis'),
        ('huge-basis', 'qbasis(999999999999,10^12)', 'qbasis'),
        ('fourier', 'qfourier(65)', 'qfourier'),
        ('huge-fourier', 'qfourier(10^12)', 'qfourier'),
        ('qft', 'qft(7)', 'qft'),
        ('huge-qft', 'qft(10^12)', 'qft'),
    ]:
        initial = request(name + '-initial', expression)
        copied = request(name + '-reentry', initial['copy_text'], quantum=False)
        for value in (initial, copied):
            assert descriptor in value['copy_text'], (name, value)
            assert not value['approximate'] and value['rows'] == 0 and value['columns'] == 0 and value['cells'] == [], (name, value)
        assert initial['copy_text'] == copied['copy_text'], name
        outcomes.append(dict(name=name, passed=True, copy=copied['copy_text']))
    for name, expression, substitutions, expected in [
        ('symbolic-basis', 'qbasis(x,n)', [('n', '4'), ('x', '1')], '[0;1;0;0]'),
        ('symbolic-action', 'qfourier(n)*qbasis(1,n)', [('n', '4')], '[1;i;-1;-i]/2'),
        ('symbolic-qft', 'qft(n)', [('n', '2')], '[1,1,1,1;1,i,-1,-i;1,-1,1,-1;1,-i,-1,i]/2'),
    ]:
        initial = request(name + '-initial', expression)
        copied = request(name + '-reentry', initial['copy_text'], quantum=False)
        bound = copied['copy_text']
        for key, value in substitutions:
            bound = 'replace(' + bound + ',' + key + ',' + value + ')'
        delta = '((' + bound + ')-(' + expected + '))'
        # qnorm is a column-ket norm. For the full Fourier matrix, use the
        # squared Frobenius norm so every entry contributes to the oracle.
        comparison = 'qtrace(qmul(qdag(' + delta + '),' + delta + '))' if name == 'symbolic-qft' else 'norm(' + delta + ')'
        difference = request(name + '-reference', comparison)
        assert all(difference[key] == '0' for key in ('text', 'display_text', 'copy_text')), (name, difference)
        assert not difference['approximate'] and difference['rows'] == 0 and difference['columns'] == 0 and difference['cells'] == [], name
        outcomes.append(dict(name=name, passed=True, reference=expected))
    for index, expression in enumerate([
        'qbasis(1025,1025)', 'qfourier(0)', 'qft(-1)', 'qfourier(1/2)',
        'qmul(qfourier(65),qbasis(0,66))', 'qfourierdomain([1;0],0,65)',
    ]):
        rejected('invalid-' + str(index), expression)
        outcomes.append(dict(name='invalid-' + str(index), passed=True))
    return outcomes


if __name__ == '__main__':
    import json
    import os
    from pathlib import Path
    import subprocess
    import sys

    worker = Path(sys.argv[1] if len(sys.argv) > 1 else 'quantum-worker' + ('.exe' if os.name == 'nt' else '')).resolve()

    def run(expression, quantum=True):
        result = subprocess.run([str(worker), '--json'], input=(('quantum:' if quantum else '') + expression).encode('utf-8'), capture_output=True, timeout=60)
        assert len(result.stdout) + len(result.stderr) <= 1048576
        return result

    def request(name, expression, quantum=True):
        result = run(expression, quantum)
        assert result.returncode == 0 and not result.stderr, (name, result.returncode, result.stderr)
        return json.loads(result.stdout)

    def rejected(name, expression):
        result = run(expression)
        assert result.returncode == 2 and not result.stdout and result.stderr, (name, result.returncode, result.stdout, result.stderr)

    register = request("Hadamard register", r"$H^{\otimes n}|0\rangle$")["copy_text"]
    assert request("copied register", register)["copy_text"] == register
    for width in (1, 2, 3):
        size = 2**width
        amplitudes = ",".join([f"1/sqrt({size})"]*size)
        compare = f'qcompare(replace({register},"n",{width}),matrix({size},1,[{amplitudes}]),4)'
        assert request("all amplitudes", compare)["copy_text"] == "1"
    flipped = request("bit-flipped register", r"$X^{\otimes 2}|0\rangle$")["copy_text"]
    assert request("bit order", f"qcompare({flipped},[0;0;0;1],4)")["copy_text"] == "1"
    assert request("wrong ket", f"qcompare({flipped},[1;0;0;0],4)")["copy_text"] == "0"
    diffusion = request("diffusion", r"$D=2|\psi\rangle\langle\psi|-I$")["copy_text"]
    assert request("copied diffusion operator", diffusion)["copy_text"] == diffusion

    reflection = request("phase oracle reflection",
        r"$$Z_{\mathrm{OR}} = 2 \vert 0^n \rangle \langle 0^n \vert - \mathbb{I}.$$")["copy_text"]
    assert request("copied reflection", reflection)["copy_text"] == reflection
    for width in (1, 2, 3):
        dimension = 2**width
        for sign, expected in ((1, "1"), (-1, "0")):
            entries = [str(sign*(1 if row == 0 else -1)) if row == col else "0"
                       for row in range(dimension) for col in range(dimension)]
            operator = f'matrix({dimension},{dimension},[{",".join(entries)}])'
            bound = f'replace({reflection},vector("Z_OR","n"),vector({operator},{width}))'
            assert request("bound oracle", bound)["copy_text"] == expected

    print('Wide basis worker outcomes:', len(check_wide_copy(request, rejected)))
