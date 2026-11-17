"""SDK-free source identity and independent Boolean-oracle tests.

Set QB027_ORIGINAL_SOURCE to the retained immutable notebook path.
"""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('qb027_authored_witness', ROOT/'witnesses/qb027.py')
witness = importlib.util.module_from_spec(spec)
spec.loader.exec_module(witness)


def sequential_truth_state(n, truth):
    """Separate full basis-vector gate evolution, not a Walsh character sum."""
    values = [0j] * 2**(n+1); values[0] = 1
    def h(q):
        mask = 1 << (n-q)
        for i in range(len(values)):
            if not i & mask:
                a,b = values[i],values[i|mask]
                values[i],values[i|mask] = (a+b)/math.sqrt(2),(a-b)/math.sqrt(2)
    for q in range(n): h(q)
    values[:] = [values[i^1] for i in range(len(values))]
    h(n)
    after = [0j]*len(values)
    for basis, amplitude in enumerate(values):
        after[basis ^ truth[basis >> 1]] = amplitude
    values[:] = after
    for q in range(n): h(q)
    return values


class QB027Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads((ROOT/'contracts/qb027.json').read_bytes())
        cls.original=Path(os.environ['QB027_ORIGINAL_SOURCE']).read_bytes()
        cls.notebook=json.loads(cls.original)

    def test_original_file_and_all_ten_cells(self):
        self.assertEqual(hashlib.sha256(self.original).hexdigest(),self.contract['source']['sha256'])
        self.assertEqual(len(self.notebook['cells']),10)
        for i,(cell,record) in enumerate(zip(self.notebook['cells'],self.contract['source']['cells'])):
            self.assertEqual(record,dict(index=i,type=cell['cell_type'],
                sha256=hashlib.sha256(''.join(cell['source']).encode()).hexdigest()))
        self.assertEqual(len(self.contract['source']['cells']),10)

    def test_exact_selected_boundary(self):
        self.assertEqual(self.contract['route'],'selected-cells/direct-native-execution')
        self.assertEqual(self.contract['selected_cells'],[6]);self.assertEqual(self.contract['code_cells'],[6])
        self.assertEqual(set(self.contract['excluded_code_cells']),{'1','3','4','7','8'})
        self.assertEqual(sum(c['cell_type']=='markdown' for c in self.notebook['cells']),4)
        self.assertIsNone(self.contract['preamble'])
        self.assertEqual(self.contract['profile'],'qir-win-py312')

    def test_witness_hash_and_syntax(self):
        raw=(ROOT/'witnesses/qb027.py').read_text(encoding='utf-8').encode()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),self.contract['witness']['sha256'])
        compile(raw,'authored-witness','exec')

    def test_finite_case_table(self):
        cases=witness.finite_cases()
        self.assertEqual(len(cases),14);self.assertEqual(len({r[0] for r in cases}),14)
        self.assertEqual([n for _,n,_ in cases],[2]*12+[3]*2)
        self.assertEqual({tuple(t) for _,_,t in cases[:8]},
            {(0,0,0,0),(1,1,1,1),(0,0,1,1),(0,1,0,1),(0,1,1,0),
             (1,0,0,1),(1,0,1,0),(1,1,0,0)})

    def test_walsh_against_independent_sequential_gates(self):
        for label,n,truth in witness.finite_cases():
            with self.subTest(case=label):
                expected=witness.walsh_state(truth);actual=sequential_truth_state(n,truth)
                self.assertLess(max(abs(a-b) for a,b in zip(actual,expected)),1e-14)
                self.assertAlmostEqual(sum(abs(a)**2 for a in expected),1)
                support=[y for y in range(2**n) if abs(expected[2*y])>1e-12]
                self.assertEqual(len(support),1)
                if label.startswith('bv_'):self.assertEqual(support,[int(label[3:],2)])
                elif sum(truth) in (0,len(truth)):self.assertEqual(support,[0])
                else:self.assertNotEqual(support,[0])

    def test_global_phase_and_order_mutations_are_detectable(self):
        zero=witness.walsh_state([0]*4);one=witness.walsh_state([1]*4)
        self.assertEqual(one,[-v for v in zero])
        cases={label:(n,t) for label,n,t in witness.finite_cases()}
        a=witness.walsh_state(cases['bv_001'][1]);b=witness.walsh_state(cases['bv_100'][1])
        self.assertGreater(max(abs(x-y) for x,y in zip(a,b)),.7)

    def test_truth_validation(self):
        for bad in ([],[0],[0,1,0],[0,True],[0,2],[0,0.0]):
            with self.subTest(value=bad),self.assertRaises(AssertionError):witness.walsh_state(bad)

    def test_count_validation(self):
        witness.check_counts({'00':2048,'11':2048},4096,2,{'00','11'})
        for bad in ({},{'00':4095},{'0':4096},{'02':4096},{'01':4096},
                    {'00':4096.0},{'00':True},{'00':-1,'11':4097}):
            with self.subTest(value=bad),self.assertRaises(AssertionError):
                witness.check_counts(bad,4096,2,{'00','11'})

    def test_nonfinite_state_rejected_before_residual(self):
        self.assertEqual(witness.state_residual([1,0],[1,0]),0)
        for bad in (float('nan'),float('inf'),-float('inf'),complex(0,float('nan'))):
            for index in (0,1):
                values=[1,0];values[index]=bad
                with self.subTest(bad=bad,index=index):
                    with self.assertRaisesRegex(AssertionError,'STATE_NONFINITE'):
                        witness.state_residual(values,[1,0])
                    with self.assertRaisesRegex(AssertionError,'STATE_NONFINITE'):
                        witness.state_residual([1,0],values)
        with self.assertRaisesRegex(AssertionError,'STATE_AMPLITUDES'):
            witness.state_residual([0,1],[1,0])

    def test_predeclared_shots_and_bound(self):
        self.assertEqual(witness.BELL_SHOTS,4096);self.assertEqual(witness.ALGORITHM_SHOTS,128)
        self.assertEqual(witness.BELL_FREQUENCY_TOLERANCE,.05)
        self.assertLess(4*math.exp(-2*4096*.05**2),1e-8)
        self.assertEqual(witness.STATE_TOLERANCE,1e-12)


if __name__=='__main__':unittest.main(verbosity=2)
