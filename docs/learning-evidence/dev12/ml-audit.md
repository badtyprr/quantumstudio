# DEV-12 machine-learning source audit

Audit-only: no product operation, shared build file or central checklist changed.
Upstream was fetched from `origin` (there is no `upstream` remote); selected base
`753bf16df56aeae0f6454f89999ef203665755f6`. Ownership agreed with Agent 1:
ML-specific evidence here; general objectives/derivatives and integration stay
with Agent 1, chemistry/eigensolvers with Agent 2. No new bounded product gap was
confirmed. This is **seven inventoried rows, zero fully certified rows**.

## Sources and coverage ledger

[Source manifest](ml-source-manifest.json) pins downloaded HTML/notebook URLs,
byte lengths and SHA256. [Cell ledger](ml-cell-ledger.json) inventories every cell
(zero-based indices, source-text hashes, type and acceptance status).
All raw bytes, original failures and complete run artifacts remain outside the
checkout at `F:/src/libqalculate/cleanup-audit/dev12-ml-20261102/`.
Initial Python urllib download returned HTTP403; `fetch-attempt-1.log` records
that failure. Curl subsequently fetched all seven notebooks successfully.
No source is presently access-blocked; linked video, image, PDF and reference
contents were not independently audited or certified.

| Row and primary source | Inventory and tested scope | Remaining surfaces / owner |
|---|---|---|
| [IBM-096 introduction](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/introduction) | Cell5: CSV selection, seven-qubit Ry/CZ/Rz/Rx encoding, overlap, sampling. Its encoding is shared with IBM099; no claim for the original sorted first-20 selection or indices14/19. | Original SDK/import/data-selection execution DEV-13; shots and full row unaudited. Advantage/existence discussion and media not certified. |
| [IBM-097 classical review](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/classical-ml-review) | Cells1–4 inventory SVM primal/dual objectives, quadratic feature lifting, Gram matrices, perceptron activation, MSE, gradient descent and QNN expectations/reuploading. Local finite Gram, MSE and expectation evidence is linked through IBM099/100; no original executable code cells. | SVM fitting/quadratic optimization, general activation/backpropagation and reuploading claims not certified; external training tooling and general objective work stay with their owners. |
| [IBM-098 encoding](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/data-encoding) | Cells6/8 amplitude examples (including padding); 11 angle,16 phase,22 dense angle,38 two-wire phase convention adapted and verified. | Cells3/4 12-wire basis example; 13/18 plots; 26/33 SU2; 40 Z-map repetitions; 43–49 ZZ; 53/56 Pauli gallery; 59 depth survey and hardware discussion remain unaudited as original executions. Generic scaling and arbitrary maps not certified. |
| [IBM-099 kernels](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/quantum-kernel-methods) | Cells26/30/32: original seven-wire custom map on first three pinned CSV rows, theta=pi/2; complete complex Gram and fidelity kernel, all nine inverse overlaps. Actual diagonal execution checked. | Original 10-feature example cells3–23, 90/30 training/test split, SVC cells34/36, 42-feature/21-wire scaling cells39–58, plots, shots, transpilation and provider calls not executed. |
| [IBM-100 QVC/QNN](https://quantum.cloud.ibm.com/learning/en/courses/quantum-machine-learning/qvc-qnn) | Cells10/12/16/18/20: original first eight-wire ansatz on two authored inputs/fixed weights; all 256 amplitudes and probabilities, global Z parity expectation and MSE. Scalar one-wire MSE/derivatives are explicitly reduced mathematical witnesses. | Source random dataset/split, COBYLA training (cell34 seed42, batch140, one epoch, maxiter100), improved ansatz cell45, repeated training, predictions/performance, 36-wire scaling and hardware remain unexecuted. No convergence or accuracy claim. |
| [IBM-119 variational algorithms](https://quantum.cloud.ibm.com/learning/en/courses/utility-scale-quantum-computing/variational-quantum-algorithms) | Cells61/65/66/99: all32 bitstrings verify the five-node six-unit-edge diagonal Hamiltonian with offset -3 equals negative cut size. | Cells7–50 Z/ZZ U-gate variational objectives, numpy eigenvalues and sampled COBYLA; QAOA construction/parameter order, optimizer/layout/backend/mitigation cells71–99 assigned to Agent1/2 or DEV-13/provider owners, not certified here. Source offset is correct for these unit edges; no weighted generalization claimed. |
| [QB-007 Cirq VQE](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-Algorithms/cirq_vqe.ipynb) | Cells9/11/14/17/23/25: reduced fixed 2x2 adaptation, all16 probabilities and basis energies. `jr` joins rows, `jc` joins columns. The measured objective is diagonal Z/ZZ. | Original unseeded 5x5 instance and 10,000-shot CPU/GPU execution remain DEV-13/hardware work. Cell20 constructs GPU simulator unconditionally. There is no optimization loop establishing a ground state in the tested source. Original timing/comparison and later cells remain unexecuted. |

## Conventions and independent expectations

The [pinned dataset manifest](ml-data-manifest.json) records the external CSV
snapshot. Only rows0–2 and their 14 features are used; no training/test split or
optimizer is exercised. Qiskit feature q maps to backend wire `n-1-q`, because
the backend's wire0 is most significant. The source custom map applies Rz of
minus twice the odd-indexed feature, followed by Rx of minus twice the even one;
CZ connections and theta are explicit. No alphabetical parameter binder is used.

The QNN Z-map expansion uses two H/P layers with phase `2*x`, per the
[official Z feature-map API](https://quantum.cloud.ibm.com/docs/en/api/qiskit/qiskit.circuit.library.z_feature_map).
That API HTML is separately hashed in the results summary. Authored images,
weights and labels are stored in every run; zero-valued pixels and deterministic
backgrounds deliberately differ from the source random generator. The class convention is source-faithful: horizontal=-1, vertical=+1. There is no
seed, split or optimizer to reproduce in this forward-only test.

Encoding amplitudes are checked against normalization constants sqrt105 and
sqrt270 and elementary sine/cosine formulas. The two-wire phase witness uses Rz
instead of P and explicitly retains its different global phase. Independent
Python row/column matrix embedding checks every native output amplitude and
probability, without fitting global phase or dropping zero outcomes. CNOT uses
a basis permutation and diagonal gates use direct bit predicates. Kernel inner
products are independently compared with inverse-circuit zero probabilities.
Complex overlaps are not equated with their squared magnitudes. All seven
principal minors of each finite 3x3 Hermitian Gram/fidelity matrix are checked;
this is not an eigensolver implementation or proof about an entire family.
IBM099 cell32 forces training diagonals to1 and mirrors shot estimates. Ideal
PSD here does not certify finite-shot PSD or exact sampled equality.

QB007 half-turns become radians times pi. Positive fields alone receive ZPow;
negative couplings retain both endpoint X sandwiches around controlled phase,
not a mechanically substituted ZZ rotation. XPow is represented by Rx, removing
the known common factor `exp(i*pi*t/2)` per qubit; the expected state uses that
same declared phase convention. Energies independently enumerate spin values
`1-2*b`, with full diagonal worker checks. No transverse X energy is substituted.

## Results, failures and provenance

[Results summary](ml-results-summary.json) records binary hashes and the full
external result path/hash. Run3 passes 65 packaged-worker expressions plus65
actual canonical serialization re-entries, and15 native numerical circuits
(2,064 amplitudes and all corresponding probabilities). Absolute tolerance is
1e-12; largest inverse-overlap discrepancy is 8.881784197001252e-16. The 3x3
complex Gram determinant is approximately0.01644835; the fidelity-kernel
determinant is approximately0.05301815. These finite checks make no full-row,
prediction, convergence or quantum-advantage claim.

The packaged worker is release `c575cb7e70d8b952c18d0a297a7784e246c34381`, SHA256
`24ffff787c90b9ebcdb6f483ee561dce67266a646702893236a935a55890b7df`.
The native adapter links unchanged `QuantumNumericalState.cc` from the fetched
base. It is a local audit executable, **not** a packaged GUI, importer or original
SDK execution. Exact/approximate worker flags are recorded per input.

Run1's two original 256-entry quantum-notation classifier literals rejected at
the existing nesting/complexity guard; full expressions/stderr remain in
`run-1/results.json`. Run2 established the route; Run3 uses existing ordinary calculator
`qexpect(qpauliword(...),matrix(...))`, which passes. Do not remove the guard or
describe the rejection as lack of numerical expectation support. Canonical
scalar re-entry also passes. No product failure was repaired or hidden. The independent Spec review found
that run2 had inverted the two classifier labels; run3 corrects the labels and
MSE target. Both earlier runs are retained; only run3 is final acceptance.

No prior DEV-11 fixture or result was edited. Its original286 expectations and
Partial status remain historical evidence, not rerun claims for this work.
Root README, untracked work, dist, retained DEV-13/AUD-02 and DEV-16 were not
modified or cleaned. No old DEV-11 checkout or blocked cleanup was retried.

## Reproduce and integrate

From repository root, with g++ and Python available (paths shown for this run):

```powershell
g++.exe -std=c++17 -O2 -I libqalculate docs/learning-evidence/dev12/ml-numerical-driver.cc libqalculate/QuantumNumericalState.cc -o F:/src/libqalculate/cleanup-audit/dev12-ml-20261102/ml-numerical-driver.exe
python docs/learning-evidence/dev12/ml-audit.py --worker F:/src/libqalculate/dist/releases/c575cb7e/QuantumStudio/quantum-worker.exe --native F:/src/libqalculate/cleanup-audit/dev12-ml-20261102/ml-numerical-driver.exe --sources F:/src/libqalculate/cleanup-audit/dev12-ml-20261102 --output F:/src/libqalculate/cleanup-audit/dev12-ml-20261102/run-new
```

Output directory must not exist. Fetch each manifest URL with curl to the
corresponding `ID.html`/`ID.ipynb`, plus `dataset_graph7.csv`, if restoring sources;
the runner rejects changed hashes. Preserve historical runs. The script imports
the existing `dev11/probe.py` numeric-output parser, already in source distribution.

Proposed additional source-distribution entries (Agent1 owns build integration):
`docs/learning-evidence/dev12/ml-audit.py`, `ml-numerical-driver.cc`,
`ml-audit.md`, `ml-source-manifest.json`, `ml-data-manifest.json`,
`ml-cell-ledger.json`, `ml-results-summary.json` (all under the same directory).

Proposed checklist wording: **DEV-12 remains Partial. ML source-boundary audit
inventories IBM096–100 plus IBM119/QB007; finite manual encoding/kernel/QNN and
diagonal-objective adaptations pass existing operations. Zero full source rows
certified; original SDK execution, training/performance, untested feature-map
families, scaling, media and hardware remain open.** Link this record from the
seven unchecked source rows without ticking them.

Merge/CI/publication belong to Agent1. Independent exact-head reviews and final
integration CI are recorded in the external handoff; this audit does not claim
those passed in advance. Available for an assigned desktop slot; no real GUI
validation or final combined package validation is claimed here.
