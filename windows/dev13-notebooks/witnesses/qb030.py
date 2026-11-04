"""Finite authored pulse witnesses. Module import is standard-library only."""
import cmath
import hashlib
import json
import math
from pathlib import Path
import warnings

SOURCE_HASHES = {'pulser_simulation/simulation.py': 'ef3714f6093dd22ca6b1b063b5878fe72a77c83a32a32186a83d04927f622ad1', 'pulser_simulation/hamiltonian.py': '9e898be30c73ac91258084d671b528b934bad2acc27cd73b87c31dd054f2078f', 'pulser_simulation/simresults.py': '026692f600d9a5b11c7ff5be23e108bb68339a18219667a47ca36be7fd1ec6fa', 'pulser_simulation/qutip_result.py': '344417cfc5af0b1b6ad9f5d05e158c77034bd101e5951b06b7603087025c3d0f', 'pulser/sequence/sequence.py': '1eecd7289633825fd9d72954436a1024d7536d5cad74c6aa88f37393bc7eb9ec', 'pulser/channels/base_channel.py': 'bc10851aa249018ed6a9e49c5d07136fc06afab1381a0388c62aed119e39de09', 'pulser/devices/_devices.py': '582ec1ac9962d29a40c840f3d7dd392519079499fa7aecd494171b382d6d0e22', 'pulser/math/__init__.py': 'b25dc9070d0bd2c5f0a1eaa90109484582c66d9c079eb17b38c7b82016a878e6', 'scipy/interpolate/_bsplines.py': 'dfd2f328c15e04ebc84361d31dce696910c5be8edb774f83f3e3aeda14fe66b9'}
REFERENCE_BINDINGS = {'qb030-independent-reference.json': '9ca5c674b98f1d5da90d3051b4834ab05d9fc949f1bbf6ebc246a0d602d8a15f', 'qb030-spline-reference.json': '5279c823213f387bd186b51c91d9749bb07266ce4944543f9e416d75e89c864a'}

SAMPLE_TOL = 1e-10
AREA_TOL = 1e-10
MODEL_AREA_TOL = 1e-7
STATE_TOL = 1e-5
NORM_TOL = 1e-8
CONVERGENCE_TOL = 1e-7
SOLVERS = [dict(method='adams', atol=1e-10, rtol=1e-9, max_step=.001,
                nsteps=1000000, store_states=True),
           dict(method='adams', atol=1e-12, rtol=1e-11, max_step=.0005,
                nsteps=1000000, store_states=True)]
CASES = [('source-area-pi', math.pi, 0.), ('area-zero', 0., 0.),
         ('area-half-pi', math.pi/2, 0.), ('phase-half-pi', math.pi/2, math.pi/2),
         ('phase-asymmetric', math.pi/2, .37)]


def require(ok, label):
    if not ok:
        raise AssertionError(label)


def finite(values):
    return all(math.isfinite(complex(z).real) and math.isfinite(complex(z).imag) for z in values)


def distance(actual, expected):
    require(len(actual) == len(expected) and len(actual) > 0, 'VECTOR_WIDTH')
    require(finite(actual) and finite(expected), 'NONFINITE_VECTOR')
    return max(abs(a-b) for a,b in zip(actual, expected))


def samples(area, duration=1000):
    require(type(duration) is int and duration >= 4, 'DURATION')
    require(math.isfinite(area) and area >= 0, 'AREA')
    window = [max(0., .42-.5*math.cos(2*math.pi*j/(duration-1))
                  +.08*math.cos(4*math.pi*j/(duration-1))) for j in range(duration)]
    norm = math.fsum(window)
    values = [v*area*1000/norm for v in window]
    require(finite(values), 'NONFINITE_SAMPLES')
    return values


def spline(values, step=.001):
    """Scalar uniform not-a-knot cubic; no SciPy/QuTiP answers used."""
    n = len(values)
    require(n >= 4 and math.isfinite(step) and step > 0 and finite(values), 'SPLINE_GRID')
    k = n-2
    low, diag, up = [1.]*k, [4.]*k, [1.]*k
    rhs = [6*(values[i-1]-2*values[i]+values[i+1])/step**2 for i in range(1,n-1)]
    low[0], diag[0], up[0] = 0., 6., 0.
    low[-1], diag[-1], up[-1] = 0., 6., 0.
    for i in range(1,k):
        q = low[i]/diag[i-1]
        diag[i] -= q*up[i-1]
        rhs[i] -= q*rhs[i-1]
    middle = [0.]*k
    middle[-1] = rhs[-1]/diag[-1]
    for i in range(k-2,-1,-1):
        middle[i] = (rhs[i]-up[i]*middle[i+1])/diag[i]
    second = [2*middle[0]-middle[1]] + middle + [2*middle[-1]-middle[-2]]
    coefficients = [[values[i], (values[i+1]-values[i])/step-step*(2*second[i]+second[i+1])/6,
                     second[i]/2, (second[i+1]-second[i])/(6*step)] for i in range(n-1)]
    area = math.fsum(step*(values[i]+values[i+1])/2-step**3*(second[i]+second[i+1])/24
                     for i in range(n-1))
    require(finite([area]+[v for row in coefficients for v in row]), 'NONFINITE_SPLINE')
    return coefficients, area


def closed(area, phase):
    require(math.isfinite(area) and math.isfinite(phase), 'STATE_PARAMETERS')
    return [-1j*cmath.exp(1j*phase)*math.sin(area/2), complex(math.cos(area/2))]


def density(state):
    require(len(state) == 2 and finite(state), 'STATE_SHAPE_OR_FINITE')
    return [a*b.conjugate() for a in state for b in state]


def density_error(a, b):
    x, y = density(a), density(b)
    return math.sqrt(math.fsum(abs(u-v)**2 for u,v in zip(x,y)))


def state_checks(actual, expected, original_expected, pi_case=False):
    require(len(actual) == 2 and finite(actual), 'RAW_STATE')
    norm_error = abs(math.fsum(abs(z)**2 for z in actual)-1)
    error = density_error(actual, expected)
    original_error = density_error(actual, original_expected)
    require(norm_error <= NORM_TOL, 'STATE_NORM')
    require(error <= STATE_TOL and original_error <= STATE_TOL, 'STATE_DENSITY')
    if pi_case:
        require(abs(actual[0])**2 >= 1-1e-6, 'PI_EXCITED_POPULATION')
    return dict(raw_state_rg=[[z.real,z.imag] for z in actual], norm_error=norm_error,
                density_error_spline=error, density_error_original=original_error,
                excited_population=abs(actual[0])**2)


def run(original_sequence, original_pulse, original_register):
    from importlib.metadata import version
    import pulser
    from pulser import Pulse, Register, Sequence
    from pulser.devices import AnalogDevice
    from pulser.waveforms import BlackmanWaveform
    from pulser.noise_model import NoiseModel
    from pulser_simulation import QutipEmulator

    site = Path(pulser.__file__).resolve().parent.parent
    for relative, expected_hash in SOURCE_HASHES.items():
        require(hashlib.sha256((site/relative).read_bytes()).hexdigest() == expected_hash,
                'PINNED_SOURCE_CHANGED:'+relative)
    require(list(original_register.qubit_ids) == ['q0'], 'REGISTER_ORDER')
    require(distance(list(original_register.qubits['q0']), [0.,0.]) == 0, 'REGISTER_POSITION')
    require(set(original_sequence.declared_channels) == {'rydberg'}, 'DECLARED_CHANNEL')
    channel = original_sequence.declared_channels['rydberg']
    require(channel.basis == 'ground-rydberg' and channel.addressing == 'Global', 'CHANNEL_BASIS')
    require(channel.clock_period == 4 and channel.min_duration == 16, 'CHANNEL_CLOCK')
    require(abs(channel.max_amp-4*math.pi) < 1e-12, 'CHANNEL_AMPLITUDE_LIMIT')
    require(original_sequence.get_duration() == 1000 and original_pulse.duration == 1000, 'SOURCE_DURATION')
    source_samples = list(original_pulse.amplitude.samples.as_array(detach=True))
    require(distance(source_samples, samples(math.pi)) <= SAMPLE_TOL, 'SOURCE_WAVEFORM')
    require(distance(list(original_pulse.detuning.samples.as_array(detach=True)), [0.]*1000) == 0,
            'SOURCE_DETUNING')
    require(float(original_pulse.phase) == 0, 'SOURCE_PHASE')
    serialized = original_sequence.to_abstract_repr()
    restored = Sequence.from_abstract_repr(serialized)
    require(json.loads(restored.to_abstract_repr()) == json.loads(serialized), 'SERIALIZATION_ROUNDTRIP')
    require(restored.get_duration() == 1000 and list(restored.register.qubit_ids) == ['q0'],
            'REIMPORT_IDENTITY')

    def make_sequence(area, phase):
        seq = Sequence(Register({'q0':(0.,0.)}), AnalogDevice)
        seq.declare_channel('rydberg','rydberg_global')
        seq.add(Pulse.ConstantDetuning(BlackmanWaveform(1000,area),0.,phase),'rydberg')
        return seq

    cases, captured_warnings = [], []
    for name, area, phase in CASES:
        seq = original_sequence if name == 'source-area-pi' else make_sequence(area,phase)
        expected_samples = samples(area)
        coeff, cubic_area = spline(expected_samples+[0.])
        discrete_area = math.fsum(expected_samples)*.001
        require(abs(discrete_area-area) <= AREA_TOL, 'DISCRETE_AREA')
        require(abs(cubic_area-discrete_area) <= MODEL_AREA_TOL, 'CUBIC_MODEL_AREA')
        expected_state, original_state = closed(cubic_area,phase), closed(area,phase)
        runs, states = [], []
        for options in SOLVERS:
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter('always')
                emulator = QutipEmulator.from_sequence(seq, sampling_rate=1., evaluation_times='Full',
                    with_modulation=False, noise_model=NoiseModel())
                emulator.set_initial_state('all-ground')
                require(emulator.basis_name == 'ground-rydberg' and emulator.dim == 2, 'EMULATOR_BASIS')
                require(emulator.total_duration_ns == 1000, 'EMULATOR_DURATION')
                require(not emulator.noise_model.noise_types, 'UNEXPECTED_NOISE')
                require(len(emulator._current_hamiltonian._collapse_ops) == 0, 'COLLAPSE_OPERATORS')
                require(distance(list(emulator.basis['r'].full().ravel()), [1.,0.]) == 0 and
                        distance(list(emulator.basis['g'].full().ravel()), [0.,1.]) == 0, 'BASIS_VECTORS')
                require(distance(list(emulator.initial_state.full().ravel()), [0.,1.]) == 0, 'INITIAL_STATE')
                require(distance(list(emulator.sampling_times), [j*.001 for j in range(1001)]) <= 1e-12,
                        'COEFFICIENT_GRID')
                sampled = emulator.samples_obj.channel_samples['rydberg']
                actual_amp = list(sampled.amp.as_array(detach=True))
                require(distance(actual_amp, expected_samples+[0.]) <= SAMPLE_TOL, 'EMULATOR_AMPLITUDE')
                require(distance(list(sampled.det.as_array(detach=True)), [0.]*1001) == 0, 'EMULATOR_DETUNING')
                require(distance(list(sampled.phase.as_array(detach=True)), [phase]*1001) <= 1e-12,
                        'EMULATOR_PHASE')
                h_checks = []
                for index, fraction in [(0,0.),(1,.17),(127,.5),(499,.5),(998,.83),(999,.5),(999,1.)]:
                    a,b,c,d = coeff[index]
                    t = fraction*.001
                    omega = a+t*(b+t*(c+t*d))
                    expected_h = [0j, .5*omega*cmath.exp(1j*phase),
                                  .5*omega*cmath.exp(-1j*phase), 0j]
                    # Public get_hamiltonian takes ns; spline coordinates are us.
                    observed_h = list(emulator.get_hamiltonian(index+fraction, noiseless=True).full().ravel())
                    error = distance(observed_h, expected_h)
                    require(error <= SAMPLE_TOL, 'INTERPOLATED_HAMILTONIAN')
                    h_checks.append(dict(time_ns=index+fraction, residual=error))
                result = emulator.run(progress_bar=False, **options)
                qstate = result.get_final_state(reduce_to_basis=None, ignore_global_phase=False, normalize=False)
                require(qstate.isket and qstate.shape == (2,1), 'RAW_QOBJ_SHAPE')
                actual = [complex(z) for z in qstate.full().ravel()]
                check = state_checks(actual, expected_state, original_state, name == 'source-area-pi')
                states.append(actual)
                runs.append(dict(options=options, state=check, interpolated_hamiltonian=h_checks,
                                 coefficient_samples=actual_amp, raw_qobj_dims=qstate.dims,
                                 coefficient_grid_count=len(emulator.sampling_times),
                                 noise_types=list(emulator.noise_model.noise_types), collapse_operators=0))
                captured_warnings.extend(dict(category=w.category.__name__,message=str(w.message)) for w in caught)
        convergence = density_error(states[0],states[1])
        require(convergence <= CONVERGENCE_TOL, 'SOLVER_CONVERGENCE')
        cases.append(dict(case=name, area=area, phase=phase, discrete_area=discrete_area,
                          cubic_area=cubic_area, model_area_difference=cubic_area-discrete_area,
                          convergence_density_error=convergence, runs=runs))

    peak = max(samples(2*math.pi))
    require(peak > channel.max_amp+1e-6, 'EXPECTED_REJECTION_PRECONDITION')
    try:
        make_sequence(2*math.pi,0.)
    except ValueError as error:
        require('amplitude goes over' in str(error), 'OVER_AMPLITUDE_DIAGNOSTIC')
        rejection = dict(case='area-two-pi',duration_ns=1000,peak=peak,channel_max=channel.max_amp,
                         type=type(error).__name__,message=str(error))
    else:
        raise AssertionError('OVER_AMPLITUDE_ACCEPTED')
    require(original_sequence.to_abstract_repr() == serialized, 'ORIGINAL_SEQUENCE_MUTATED')
    return dict(accepted=True,route='selected-cells/direct-native-execution',selected_source_cells=[6],
        whole_notebook_complete=False,original_sequence_preserved=True,
        serialized_original=json.loads(serialized),serialized_reimport_equal=True,
        source_hashes=SOURCE_HASHES, cases=cases, unsupported=rejection,warnings=captured_warnings,
        versions={n:version(n) for n in ('pulser-core','pulser-simulation','qutip','numpy','scipy','matplotlib')},
        references=REFERENCE_BINDINGS,
        tolerances=dict(samples=SAMPLE_TOL,discrete_area=AREA_TOL,model_area=MODEL_AREA_TOL,
                        density=STATE_TOL,norm=NORM_TOL,convergence=CONVERGENCE_TOL),
        limits=['Original cell constructs/draws pulse; all ten local simulations are authored',
                'No noise, modulation, physical calibration, provider job or whole-notebook acceptance',
                'Two-pi1000ns control is expected device rejection, not silently adapted',
                'Deprecated pinned QutipEmulator route; warnings retained, no future API guarantee'])


if __name__ == '__main__':
    print(json.dumps(run(sequence,pulse,reg),allow_nan=False))
