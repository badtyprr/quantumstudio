# DEV-12 chemistry and diagonalization evidence

Scope: IBM-090–095 and IBM-108–113. Base fetched before checkout selection:
`753bf16df56aeae0f6454f89999ef203665755f6`, still origin/master at retrieval.
Released comparison: `checkpoint-c575cb7e`, revision
`c575cb7e70d8b952c18d0a297a7784e246c34381`. No historical evidence is replaced.

## Inventory and boundaries

The [manifest](chemistry-diagonalization-source-manifest.json) pins all 12 notebook
URLs, retrieval times and SHA256s. The [cell inventory](chemistry-diagonalization-cell-inventory.json)
indexes 422 cells, including 152 code cells, markdown code fences, headings,
equations and links. Counts are structural inventory, not successful execution.
The notebook payloads, original cell outputs, fetched source text and raw runs are
outside the checkout at `F:/src/libqalculate/cleanup-audit/dev12-chem-diag-20261102`.
**Zero of twelve whole source rows are certified.** Videos, figures, linked
papers, downloadable archives, interactive exercises and original SDK workflows
are not certified by this audit. Notebook endpoints were accessible; these other
surfaces were not executed or exhaustively inspected. In particular the IBM Box
molecule ZIP linked by IBM-109 remains untested.

| Source | Inventoried examples | Finite audit and remaining boundary |
|---|---|---|
| IBM-090 introduction | Motivation, goals, course structure | Text inventory only; no executable certification |
| IBM-091 VQE | H2, complex two-qubit Pauli Hamiltonian, efficient_su2, estimator, COBYLA, backend layout | Both literal Hamiltonians; no SDK, optimization, shots or hardware run |
| IBM-092 Krylov | 3x3 analytic, 5x5 iterative projection, seeded size/timing family, generalized problem, ten-spin time evolution/Hadamard tests | 3x3 and 5x5 matrices; explicitly adapted 3x3 overlap problem. Large family/timings, original ten-spin circuit, regularization and sampled overlaps untested |
| IBM-093 SQD overview | Two 8x8 matrices, four projected matrices, configuration selection/recovery | Original finite matrices/projections; no generic recovery algorithm or asymptotic claims |
| IBM-094 SQD implementation | N2 PySCF integrals, CCSD, ffsim LUCJ, hardware layout/sampling, fermion solve/configuration recovery | Inventory only; chemistry preprocessing, external packages and original large circuit untested |
| IBM-095 SKQD | 22-spin ring, Neel preparation, Trotter evolution, sampling, postselection, subsampling eigsh | Inventory only; no dense-limit increase or smaller-example substitution claimed as source success |
| IBM-108 introduction | Chemistry/VQE overview/video | Inventory only |
| IBM-109 Hamiltonians | Toy XX+YY+ZZ, H2 sto-6g, Jordan–Wigner creation/destruction, Cholesky, LiH, placeholder ethene geometry, OpenFermion conversion | Toy and printed four-qubit H2; no PySCF regeneration, LiH/ethene computation, package conversion or ZIP audit |
| IBM-110 ansatz | efficient_su2 variants, n_local, pauli_two_design and explicit 3/4-wire circuits | Inventory only; circuit capability exists but these original ansatz workflows are untested here |
| IBM-111 optimizers | Markdown minimize example; COBYLA/SLSQP/Nelder–Mead and stopping criteria | Shared optimizer ownership belongs to Agent 1; no new optimizer or global-optimum claim |
| IBM-112 ground state | Four-qubit H2, rx ansatz, estimator, transpilation, finite COBYLA, nuclear offset | Full literal Hamiltonian; local spectral reference only, no original optimization/provider execution |
| IBM-113 geometry | PySCF geometry-dependent Hamiltonians, repeated VQE and plots | Inventory only; neither geometry sweep nor molecular geometry minimum certified |

## Existing capabilities and demonstrated gap

`QuantumAlgebra`, `QuantumStabilizer`, `QuantumMatrixPower`, `QuantumMatrixExp`,
`QuantumEvolution`, state metrics and the numerical/exact circuit implementations
already provide Pauli construction, matrix products, adjoints, state expectations,
bounded matrix powers/logarithms/exponentials and circuit execution. Private
Jacobi solvers in matrix functions/state metrics do not expose eigenpairs.
All twelve selected matrix expressions (including the original four-qubit H2)
pass the released worker. A dedicated function name is not evidence that those
matrix operations were missing.

The gap is computing eigenpairs directly: attempted `heigenvalues(A)` and
`heigenvectors(A)` on the released public route produce nonnumeric implicit
products, despite process status zero. They are not numerical results and are
not described as explicit solver rejections. The fixture preserves the original
notebook cell including outputs, translated input, expected matrix and spectrum;
the result preserves argv, stdout, stderr, return code and binary hash. The
original source uses NumPy/SciPy eig/eigh, not these new product spellings.

Agreed ownership adds only `QuantumEigensystem.cc/.h` and
`src/quantum-eigensystem-test.cc`. Agent 1 owns parser aliases, Calculator
registration, build files, user-facing notation documentation and integration.
No allocation limits are raised. Existing private matrix-function algorithms are
unchanged. The complex Jacobi path returns exactly n orthonormal complex vectors;
it avoids treating the doubled real embedding as 2n independent complex vectors.

`qheigenvalues(A)` returns an n-by-1 ascending real eigenvalue column;
`qheigenvectors(A)` returns paired eigenvector columns. Inputs are finite numerical
Hermitian matrices of dimension 1–64. Outputs are explicitly approximate double
precision, reported at 12 digits even when calculator precision is larger.
There is no general non-Hermitian or generalized eigensolver API in this change.
The largest-magnitude component is phased positive real for reproducibility,
but vector phases and repeated-eigenvalue bases are not an API uniqueness promise.

Internal Hermiticity is tested after scaling by the largest real/imaginary
component, at 1e-12. Internal vector residual norms and pairwise orthonormality
errors must be at most 1e-10. These checks precede decimal output rounding and
are numerical acceptance criteria, not bounds on arbitrary input uncertainty or
relative accuracy of tiny eigenvalues. Nonfinite values, broad intervals,
non-Hermitian inputs, overflow and detected scaling underflow are rejected.

## Oracles, ordering, units and source discrepancies

The source probe uses NumPy/SciPy LAPACK independently of the C++ Jacobi routine.
Pauli construction is checked two ways: Kronecker products and independent
computational-basis bit action. Labels run left to right from most to least
significant bit; Qiskit qubit zero is the rightmost label. No implicit bit reversal
is applied. The mathematical matrices carry dimensionless numbers; chemistry
energy numbers are interpreted in hartree and geometry in angstrom per source.
The two-qubit XX+YY+ZZ illustration is not treated as a molecular model.

IBM-109 cell 23 starts from `ecore * identity`; cell 25's printed coefficients
match IBM-112 cell 2. The full sixteen-dimensional Hamiltonian includes the core
constant and, for this all-active H2 example, nuclear repulsion. Its rounded
coefficient spectrum gives total ground energy about -1.1459778447627311 Ha.
Subtracting 0.7199689944489797 Ha gives electronic energy -1.865946839211711 Ha,
consistent with the subtraction convention in IBM-112 cell 22. Adding that
constant again would double count it. The source's finite eight-decimal
coefficients are retained; no fresh PySCF integrals or higher-accuracy molecular
energy are claimed. The computational diagonal at binary 1010 is -1.12562866 Ha,
matching the printed Hartree–Fock total at its displayed precision. Do not infer
physical occupation labels solely from the binary ket without checking the
source creation/destruction convention.

IBM-092 cell 4 has eigenvalues 4-sqrt(2), 4, 4+sqrt(2). Cell 5's prose swaps the
first/last eigenvectors relative to their eigenvalues; the original remains in
the snapshot. Analytic residuals select the code-output pairing. IBM-093's rounded
matrix and stated normalized ket 0.8|011>+0.6|101> give expectation -0.535656 and
residual about 4.0792e-5, so the printed ket is not an exact eigenvector of those
rounded coefficients. Projectors/subspaces are compared rather than arbitrary
individual phases. A tiny displayed eigenvalue difference is not a new defect.

The generalized audit adapts IBM-092 cell 50 to its cell-4 matrix, with
K=[v,Av,A²v], v=(1,0,0), S=K†K and H=K†AK. S has eigenvalues approximately
0.003259586, 0.826541154, 371.170199261 and condition number 113870.357. Independent
`scipy.linalg.eigh(H,S)` checks generalized residuals and S-orthonormality;
the product's existing inverse square-root route whitens S before the ordinary
Hermitian solve. This is a full-rank finite adaptation; it does not test the
source's thresholded singular-overlap recovery or noisy ten-spin experiment.

Native analytic tests use scaled errors at 2e-10. Probe matrix comparisons use
absolute 2e-10 (2e-8 for the conditioned whitening adaptation); eigenvalues,
residuals and spectral projectors use 2e-8, orthonormality 2e-9 after serialized
output. These tolerances are separate from exact arithmetic. The audit does not
claim exactness from close floating-point agreement. A variational expectation
is bounded below by the ground energy for a normalized state and Hermitian H;
finite optimizer termination does not prove a global optimum, and this tranche
does not run a chemistry optimizer.

## Reproduction and validation status

Python oracle dependencies used: NumPy 2.4.6, SciPy 1.17.1, CPython 3.11 in an
external isolated environment. These are audit dependencies only.

```text
python chemistry-diagonalization-inventory.py --sources SNAPSHOTS --output inventory.json
python chemistry-diagonalization-probe.py --worker RELEASE/quantum-worker.exe --sources SNAPSHOTS --output NEW_RUN --baseline
python chemistry-diagonalization-probe.py --worker CANDIDATE/quantum-worker.exe --sources SNAPSHOTS --output NEW_RUN
```

Run from this evidence directory or use full script paths. `--fetch` on the
inventory tool retrieves into a new source directory and rejects hash drift.
The source probe creates a new output directory and does not overwrite runs.
It executes only constructed calculator requests, never downloaded notebook code.

Released baseline: 12 matrix constructions, 12 norms and 12 expectation values
passed; all 24 attempted eigen operations lacked numeric eigenpair results
(`baseline-4`, extending `baseline-3` with norms/expectations). Initial harness
attempts are retained: baseline-1 demanded an overly strict 1e-14 Hermiticity
check on numerically whitened data (observed skew 2.6e-13); baseline-2 omitted
the worker's large-matrix copy-text route. Both were harness corrections, not
product fixes. Initial manual shell probes omitted the definitions path and
quantum prefix; they are not counted as capability failures.

Candidate tests, exact-head independent review and required CI results are
recorded in the final handoff. Product registration/build integration, packaged
validation and serialized GUI testing belong to Agent 1's integration process.
No release or whole-lesson completion is claimed by this scoped evidence.
