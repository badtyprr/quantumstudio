"""Check Clifford error propagation and parity extraction for the illustrated circuits."""
import hashlib
import itertools
import json
from pathlib import Path
import sys


def cnot(pauli,control,target):
    x,z=pauli
    return x ^ ((x>>control & 1)<<target), z ^ ((z>>target & 1)<<control)


def run(pauli,gates):
    for c,t in gates:
        pauli=cnot(pauli,c,t)
    return pauli


def span(rows):
    words={0}
    for v in rows:
        words |= {u^v for u in words}
    return words


def main():
    directory=Path(sys.argv[1])
    summary={}
    def record(stem,**results):
        data=(directory/(stem+".svg")).read_bytes()
        summary[stem]=dict(sha256=hashlib.sha256(data).hexdigest(),**results)
    for size,name in ((2,"CNOT-error-propagation"),(4,"multiple-CNOT-error-propagation")):
        pairs=[(0,j) for j in range(1,size)]
        assert run((1,0),pairs)==((1<<size)-1,0)
        assert run((0,1),[(t,c) for c,t in pairs])==(0,(1<<size)-1)
        record(name,propagated_x_weight=size,propagated_z_weight=size)
    pairs=list(zip(range(5),range(5,10)))
    for block in (0,1):
        for wire in range(5):
            bit=1<<(wire+5*block)
            for before in [(bit,0),(0,bit),(bit,bit)]:
                after=run(before,pairs)
                support=after[0]|after[1]
                assert support & ~((1<<wire)|(1<<(wire+5)))==0
    record("transversal-CNOT",pairs=5,single_pauli_errors_checked=30)
    # Three cat-state controls accumulate the eigenvalue of the Pauli product.
    for signs in itertools.product((-1,1),repeat=3):
        parity=sum(s<0 for s in signs)%2
        assert (-1)**parity==signs[0]*signs[1]*signs[2]
    record("Shor-error-detection",ancillas=3,sign_patterns=8)
    # The dual Hamming code has zero syndrome. Transversal readout transfers a
    # data error to the ancilla word, preserving its classical syndrome.
    checks=(0b1111000,0b1100110,0b1010101)
    def syndrome(word):
        return tuple((word & row).bit_count()%2 for row in checks)
    assert len(set(syndrome(1<<i) for i in range(7)))==7
    for ancilla,error in itertools.product(span(checks),range(128)):
        assert syndrome(ancilla^error)==syndrome(error)
    record("Steane-error-detection",qubits_per_block=7,ancilla_error_pairs=1024)
    print(json.dumps(summary,indent=2))

if __name__=="__main__":
    main()
