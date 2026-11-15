"""Tensor coefficients, ordinary Copy and deferred scalar/operator substitution."""


def check_tensor_chain(request):
    outcomes = []
    for name, expression in [
        ('coefficient', 'norm((|0> @ (1/2)|0>)-([1;0;0;0]/2))'),
        ('grouped', 'norm((|0> @ ((1/2)|0>))-([1;0;0;0]/2))'),
        ('gate-application', 'norm((H @ H |00>)-([1;1;1;1]/2))'),
        ('unresolved-state', 'tensor(|psi>,|0>)'),
        ('unresolved-type', 'H @ x |00>'),
        ('unresolved-coefficient', '|psi> @ (1/2)|0>'),
        ('tex-coefficient', r'norm((\ket{0}\otimes\frac{1}{2}\ket{0})-([1;0;0;0]/2))'),
    ]:
        original = request(name, expression)
        assert not original['approximate'], name
        if not name.startswith('unresolved-'):
            assert original['copy_text'] == '0', (name, original)
        if name in ('unresolved-type', 'unresolved-coefficient'):
            copied = request(name + '-reentry', original['copy_text'], quantum=False)
            stable = request(name + '-stable', copied['copy_text'], quantum=False)
            # An evaluated matrix is first copied as a literal. Ordinary
            # reentry retains its matrix constructor with vector entries.
            # Permit exactly that normalization, then require stable Copy.
            if name == 'unresolved-type':
                expected = original['copy_text'].replace('matrix(2,2,[', 'matrix(2,2,vector(', 1).replace(']),vector(x', ')),vector(x', 1)
            else:
                expected = original['copy_text'].replace('matrix(2,1,[', 'matrix(2,1,vector(', 1).replace(']))', ')))', 1)
            assert copied['copy_text'] == expected, (name, original, copied)
            assert stable['copy_text'] == copied['copy_text'], name
            assert original['display_text'] == copied['display_text'] == stable['display_text'], name
            for value in (original, copied, stable):
                assert not value['approximate'] and value['rows'] == 0 and value['columns'] == 0 and value['cells'] == [], (name, value)
                assert '⊗' in value['display_text'] and 'qtensorchain' not in value['display_text'], (name, value)
            if name == 'unresolved-type':
                for phase, value in [('initial', original), ('reentry', copied)]:
                    for label, replacement, reference in [
                        ('scalar', '2', 'tensor(H,2|00>)'),
                        ('gate', 'H', '[1;1;1;1]/2'),
                    ]:
                        delta = '(replace((' + value['copy_text'] + '),x,' + replacement + ')-(' + reference + '))'
                        # The gate case is a column; the scalar case is an
                        # 8-by-2 matrix and needs the full Frobenius norm.
                        comparison = 'qnorm(' + delta + ')' if label == 'gate' else 'qtrace(qmul(qdag(' + delta + '),' + delta + '))'
                        checked = request(name + '-' + phase + '-' + label, comparison)
                        assert checked['copy_text'] == '0' and not checked['approximate'], (phase, label, checked)
        outcomes.append(dict(name=name, passed=True))
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
        assert len(result.stdout) + len(result.stderr) <= 1048576, name
        return json.loads(result.stdout)

    print('Tensor chain worker outcomes:', len(check_tensor_chain(request)))
