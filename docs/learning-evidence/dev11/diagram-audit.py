"""Manual IBM diagram transcriptions; independent codeword/Pauli expectations.

This runs an audit adapter linked to QuantumNumericalState, not IBM notebooks.
All omitted amplitudes are checked as zero. No phase fitting is used.
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from probe import parse_complex


def h(*wires):
    return [('H', q) for q in wires]


def cx(*pairs):
    return [('CNOT', a, b) for a, b in pairs]


REP = cx((0, 1), (0, 2))
PHASE = REP + h(0, 1, 2)
INNER = cx((0, 1), (3, 4), (6, 7), (0, 2), (3, 5), (6, 8))
SHOR = cx((0, 3), (0, 6)) + h(0, 3, 6) + INNER
STEANE = (cx((0, 1)) + h(4, 5, 6) + cx((0, 2), (6, 3), (6, 1),
          (6, 0), (5, 3), (5, 2), (5, 0), (4, 3), (4, 2), (4, 1)))
BIT_CHECK = cx((0, 3), (1, 3), (1, 4), (2, 4))
PHASE_CHECK = h(3, 4) + cx((3, 0), (3, 1), (4, 1), (4, 2)) + h(3, 4)
PHASE_LONG = h(0, 1, 2) + BIT_CHECK + h(0, 1, 2)
SHOR_CHECK = h(9, 10) + cx(*[(9, q) for q in range(6)],
                          *[(10, q) for q in range(3, 9)]) + h(9, 10)
SHOR_LONG = (list(reversed(INNER)) + h(9, 10) +
             cx((9, 0), (9, 3), (10, 3), (10, 6)) + INNER + h(9, 10))
ENCODERS = {'repetition': (3, REP, 'repetition-encoder.svg'),
            'phase': (3, PHASE, 'repetition-encoder-modified.svg'),
            'shor': (9, SHOR, 'Shor-encoder.svg'),
            'steane': (7, STEANE, 'Steane-encoder.svg')}


def codeword(family, logical):
    """Closed codeword formulas, deliberately independent of the gate lists."""
    n = ENCODERS[family][0]
    out = [0j] * (1 << n)
    if family == 'repetition':
        out[logical * 7] = 1
    elif family == 'phase':
        out = [(-1)**(logical * x.bit_count()) / math.sqrt(8) for x in range(8)]
    elif family == 'shor':
        for x in range(8):
            bits = ''.join('111' if x & (1 << b) else '000' for b in (2, 1, 0))
            out[int(bits, 2)] = (-1)**(logical * x.bit_count()) / math.sqrt(8)
    else:
        # IBM-062 dual words, reversed to the top-to-bottom IBM-060 drawing.
        for word in ('0000000', '0011110', '0101101', '0110011',
                     '1001011', '1010101', '1100110', '1111000'):
            x = int(word[::-1], 2)
            if logical:
                x ^= 0b1110000
            out[x] = 1 / math.sqrt(8)
    return out


def logical_state(family, witness):
    zero, one = codeword(family, 0), codeword(family, 1)
    if witness == '0':
        return zero
    if witness == '1':
        return one
    return [(a + 1j*b)/math.sqrt(2) for a, b in zip(zero, one)]


def prepare(witness):
    return [] if witness == '0' else [('X', 0)] if witness == '1' else [('H', 0), ('S', 0)]


def error_action(vector, gate, wire, n):
    if wire is None:
        return vector[:]
    out = [0j] * len(vector)
    mask = 1 << (n - 1 - wire)
    for i, value in enumerate(vector):
        out[i ^ mask if gate == 'X' else i] = value * (-1 if gate == 'Z' and i & mask else 1)
    return out


def with_syndrome(vector, syndrome):
    out = [0j] * (4 * len(vector))
    for i, value in enumerate(vector):
        out[4*i + syndrome] = value
    return out


def sparse(vector):
    return [[i, complex(z).real, complex(z).imag] for i, z in enumerate(vector) if z != 0]


def dense(entries, n):
    out = [0j] * (1 << n)
    for i, real, imag in entries:
        out[i] = complex(real, imag)
    return out


def fixtures():
    cases = []

    def add(name, n, ops, expected, image, **extra):
        cases.append(dict(id=name, qubits=n, operations=ops, expected=sparse(expected),
                          source_image=image, adaptation='Manual transcription; top wire = numerical wire 0.', **extra))

    for family, (n, gates, image) in ENCODERS.items():
        for witness in ('0', '1', 'i'):
            add(f'{family}-encoder-{witness}', n, prepare(witness)+gates,
                logical_state(family, witness), image, round_trip=True)

    # Preserve the pink Z gate at its original location BEFORE inner encoding.
    # The larger sweep below deliberately moves errors to physical output wires.
    for check, image in ((SHOR_CHECK,'Shor-phase-error-detect-2.svg'),
                         (SHOR_LONG,'Shor-phase-error-detect-1.svg')):
        for witness in ('0','1','i'):
            ops=prepare(witness)+cx((0,3),(0,6))+h(0,3,6)+[('Z',3)]+INNER+check
            expected=with_syndrome(error_action(logical_state('shor',witness),'Z',3,9),3)
            add(image[:-4]+'-original-'+witness,11,ops,expected,image,
                expected_syndrome={'11':1},round_trip=True,
                adaptation_detail='Original pink Z before the inner encoder; terminal measurements checked by the generalized branch fixtures.')

    # Full coherent premeasurement state and actual measured/corrected branches.
    for family, checks, image in (
            ('repetition', BIT_CHECK, 'repetition-error-detection.svg'),
            ('phase', PHASE_CHECK, 'simplified-phase-error-detect.svg'),
            ('phase', PHASE_LONG, 'three-bit-modified-error-detect.svg'),
            ('shor', SHOR_CHECK, 'Shor-phase-error-detect-2.svg'),
            ('shor', SHOR_LONG, 'Shor-phase-error-detect-1.svg')):
        n, encoder, _ = ENCODERS[family]
        gate = 'X' if family == 'repetition' else 'Z'
        for error in [None] + list(range(n)):
            block = None if error is None else error//3 if family == 'shor' else error
            syndrome = 0 if block is None else (2, 3, 1)[block]
            # Classical bit 0 is first measured; numeric record reverses display order.
            record = ((syndrome >> 1) & 1) | ((syndrome & 1) << 1)
            for witness in ('0', '1', 'i'):
                encoded = logical_state(family, witness)
                damaged = error_action(encoded, gate, error, n)
                ops = prepare(witness)+encoder+([] if error is None else [(gate, error)])+checks
                tag = f'{image[:-4]}-{error}-{witness}'
                add(tag, n+2, ops, with_syndrome(damaged, syndrome), image,
                    expected_syndrome={format(syndrome, '02b'): 1}, round_trip=witness == 'i')
                correction = [('M', n, 0, 0.37), ('M', n+1, 1, 0.61)]
                for b, value in enumerate((1, 3, 2)):
                    correction.append(('F', b*3 if family == 'shor' else b, 3, value, gate))
                add(tag+'-recovered', n+2, ops+correction,
                    with_syndrome(encoded, syndrome), image, expected_record=record,
                    adaptation_detail='Conditional corrections from source prose/table, absent from detection-only drawing.')

    # A coherent error produces two ancilla outcomes. Compare complete joint states,
    # then both native measurement branches and recovery on the complex logical state.
    for family, check, image in [('repetition', BIT_CHECK, 'repetition-error-detection.svg'),
                                  ('phase', PHASE_CHECK, 'simplified-phase-error-detect.svg')]:
        n, encoder, _ = ENCODERS[family]
        gate = 'X' if family == 'repetition' else 'Z'
        encoded = logical_state(family, 'i')
        damaged = error_action(encoded, gate, 0, n)
        # H Z H? Instead use H on error wire: (X+Z)/sqrt(2), whose branches
        # have independent Pauli expectations and expose non-correctable components.
        xpart = error_action(encoded, 'X', 0, n)
        zpart = error_action(encoded, 'Z', 0, n)
        sx, sz = (2, 0) if family == 'repetition' else (0, 2)
        expected = [(a+b)/math.sqrt(2) for a,b in zip(with_syndrome(xpart,sx),with_syndrome(zpart,sz))]
        ops = prepare('i')+encoder+[('H',0)]+check
        add(f'{family}-coherent-error', 5, ops, expected, image,
            expected_syndrome={'00':0.5,'10':0.5}, adaptation_detail='H error is an explicit audit adaptation, not a pictured source gate.')
        for draw, syn, part in ((0.1,0,zpart if family=='repetition' else xpart),
                                (0.9,2,xpart if family=='repetition' else zpart)):
            recovered = error_action(part,gate,0,n) if syn else part
            add(f'{family}-coherent-branch-{syn}',5,
                ops+[('M',3,0,draw),('M',4,1,0.5),('F',0,3,1,gate)],
                with_syndrome(recovered,syn),image,expected_record=1 if syn else 0,
                adaptation_detail='Branch 00 retains the uncorrectable logical component; recovery is not claimed for H.')
    return cases


def execute(executable, cases, env):
    request = ''.join(f"{c['qubits']} {len(c['operations'])}\n" +
                      '\n'.join(' '.join(map(str, op)) for op in c['operations'])+'\n' for c in cases)
    run = subprocess.run([str(executable)], input=request, text=True, capture_output=True, env=env, timeout=180)
    if run.returncode:
        raise RuntimeError(run.stderr)
    results = [json.loads(line) for line in run.stdout.splitlines()]
    if len(results) != len(cases):
        raise ValueError('Native result count mismatch')
    for case, actual in zip(cases, results):
        got, want = dense(actual['amplitudes'],case['qubits']), dense(case['expected'],case['qubits'])
        residual = max(abs(a-b) for a,b in zip(got,want))
        actual.update(id=case['id'], max_amplitude_error=residual,
                      leakage=sum(abs(a)**2 for a,b in zip(got,want) if b==0))
        actual['pass'] = residual < 1e-12 and abs(actual['norm']-1) < 1e-12
        if 'expected_record' in case:
            actual['pass'] &= actual['record'] == case['expected_record']
        if 'expected_syndrome' in case:
            dist = {format(s,'02b'):sum(abs(z)**2 for i,z in enumerate(got) if i%4==s) for s in range(4)}
            actual['syndrome_distribution'] = dist
            actual['pass'] &= all(abs(p-case['expected_syndrome'].get(s,0)) < 1e-12 for s,p in dist.items())
    return results


def main():
    ap=argparse.ArgumentParser()
    for arg in ('native','exporter','helper','sources','media','output','toolchain'):
        ap.add_argument('--'+arg,type=Path,required=True)
    args=ap.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    manifests=json.loads((HERE/'source-manifest.json').read_text())
    for row in manifests:
        assert hashlib.sha256((args.sources/(row['id']+'.ipynb')).read_bytes()).hexdigest()==row['notebook']['sha256']
    media=json.loads((HERE/'diagram-media.json').read_text())
    for row in media:
        assert hashlib.sha256((args.media/row['file']).read_bytes()).hexdigest()==row['sha256']
    env=dict(os.environ,PATH=str(args.toolchain)+os.pathsep+os.environ['PATH'])
    cases=fixtures()
    by_image={row['file']:row for row in media}
    by_row={row['id']:row for row in manifests}
    for case in cases:
        asset=by_image[case['source_image']]
        source=by_row[asset['row']]
        notebook=json.loads((args.sources/(asset['row']+'.ipynb')).read_text(encoding='utf-8'))
        cell=notebook['cells'][0]
        lines=''.join(cell['source']).splitlines()
        case.update(source_row=asset['row'],source_url=source['url'],notebook_sha256=source['notebook']['sha256'],
                    cell_index=0,cell_id=cell.get('id'),image_url=asset['url'],image_sha256=asset['sha256'],
                    image_line=next(i+1 for i,line in enumerate(lines) if asset['url'] in line))
    results=execute(args.native,cases,env)
    (args.output/'native-results.json').write_text(json.dumps(results),encoding='utf-8')
    round_cases=[]
    for case in cases:
        if not case.get('round_trip'):
            continue
        circuit={'Qubits':case['qubits'],'Steps':[{'Gate':op[0],'Angle':'','Wires':list(op[1:])} for op in case['operations']]}
        exported=subprocess.run([str(args.exporter)],input=json.dumps(circuit),text=True,capture_output=True,check=True,env=env).stdout
        imported=subprocess.run([str(args.helper)],input=exported,text=True,capture_output=True,check=True,env=env,timeout=60)
        returned=json.loads(imported.stdout)
        (args.output/(case['id']+'.qasm')).write_text(exported,encoding='utf-8')
        (args.output/(case['id']+'.import.json')).write_text(imported.stdout,encoding='utf-8')
        assert returned['Qubits']==case['qubits']
        steps=returned['Steps']
        assert all(not s['Angle'] for s in steps)
        clone=dict(case,id=case['id']+'-roundtrip',operations=[(s['Gate'],*s['Wires']) for s in steps])
        round_cases.append(clone)
    round_results=execute(args.native,round_cases,env)
    provenance={name:{'path':str(path),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
                for name,path in [('native',args.native),('exporter',args.exporter),('helper',args.helper)]}
    provenance['source_revision']=subprocess.check_output(['git','rev-parse','HEAD'],cwd=HERE,text=True).strip()
    root=HERE.parents[2]
    provenance['source_files']={str(path.relative_to(root)):hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [root/'libqalculate/QuantumNumericalState.cc',root/'libqalculate/QuantumNumericalState.h',
                     root/'windows/QasmGateSerializer.cs',root/'windows/QasmAngle.cs',
                     HERE/'diagram-native.cc',HERE/'diagram-export.cs',HERE/'diagram-audit.py']}
    report={'provenance':provenance,'mode':'fresh native numerical core, tolerance 1e-12; real gate serializer and frozen importer round trip',
            'manual_cases':len(cases),'round_trip_cases':len(round_cases),'results':results+round_results}
    (args.output/'fixtures.json').write_text(json.dumps(cases+round_cases,indent=2),encoding='utf-8')
    (args.output/'results.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    failures=[r['id'] for r in report['results'] if not r['pass']]
    print(json.dumps({'manual':len(cases),'round_trip':len(round_cases),'failures':failures}))
    return bool(failures)


if __name__=='__main__':
    raise SystemExit(main())
