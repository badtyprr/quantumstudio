"""Finite IBM-063 L=3 adaptation; independent geometric and Pauli-letter oracles.

The original source illustrates L=9. This audit does not certify that figure,
general L, a decoder, or whole-source coverage. All arithmetic here is exact.
"""
import argparse
import hashlib
import itertools
import json
import os
from pathlib import Path
import re
import subprocess


def fixtures():
    def h(x, y): return 3*(y % 3)+x % 3
    def v(x, y): return 9+h(x, y)
    def label(letter, sites):
        return ''.join(letter if q in sites else 'I' for q in range(18))
    stars = [label('X', {h(x,y), h(x-1,y), v(x,y), v(x,y-1)})
             for y in range(3) for x in range(3)]
    faces = [label('Z', {h(x,y), h(x,y+1), v(x,y), v(x+1,y)})
             for y in range(3) for x in range(3)]
    checks = stars+faces
    # Enumerate the generated binary group independently of Gaussian
    # elimination. Exactly 65536 elements means rank 16 and two relations.
    encoded=[(int(''.join('1' if c in 'XY' else '0' for c in g),2)<<18)
             |int(''.join('1' if c in 'ZY' else '0' for c in g),2) for g in checks]
    span={0}
    for generator in encoded: span |= {word^generator for word in span}
    assert len(span)==65536
    def cp(word): return 'compact_pauli("'+word+'")'
    group = 'vector('+','.join(map(cp, checks))+')'
    def anti(a, b):
        return sum(x != y and x != 'I' and y != 'I' for x,y in zip(a,b)) % 2
    # Independent exhaustive lower bound: every weight-one/two Pauli has a
    # nonzero syndrome. No stabilizer membership algorithm is used here.
    lower_bound_count = 0
    for weight in (1,2):
        for sites in itertools.combinations(range(18), weight):
            for letters in itertools.product('XYZ', repeat=weight):
                word = ['I']*18
                for site, letter in zip(sites, letters): word[site] = letter
                assert any(anti(word, g) for g in checks)
                lower_bound_count += 1
    loops = [label('Z', {h(x,0) for x in range(3)}),
             label('Z', {v(0,y) for y in range(3)}),
             label('X', {h(0,y) for y in range(3)}),
             label('X', {v(x,0) for x in range(3)})]
    for loop in loops: assert not any(anti(loop,g) for g in checks)
    assert anti(loops[0],loops[2]) and anti(loops[1],loops[3])
    # Each weight-three loop anticommutes with a normalizer loop, so cannot
    # be a stabilizer. Combined with the exhaustive lower bound: distance 3.
    cases=[]
    def add(name, expression, expected):
        cases.append(dict(id=name, expression='quantum:'+expression, expected=expected))
    add('18-qubit-value',cp('X'+'I'*17),[18,131072,0,0])
    add('exact-Y-phase',cp('-iY'+'I'*17),[18,131072,131072,2])
    for a,g in enumerate(checks):
        for b,k in enumerate(checks):
            add(f'commute-{a}-{b}','compact_commutes('+cp(g)+','+cp(k)+')',1)
    for name,family in [('stars',stars),('faces',faces)]:
        expression=cp('I'*18)
        for word in family: expression='compact_multiply('+expression+','+cp(word)+')'
        add(name+'-dependency',expression,[18,0,0,0])
    add('rank','compact_rank('+group+')',16)
    add('dimension','compact_dimension('+group+')',4)
    add('distance','compact_distance('+group+',3)',3)
    for site in range(18):
        for letter in 'XYZ':
            word=label(letter,{site})
            add(f'syndrome-{site}-{letter}','compact_syndrome('+group+','+cp(word)+')',
                [anti(word,g) for g in checks])
    for a,loop in enumerate(loops):
        add(f'logical-{a}-syndrome','compact_syndrome('+group+','+cp(loop)+')',[0]*18)
        for b,other in enumerate(loops):
            add(f'logical-{a}-{b}','compact_commutes('+cp(loop)+','+cp(other)+')',1-anti(loop,other))
    return cases, dict(stars=stars,faces=faces,logical_loops=loops,
                      exhaustive_weight_one_two=lower_bound_count,
                      independently_enumerated_group_size=len(span),independent_relations=2)


def parse_integer_result(text):
    text=text.strip()
    if re.fullmatch(r'-?\d+',text): return int(text)
    match=re.fullmatch(r'vector\(\s*(-?\d+(?:\s*,\s*-?\d+)*)\s*\)',text)
    if not match: raise ValueError('Unexpected exact integer result: '+text)
    return [int(x) for x in match[1].split(',')]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--worker',type=Path,required=True)
    parser.add_argument('--sources',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    args.output.mkdir(parents=True,exist_ok=False)
    manifest=json.loads(Path(__file__).with_name('source-manifest.json').read_text(encoding='utf-8'))
    source=next(x for x in manifest if x['id']=='IBM-063')
    notebook=args.sources/'IBM-063.ipynb'
    assert hashlib.sha256(notebook.read_bytes()).hexdigest()==source['notebook']['sha256']
    source_map=json.loads(Path(__file__).with_name('source-map.json').read_text(encoding='utf-8'))
    locations=next(x for x in source_map if x['id']=='IBM-063')
    cases,oracle=fixtures()
    provenance=dict(worker=str(args.worker.resolve()),worker_sha256=hashlib.sha256(args.worker.read_bytes()).hexdigest(),
                    source=source,locations=locations,oracle=oracle,mode='fresh execution',tolerance=None)
    (args.output/'provenance.json').write_text(json.dumps(provenance,indent=2),encoding='utf-8')
    (args.output/'fixtures.json').write_text(json.dumps(cases,indent=2),encoding='utf-8')
    results=[]
    env=dict(os.environ,QALCULATE_DEFINITIONS_DIR=str(args.worker.resolve().parent/'data'))
    try:
        for case in cases:
            run=subprocess.run([str(args.worker.resolve()),'--json'],input=case['expression'].encode(),
                               capture_output=True,env=env,timeout=30)
            record=dict(id=case['id'],returncode=run.returncode,stdout=run.stdout.decode(),stderr=run.stderr.decode())
            results.append(record)
            assert run.returncode==0 and not run.stderr,record
            result=json.loads(run.stdout)
            assert result['approximate'] is False,record
            assert parse_integer_result(result['copy_text'])==case['expected'],record
            # Exercise the actual serialized calculator output, not a rebuilt
            # expected expression. Keep the complete second result as evidence.
            replay=subprocess.run([str(args.worker.resolve()),'--json'],input=('quantum:'+result['copy_text']).encode(),
                                  capture_output=True,env=env,timeout=30)
            record['reentry']=dict(returncode=replay.returncode,stdout=replay.stdout.decode(),stderr=replay.stderr.decode())
            assert replay.returncode==0 and not replay.stderr,record
            second=json.loads(replay.stdout)
            assert second['approximate'] is False and parse_integer_result(second['copy_text'])==case['expected'],record
    finally:
        (args.output/'results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
    assert hashlib.sha256(args.worker.read_bytes()).hexdigest()==provenance['worker_sha256']
    print(f'PASS: {len(results)} exact compact toric results and serialized re-entries; {oracle["exhaustive_weight_one_two"]} independent lower-bound cases')


if __name__=='__main__': main()
