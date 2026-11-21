# QB-007 original CPU workload

This route executes the original five-by-five circuit with 25 qubits and 10,000
shots. It supplements the existing six-function, four-qubit `qb007` route;
neither route establishes the full GPU notebook. QB-007 remains open.

The notebook is `qBraid-Algorithms/cirq_vqe.ipynb` at revision
`86787e1ba372facc224f925189755e69c479828b`, SHA-256
`221d531613cbf4f74db1f9df4faf2c28d462c13480f28b5b559ec2ffc0f1697d`.
All 33 cell identities are retained. The `qb007-cpu` contract executes 18 original
code cells unchanged, including imports, random coefficient generation,
intermediate circuit construction/display, the 25-qubit circuit, cost functions
and the original CPU benchmark. The grid and shot count are not reduced.

## Explicit execution boundary

The original cell 20 initializes a Cirq CPU simulator and then a qsim cuStateVec
GPU simulator. In the prerequisite probe, its second part raises `ValueError`:
cuStateVec execution is requested but unsupported. The probe records the entire
original failure and subsequently runs the original CPU benchmark using the CPU
simulator that the first part created. That probe is not whole-notebook success.

The integrated route excludes cell 20 and uses a separately labelled preamble
to initialize only `cirq.Simulator()`. GPU benchmark cell 29 and speedup cell 31
are also excluded. Original cell 2 imports real Cirq and qsimcirq; no stub or
mock replaces the unavailable backend. The host has an AMD Radeon RX 7900 XT;
the requested cuStateVec backend is NVIDIA-specific. See the
[qsim hardware guide](https://quantumai.google/qsim/choose_hw).

The dedicated Windows Python 3.12.10 profile retains 60 hash-pinned wheels,
including cirq-core 1.5.0 and qsimcirq 0.22.1. Dependency closure verifies 60
distributions and 88 active requirements. This does not modify the existing
QIR environment or its six-cell contract.

## Independent result checks

The original random coefficients and samples remain unseeded. Each run records
its actual fields and couplings, counts, raw-measurement hash and observed CPU
duration. Runs need not produce identical circuits, energies, counts or timings.
No portable performance threshold or GPU speedup is claimed.

The witness checks the original grid, measurement order and 10,000-shot shape.
It calculates every sample's diagonal cost independently with array operations,
compares all 10,000 values with the source cost function and checks the source
sample mean. A separate integer row-dynamic-programming calculation finds the
minimum of that same classical cost function and retains a minimizing bit-grid
certificate. The certificate is evaluated independently and observed costs must
not fall below the bound.

Exhaustive tests cover all basis assignments on one-, two- and three-by-three
grids for four authored coefficient sets at each size: 2,120 cost comparisons.
They check every sample cost, the minimum and its certificate. A five-by-five
all-negative case checks the known minimum `-65`. Invalid coefficient shapes,
non-spin values and invalid measurement arrays are rejected.

The original output calls its sample mean a ground-state expectation. This
notebook runs one fixed-angle circuit; it contains no optimization loop. The
report therefore sets `ground_state_optimization_performed: false` and keeps
sampled energy separate from the classical minimum. That minimum concerns the
source diagonal cost function, not an arbitrary quantum Hamiltonian. No
independent full 25-qubit amplitude equivalence or native QuantumStudio worker
acceptance is claimed.

Both real-kernel runs and 48 focused tests pass, with zero owned processes
remaining after each. Each run checks all 10,000 source row energies. The replay
retained identical bytes and sizes for 29,536 files (602,366,249 bytes) across the
environment, base interpreter and notebook runtime. This compares interval
endpoints, not transient writes. The two random instances are verified separately;
no cross-run output identity is claimed. The [artifact index](index.json) binds 46 retained files by size and SHA-256,
including the prerequisite GPU failure and dependency resolution. All 33 source
cell hashes were checked. Exact-head reviews remain pending. External records are under
`cleanup-audit/learning-coverage-20261117/qb007-cpu/` and the adjacent
`qb007-prerequisites/`. GPU execution, speedup, whole-source audit, GUI/package,
required CI and release remain open.

## Independent full-state comparison

A seeded five-by-five instance now has an independent reference for all 33,554,432 complex amplitudes. The reference forms phases from the grid field and both edge arrays, then applies the final fractional-X layer. Cirq executes the source circuit without terminal measurements for the amplitude comparison. After global phase alignment the maximum amplitude error was 7.15e-9 and fidelity exceeded 0.999999999999. The exact mean energy was 12.5754101. A separate 10,000-shot run of the measured circuit gave 12.569, with standard error 0.08222. Every sampled row energy matched the independently calculated grid energy. Inputs and numerical details are in full-state.json.

Run verify-full-state.py with the pinned source notebook and a fresh output JSON path using the Cirq/qsimcirq CPU environment. This is a seeded additional instance. The source's GPU, speedup, whole-notebook and published app checks remain open.
