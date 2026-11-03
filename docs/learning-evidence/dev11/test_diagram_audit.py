"""Adversarial checks of the audit comparator using the actual native adapter."""
import argparse
import copy
import importlib.util
import json
import os
from pathlib import Path

spec=importlib.util.spec_from_file_location('diagram',Path(__file__).with_name('diagram-audit.py'))
diagram=importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagram)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--native',type=Path,required=True)
    parser.add_argument('--toolchain',type=Path,required=True)
    args=parser.parse_args()
    base=next(c for c in diagram.fixtures() if c['id']=='repetition-encoder-i')
    cases=[copy.deepcopy(base) for _ in range(4)]
    cases[1]['operations'][-1]=('CNOT',2,0)  # control/target reversal
    cases[2]['expected'][1][2]*=-1           # relative phase, same probabilities
    cases[3]['operations'].append(('X',1)) # leakage out of the code space
    for case,name in zip(cases,('control','reversed-wire','relative-phase','leakage')):
        case['id']=name
    env=dict(os.environ,PATH=str(args.toolchain)+os.pathsep+os.environ['PATH'])
    results=diagram.execute(args.native,cases,env)
    assert [r['pass'] for r in results]==[True,False,False,False],results
    assert results[3]['leakage']>0.99
    print(json.dumps({'comparator_checks':4,'pass':True,'results':results}))


if __name__=='__main__':
    main()
