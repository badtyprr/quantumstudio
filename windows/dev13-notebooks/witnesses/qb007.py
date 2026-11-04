"""Authored finite Cirq witness; original six function cells remain unchanged."""
import collections
import hashlib
import json
import math

REFERENCE_JSON = r'''{"authored_h":[[1,-1],[1,1]],"authored_jc":[[1],[-1]],"authored_jr":[[-1,1]],"basis_order":"0000 through1111; first qubit most significant","cases":[{"amplitudes":[[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0],[0.25,0.0]],"expected_energy":0.0,"half_turns":{"controlled_phase":0,"x":0,"z":0},"name":"zero","oracle_crosscheck_max_residual":0.0,"probabilities":[0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625,0.0625]},{"amplitudes":[[-0.021165965984034918,0.3400430928902235],[-0.25711583341521066,0.21606179805586465],[-0.11124364935836797,0.5114707060561996],[-0.15354309028090338,0.10896645483321332],[-0.20811089317518489,0.1486122842957229],[-0.08366596598403504,-0.04778459307350013],[-0.2234202145777718,0.3081977522968218],[0.04314829565857764,-0.008138763610990626],[-0.2571158334152107,0.21606179805586462],[-0.25155297076095495,0.08023835805662838],[-0.1535430902809034,0.10896645483321332],[-0.005856644581448144,0.0593107501491512],[-0.08366596598403504,-0.0477845930735001],[0.0640204797154204,0.023706576982411257],[0.04314829565857766,-0.008138763610990626],[0.021721038792885033,0.04839301746322658]],"expected_energy":1.3583704137497343,"half_turns":{"controlled_phase":0.3,"x":0.3,"z":0.3},"name":"original_angles","oracle_crosscheck_max_residual":1.1443916996305594e-16,"probabilities":[0.11607730313838649,0.11279125237193158,0.27397743267619484,0.035449168851928364,0.06539575490176598,0.009283361199241709,0.1449024468027907,0.0019280148913556152,0.11279125237193162,0.06971709120228554,0.03544916885192837,0.003552065369008445,0.009283361199241702,0.004660623615215546,0.0019280148913556172,0.002813687665438169]},{"amplitudes":[[0.368645293307611,0.06254400608682929],[0.05575820380346464,-0.06391887711933372],[-0.061265130350368915,0.016730084081298228],[-0.03405398050917336,0.08711680837978121],[0.5378056912256194,-0.32107672717389163],[0.34451198839934977,-0.05103581185860348],[-0.02182090961949381,-0.06980593505374848],[0.09705013351777708,0.09452444545562791],[0.05575820380346463,-0.06391887711933374],[0.01265450090843008,-0.12633380007477732],[-0.034053980509173375,0.08711680837978118],[0.046369418507495645,0.006092343988939965],[0.34451198839934977,-0.05103581185860351],[0.2784093252830775,-0.03766725694574618],[0.09705013351777707,0.09452444545562792],[0.09660706964244012,0.2018154593193505]],"expected_energy":0.922488947988664,"half_turns":{"controlled_phase":-0.29,"x":0.41,"z":0.17},"name":"asymmetric_angles","oracle_crosscheck_max_residual":1.1102230246251565e-16,"probabilities":[0.13981110497524385,0.0071946001435851835,0.004033311910215003,0.008749011890798675,0.3923252262473638,0.12129316424294047,0.005349020665350267,0.018353599204512336,0.0071946001435851835,0.016120365434575262,0.008749011890798674,0.002187239628002852,0.12129316424294047,0.07893057465039532,0.018353599204512336,0.05006240552517969]},{"amplitudes":[[-0.06217247179121366,-0.2421457902821578],[0.23244412147206286,-0.09203113817116947],[0.2151855067509859,0.12726035393759283],[0.12043841852542879,0.21907667001096592],[-0.06217247179121366,-0.2421457902821578],[0.06974777650980737,-0.24007342141923574],[0.2151855067509859,0.12726035393759283],[0.24692208514878441,0.03910861626005775],[0.23244412147206286,-0.09203113817116947],[0.12043841852542879,0.21907667001096592],[0.12043841852542879,0.21907667001096592],[-0.00785268976953207,0.2498766400914329],[0.06974777650980737,-0.24007342141923574],[0.18224215685535292,-0.17113677648217213],[0.24692208514878441,0.03910861626005775],[0.24397919048468686,-0.0545358103491356]],"expected_energy":-5.551115123125783e-17,"half_turns":{"controlled_phase":-0.29,"x":0,"z":0.17},"name":"diagonal_only","oracle_crosscheck_max_residual":0.0,"probabilities":[0.0625,0.0625,0.0625,0.0625,0.0625,0.062499999999999986,0.0625,0.062499999999999986,0.0625,0.0625,0.0625,0.0625,0.062499999999999986,0.0625,0.062499999999999986,0.0625]},{"amplitudes":[[0.24999999999999986,2.42861286636753e-17],[0.24999999999999992,0.0],[0.24999999999999997,-3.469446951953614e-17],[0.25,-3.469446951953614e-17],[0.24999999999999997,-3.469446951953614e-17],[0.25,-3.469446951953614e-17],[0.25,-2.7755575615628914e-17],[0.25,-1.3877787807814457e-17],[0.24999999999999997,-6.938893903907228e-18],[0.25,-2.0816681711721685e-17],[0.24999999999999994,-2.7755575615628914e-17],[0.24999999999999994,-1.3877787807814457e-17],[0.24999999999999994,-2.0816681711721685e-17],[0.24999999999999994,-1.3877787807814457e-17],[0.24999999999999994,-2.7755575615628914e-17],[0.24999999999999994,1.3877787807814457e-17]],"expected_energy":-2.7755575615628914e-17,"half_turns":{"controlled_phase":0,"x":0.41,"z":0},"name":"plus_mixer","oracle_crosscheck_max_residual":1.4088688899021424e-16,"probabilities":[0.06249999999999993,0.06249999999999996,0.062499999999999986,0.0625,0.062499999999999986,0.0625,0.0625,0.0625,0.062499999999999986,0.0625,0.06249999999999997,0.06249999999999997,0.06249999999999997,0.06249999999999997,0.06249999999999997,0.06249999999999997]}],"classification":"authored-independent-reference; no source cells or SDK executed","energies":[2,0,4,-2,0,2,2,0,0,-2,-2,-8,2,4,0,-2],"limits":["No unchanged-cell execution, runtime/profile acceptance, GPU or whole-notebook proof.","Two oracle formulations are internal consistency checks, not independent framework validation.","Original function semantics retained, not ideal Ising evolution or ground-state optimization.","Floating-point references use absolute1e-13 norm and1e-14 consistency bounds; future SDK tolerance must be explicit."],"qubit_order":[[0,0],[0,1],[1,0],[1,1]],"sampling_acceptance_proposal":{"absolute_energy_tolerance":0.5,"energy_bounds":[-8,8],"hoeffding_upper_bound":2.2507034943851823e-07,"shots":8192,"status":"proposed; no shots executed"},"selected_source_cell_hashes":{"11":"3dc5f3f534200b4a902e8fe70c3c87a1b5b1404bb296f0ecb3e62ea3bedaac12","14":"3f195b9d5ab09e2898a0c13e4293190ba0db11fed9d93f6a1717a8ee5a6ad107","23":"4378cd2bb596bdf50feabc49f696950b8af99d0477be0a4dd6eb8d15e6f7f1c2","25":"11319e0dd0c23b4b7103ae6d831f62ada12047223bc5ebb88c47a78b059cacb7","7":"eb5a297c3c7a2c72ec2c1c4ed33f2f7bd4371fe20e04321e822795ddeec19e68","9":"f5e29a3f72be4d7c9819bf8a72e1dced1312ce82e11d5c1c4f04c9473ea025c2"},"source_path":"qBraid-Algorithms/cirq_vqe.ipynb","source_revision":"86787e1ba372facc224f925189755e69c479828b","source_sha256":"221d531613cbf4f74db1f9df4faf2c28d462c13480f28b5b559ec2ffc0f1697d","stable_id":"QB-007"}'''
if hashlib.sha256(REFERENCE_JSON.encode()).hexdigest() != "97c2f274b82a2314668468a6e059530098e9f656464142db67ef2053e5e5a2b7":
    raise ValueError("INDEPENDENT_REFERENCE_CHANGED")
reference = json.loads(REFERENCE_JSON)

def require(condition, message):
    if not condition:
        raise ValueError(message)

qubits = [cirq.GridQubit(i, j) for i in range(2) for j in range(2)]
source_energy = energy_func(length, h, jr, jc)
energies = []
for basis in range(16):
    bits = [(basis >> (3 - i)) & 1 for i in range(4)]
    signs = [1 - 2 * bit for bit in bits]
    expected = sum(a * b for a, b in zip([1, -1, 1, 1], signs))
    expected += sum(j * signs[a] * signs[b] for a, b, j in [(0, 2, -1), (1, 3, 1), (0, 1, 1), (2, 3, -1)])
    require(int(source_energy(bits)) == expected, "SOURCE_ENERGY_MISMATCH")
    energies.append(expected)
require(energies == reference["energies"], "REFERENCE_ENERGY_MISMATCH")

checks = []
for case in reference["cases"]:
    params = case["half_turns"]
    circuit = cirq.Circuit(prepare_plus_layer(length), rot_z_layer(h, params["z"]),
        rot_11_layer(jr, jc, params["controlled_phase"]), rot_x_layer(length, params["x"]))
    simulator = cirq.Simulator(dtype=np.complex128, seed=1731)
    actual = simulator.simulate(circuit, qubit_order=qubits).final_state_vector
    expected = np.array([complex(a, b) for a, b in case["amplitudes"]], dtype=np.complex128)
    residual = float(np.max(np.abs(actual - expected)))
    require(math.isfinite(residual) and residual < 1e-12, "SOURCE_STATE_MISMATCH")
    expectation = float(sum(float(abs(a) ** 2) * e for a, e in zip(actual, energies)))
    require(abs(expectation - case["expected_energy"]) < 1e-12, "EXPECTED_ENERGY_MISMATCH")
    measured = circuit.copy()
    measured.append(cirq.measure(*qubits, key="x"))
    sample = simulator.run(measured, repetitions=8192)
    raw = sample.measurements["x"]
    require(raw.shape == (8192, 4), "MEASUREMENT_SHAPE")
    counts = collections.Counter("".join(str(int(bit)) for bit in row) for row in raw)
    require(sum(counts.values()) == 8192 and all(len(key) == 4 and set(key) <= {"0", "1"} for key in counts), "COUNT_ENCODING")
    independent_mean = sum(energies[int(key, 2)] * count for key, count in counts.items()) / 8192
    source_mean = float(obj_func(sample))
    require(abs(source_mean - independent_mean) < 1e-12, "OBJECTIVE_MISMATCH")
    require(abs(independent_mean - case["expected_energy"]) <= .5, "SAMPLING_ENERGY_BOUND")
    checks.append(dict(case=case["name"], state_residual=residual, expected_energy=case["expected_energy"],
        state_energy=expectation, sampled_energy=independent_mean, source_objective=source_mean,
        shots=8192, counts=dict(sorted(counts.items()))))

ordering = []
for which, expected_key, expected_basis in [(0, "1000", 8), (3, "0001", 1)]:
    control = cirq.Circuit(cirq.I.on_each(qubits), cirq.X(qubits[which]))
    simulator = cirq.Simulator(dtype=np.complex128, seed=1731)
    vector = simulator.simulate(control, qubit_order=qubits).final_state_vector
    expected = np.zeros(16, dtype=np.complex128)
    expected[expected_basis] = 1
    require(float(np.max(np.abs(vector - expected))) < 1e-12, "ORDERING_STATE")
    control.append(cirq.measure(*qubits, key="x"))
    observed = simulator.run(control, repetitions=16).histogram(key="x")
    require(dict(observed) == {expected_basis: 16}, "ORDERING_COUNTS")
    ordering.append(dict(qubit_index=which, bitstring=expected_key, basis=expected_basis, shots=16))

print(json.dumps(dict(accepted=True, route="selected-cells/direct-native-execution",
    whole_notebook_complete=False, selected_source_cells=[7, 9, 11, 14, 23, 25],
    reference_sha256="7b5235b8ffb2973500a26045067fd6223930ab78cb8b57fe9299b422b7144ef2",
    reference_payload_sha256=hashlib.sha256(REFERENCE_JSON.encode()).hexdigest(),
    cirq_version=cirq.__version__, numpy_version=np.__version__, energies=energies,
    qubit_order=[[q.row, q.col] for q in qubits], checks=checks, ordering_controls=ordering,
    seed=1731, state_tolerance=1e-12, sample_energy_tolerance=.5,
    sampling_assumption="Independent samples; Hoeffding bound 2exp(-16) per case with energy in [-8,8]",
    limitations=["Selected functions with authored setup, not original 5x5 GPU benchmark",
                "No optimization loop or ground-state minimum claim", "No QASM adaptation or provider jobs"])))
