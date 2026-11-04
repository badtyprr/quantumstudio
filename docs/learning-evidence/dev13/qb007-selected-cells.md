# QB007: selected unchanged Cirq function cells

This contract executes six original function cells from
[cirq_vqe.ipynb](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/cirq_vqe.ipynb)
at revision `86787e1ba372facc224f925189755e69c479828b`. Original notebook SHA-256:
`221d531613cbf4f74db1f9df4faf2c28d462c13480f28b5b559ec2ffc0f1697d`.
Stable source ID QB-007 is unchanged. The route is explicitly
`selected-cells/direct-native-execution`, not whole-notebook execution, import-only
coverage or QASM adaptation.

The implementation is prepared against
`244681403225583af607d6839ec39511d83fc2ab`. At this preparation stage only synthetic
tests have run; actual Cirq source execution and acceptance remain pending.

## Exact source and setup boundary

The full original file and all33 cell text/type hashes are validated before
environment inspection and launch. Only original indices7,9,11,14,23,25 enter the
execution notebook, unchanged and in original order. They define prepare_plus_layer,
rot_x_layer, rot_z_layer, rot_11_layer, energy_func and obj_func. An explicitly
authored preamble imports Cirq/NumPy and supplies length2, fixed signed fields and
couplings. An independently hashed authored witness constructs and tests circuits.
Neither authored cell is represented as original source.

| Original indices | Disposition |
|---|---|
| 7,9,11,14,23,25 | Six unchanged function cells selected for execution |
| 2 | Broader original imports, including qsimcirq, excluded |
| 4,5 | Original random coefficient generation/display excluded |
| 8,10,12,13,15,16 | Intermediate source demonstrations/displays excluded |
| 17,18 | Original5×5 benchmark construction/drawing excluded |
| 20 | Original CPU/GPU simulator construction excluded |
| 27,29,31 | Original CPU/GPU runs, timing and speedup excluded |
| 0,1,3,6,19,21,22,24,26,28,30,32 | Twelve Markdown cells retained in the full source and disposition record |

`source-original.ipynb` preserves the complete original bytes.
`source-disposition.json` accounts for every original cell, with source hash,
index, type, state and exclusion reason. It exists before process launch and is
updated at checkpoints and recovery. Excluded code remains `excluded_by_contract`;
Markdown remains `not_executable`. The executed notebook contains the six selected
cells plus the authored preamble and witness; it is deliberately not a rewritten
copy masquerading as the complete original.

Status always marks this route with `source_scope=selected_cells`,
`whole_notebook_complete=false`, and `original_execution=not_executed_as_whole`.
`selected_execution` separately reports not_run, incomplete or succeeded.
Cancellation, failure and missing engine reports preserve these distinctions.
The owned process lifecycle, deadlines and cleanup mechanism are reused. Existing
whole-notebook routes continue to execute all original cells and retain their
existing status vocabulary.

## Pinned environment reuse

The contract transparently reuses `qir-win-py312`: Python3.12.10, Windows64bit,
94 exact locked distributions, including cirq-core1.5.0 and NumPy2.5.4. The lock's
LF-normalized SHA-256 is
`70faf49c835ed96a1d6bf6941690536af4c47515b91659d908a7b57efaabb282`.
This is a retained dependency superset, not a minimal Cirq profile. All94 retained
wheels and the existing installed distribution inventory were reverified before
reuse; no profile or lock change is made. Later execution acceptance must retain
the actual environment identity and offline replay evidence. This contract makes
no Linux, current-Cirq-version or GPU compatibility claim.

## Independent witness

The previously reviewed scalar reference is embedded as data in the witness,
with both its original artifact hash
`7b5235b8ffb2973500a26045067fd6223930ab78cb8b57fe9299b422b7144ef2`
and an independently checked canonical payload hash. It was generated without
Cirq or source-cell execution, using closed-form mixer convolution and a separate
sequential local-pair cross-check. Expected amplitudes are not obtained from the
Cirq circuit under test.

The witness uses row-major GridQubit order `(0,0),(0,1),(1,0),(1,1)`, first qubit
most significant. It checks all16 amplitudes for five fixed angle cases, all16
energies using an independent scalar spin formula, exact state energy, and the
original obj_func against raw sampled-bitstring mean. Sampling uses seed1731 and
8,192 shots per case. The absolute energy tolerance remains0.5; with energy in
[-8,8], the retained Hoeffding bound2exp(-16) is per case and assumes independent
samples. It is not a guarantee across all future random runs or all five cases
simultaneously. State/energy arithmetic tolerance is1e-12. Separate authored
one-hot controls on the first/last qubit expose bit-order reversal.

Actual source semantics are preserved: negative fields are omitted by rot_z_layer;
negative couplings conjugate the controlled-phase gate by X on both endpoints.
The XPowGate phase convention is included in the reference. These semantics must
not be silently replaced by an idealized Ising exponential. The original has no
optimization loop: successful witness output is not a VQE ground-state solution.

## Finite acceptance matrix

Synthetic preparation tests (no Cirq/source execution) cover:

1. The actual engine cell loop cannot execute an omitted raising sentinel.
2. The whole-notebook route still executes every code cell and retains Markdown.
3. Synthetic cancellation preserves selected progress and all dispositions.
4. Missing engine-report recovery marks a running selected cell interrupted.
5. Empty, duplicate, unordered, Boolean, out-of-range or Markdown selections fail.
6. Incomplete exclusion reasons, setup observers and out-of-selection output requirements fail.
7. Selection requires an explicit supported route.
8. Changed source, changed witness and malformed selection fail before environment inspection.
9. The QB007 contract accounts for33 cells:6 selected,15 excluded code,12 Markdown; witness hash/syntax is checked without executing it.

Run the synthetic tests with the retained runtime environment:

```text
python -B -m unittest -v test_execution.SelectedCellTests test_execution.PlatformProfileTests
python -B -O -m unittest -v test_execution.SelectedCellTests test_execution.PlatformProfileTests
```

After independent implementation reviews and a reserved execution window, the
existing public command accepts `--contract qb007` with the original source path,
retained environment and fresh output directory. Actual acceptance must verify
six unchanged cells, all33 dispositions, witness states/energies/counts/order,
source bytes before/after and owned cleanup. Real selected-route cancellation
and partial checkpoints remain an execution gate; the mock kernel tests above
do not establish process cleanup by themselves.

No original GPU benchmark, timing/speedup, full-notebook output, provider/hardware
job, original random instance, or whole AUD04 completion is established here.
