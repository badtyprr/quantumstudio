"""SDK-free QB030 source, profile and independent numerical checks."""
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import sys
import unittest

FROZEN_AREAS = {'area-zero': 0.0, 'area-half-pi': 1.5707963267090879, 'source-area-pi': 3.1415926534181757, 'area-two-pi': 6.2831853068363515, 'phase-half-pi': 1.5707963267090879, 'phase-asymmetric': 1.5707963267090879}

ROOT=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('qb030_authored',ROOT/'witnesses/qb030.py')
w=importlib.util.module_from_spec(spec);spec.loader.exec_module(w)


class QB030Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.contract=json.loads((ROOT/'contracts/qb030.json').read_bytes())
        cls.raw=Path(os.environ['QB030_ORIGINAL_SOURCE']).read_bytes()
        cls.notebook=json.loads(cls.raw)

    def test_all_original_identities(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(),self.contract['source']['sha256'])
        self.assertEqual(len(self.notebook['cells']),10)
        self.assertEqual(len(self.contract['source']['cells']),10)
        for i,(c,r) in enumerate(zip(self.notebook['cells'],self.contract['source']['cells'])):
            self.assertEqual(r,dict(index=i,type=c['cell_type'],sha256=hashlib.sha256(''.join(c['source']).encode()).hexdigest()))

    def test_dispositions_and_drawing_gate(self):
        self.assertEqual(self.contract['selected_cells'],[6]);self.assertEqual(self.contract['code_cells'],[6])
        self.assertEqual(set(self.contract['excluded_code_cells']),{'1','3','4','7','8'})
        self.assertEqual(self.contract['required_images'],[6])
        self.assertEqual(self.contract['route'],'selected-cells/direct-native-execution')
        self.assertIsNone(self.contract['preamble'])

    def test_observed_profile_and_exact_lock(self):
        profile=json.loads((ROOT/'profiles/pulser-win-py312.json').read_bytes())
        raw=(ROOT/'pulser-requirements.lock').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),profile['lock_sha256'])
        self.assertEqual(profile['lock_sha256'],'b04970f6b9552e416caaea4270d7da93089444c527076c2d4f83a61b641f6502')
        self.assertEqual(len(raw.decode().splitlines()),49)
        self.assertEqual((profile['python'],profile['architecture'],profile['platform']),('3.12.10','64bit','win32'))
        self.assertTrue(profile['exact_packages']);self.assertTrue(profile['offline_only'])

    def test_witness_identity_and_no_sdk_import(self):
        raw=(ROOT/'witnesses/qb030.py').read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),self.contract['witness']['sha256'])
        self.assertNotIn('pulser',sys.modules);self.assertNotIn('qutip',sys.modules)
        compile(raw,'authored-witness','exec')

    def test_fixed_case_solver_table(self):
        self.assertEqual([c[0] for c in w.CASES],['source-area-pi','area-zero','area-half-pi','phase-half-pi','phase-asymmetric'])
        self.assertEqual(len(w.CASES)*len(w.SOLVERS),10)
        self.assertEqual(w.SOLVERS,[dict(method='adams',atol=1e-10,rtol=1e-9,max_step=.001,nsteps=1000000,store_states=True),dict(method='adams',atol=1e-12,rtol=1e-11,max_step=.0005,nsteps=1000000,store_states=True)])
        self.assertEqual((w.SAMPLE_TOL,w.AREA_TOL,w.MODEL_AREA_TOL,w.STATE_TOL,w.NORM_TOL,w.CONVERGENCE_TOL),(1e-10,1e-10,1e-7,1e-5,1e-8,1e-7))

    def test_reference_samples_and_cubic_areas(self):
        for name,area,phase in w.CASES+[('area-two-pi',2*math.pi,0.)]:
            with self.subTest(case=name):
                values=w.samples(area);coeff,cubic=w.spline(values+[0.])
                self.assertEqual(len(values),1000);self.assertEqual(len(coeff),1000)
                self.assertLess(abs(math.fsum(values)*.001-area),1e-12)
                self.assertLess(abs(cubic-FROZEN_AREAS[name]),1e-12)
                self.assertLess(abs(cubic-area),1e-7)
                self.assertLess(max(abs(a-b) for a,b in zip(values,reversed(values))),1e-12)

    def test_not_a_knot_polynomial_oracle(self):
        for degree in range(4):
            h=.125;coeff,area=w.spline([(i*h)**degree for i in range(9)],h)
            self.assertAlmostEqual(area,1/(degree+1),places=12)
            for i,(a,b,c,d) in enumerate(coeff):
                for fraction in (0,.17,.5,.83,1):
                    t=fraction*h
                    self.assertAlmostEqual(a+t*(b+t*(c+t*d)),((i+fraction)*h)**degree,places=12)
            self.assertAlmostEqual(coeff[0][3],coeff[1][3],places=10)
            self.assertAlmostEqual(coeff[-1][3],coeff[-2][3],places=10)

    def test_closed_state_sequential_and_special_points(self):
        for _,area,phase in w.CASES:
            r,g=0j,1+0j
            import cmath
            for omega in w.samples(area):
                c,s=math.cos(omega*.001/2),math.sin(omega*.001/2)
                r,g=c*r-1j*cmath.exp(1j*phase)*s*g,-1j*cmath.exp(-1j*phase)*s*r+c*g
            self.assertLess(w.distance([r,g],w.closed(area,phase)),1e-12)
        self.assertLess(w.distance(w.closed(math.pi,0),[-1j,0]),1e-12)
        self.assertLess(w.distance(w.closed(math.pi/2,math.pi/2),[1/math.sqrt(2)]*2),1e-12)

    def test_phase_basis_and_norm_mutations(self):
        expected=w.closed(math.pi/2,.37)
        self.assertGreater(w.density_error(expected,w.closed(math.pi/2,-.37)),.1)
        pi=w.closed(math.pi,0)
        with self.assertRaisesRegex(AssertionError,'STATE_DENSITY'):w.state_checks(pi[::-1],pi,pi)
        with self.assertRaisesRegex(AssertionError,'STATE_NORM'):w.state_checks([2*z for z in pi],pi,pi)
        self.assertEqual(w.density_error([1j*z for z in pi],pi),0)

    def test_nonfinite_and_shape_rejection(self):
        for bad in (float('nan'),float('inf'),-float('inf'),complex(0,float('nan'))):
            for i in (0,1):
                v=[0j,1+0j];v[i]=bad
                with self.assertRaises(AssertionError):w.distance(v,[0j,1+0j])
                with self.assertRaises(AssertionError):w.distance([0j,1+0j],v)
                with self.assertRaises(AssertionError):w.state_checks(v,[0j,1+0j],[0j,1+0j])
        with self.assertRaises(AssertionError):w.distance([0],[0,1])
        for values,step in [([0]*3,.001),([0,float('nan'),0,0],.001),([0]*4,0),([0]*4,float('inf'))]:
            with self.assertRaises(AssertionError):w.spline(values,step)
        for area in (float('nan'),float('inf'),-1):
            with self.assertRaises(AssertionError):w.samples(area)

    def test_device_rejection_precondition(self):
        self.assertLess(max(w.samples(math.pi)),4*math.pi)
        self.assertGreater(max(w.samples(2*math.pi)),4*math.pi+1e-6)
        self.assertAlmostEqual(max(w.samples(math.pi)),7.4874396195619575,places=12)


if __name__=='__main__':unittest.main(verbosity=2)
