# DEV-12: finite regularized-overlap composition

The existing native operations solve seven authored analytic adaptations of
IBM-092 cell50, including strict overlap cutoff, singular overlap and complex
rotation. No new native API is needed for this finite contract. Whole IBM-092
and DEV-12 remain partial; original sampled ten-spin and provider execution,
noise/conditioning families, near-cutoff perturbations and full notebook/media
coverage are outside these checks.

Pinned [original notebook](https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/quantum-diagonalization-algorithms/krylov.ipynb)
SHA-256: `524d48804ce536442b4329b818413ca7cda14304fcdf6a42c764b1b2dbdada8e`.
Cell50 SHA-256: `6627022329dcd5d84bcc48b479eeee7766cf6ce143e31b9017ab88bef48e08c8`.
The probe requires that exact local notebook, verifies both hashes and retains
its original cell text. It does not execute notebook imports or provider code.
The original function returns eigenvalues and optionally retained dimension,
not eigenvectors. Our lifted vectors are additional independent witnesses.

## Composition and independent expectations

1. Compute the overlap eigenvalues and paired eigenvector columns natively.
2. Use native `select` with strict `>` to select column indices. The host does
   not select indices or supply an expected retained basis.
3. Gather those columns with `processm`, reduce H/S, and whiten the positive
   reduced overlap using `qpower(Sr,-1/2)`.
4. Solve the whitened Hermitian matrix with native eigenvalues/eigenvectors,
   then lift its vectors to the original coordinates.

A singleton reduced product serializes as a scalar through ordinary arithmetic.
Use existing `qmul(A,qbasis(0,1))` to retain its known1×1 shape before the native
eigensolver. This is a disclosed shape-preserving construction, not a scalar
bypass of the eigensolver. Native-selected singleton index and gathered column
are preserved without manually choosing the basis.

| Authored case | Expected retained dimension | Expected spectrum |
|---|---:|---|
| Full rank2 | 2 | 3,5 |
| Zero overlap3 | 2 | 3,5 |
| Below cutoff1/4 | 1 | 3 |
| Equal cutoff1/4 | 1 | 3 |
| Above cutoff1/4 | 2 | 3,4 |
| Coupled discarded direction | 2 | 3,5 |
| Complex unitary rotation | 2 | 3,5 |

Diagonal H/S ratios supply independent expected spectra. The complex case is
an authored unitary conjugation of the diagonal problem; the coupled case adds
only couplings to the discarded direction. The script records every complete
input matrix, native request/result and ordinary canonical Copy/re-entry.
No equality of arbitrary eigenvector phases is assumed.

Exact identities are X† S X=I and U†(H X−S X Λ)=0. Finite output comparisons
use absolute tolerances2e-8 for spectra, projected residuals and copied entries,
and2e-9 for S-orthonormality, with relative tolerance zero. Shape and strict
cutoff decisions are checked separately. The coupled case intentionally has
nonzero full residual outside the retained subspace; it must not be rejected
for that reason. These are finite numerical checks, not exact symbolic proofs.

## Authored domain policy

The audit prevalidates finite matching nonempty square Hermitian H/S, a finite
nonnegative cutoff and positive-semidefinite S. Hermiticity and PSD tolerance
is1e-12. This is an explicitly authored audit policy, not a new native public
validator and not a claim about the original SciPy function's behavior.

Nine policy checks cover shape mismatch, nonfinite input, non-Hermitian H/S,
indefinite S, negative/infinite cutoff and two empty retained spaces. Invalid
preconditions stop in the audit harness. Empty selection is computed natively;
the harness reports `no overlap eigenvalues exceed cutoff` before attempting a
zero-dimensional matrix. The original source's incidental exceptions and
triangular/indefinite behavior are retained separately in the coordinator audit,
and are not promoted into acceptance criteria.

## Reproduction and evidence

Run `regularized-overlap-probe.py` with a Python environment containing NumPy,
`--worker` pointing to the actual worker, `--source` to the pinned IBM-092
notebook, and `--output` to a fresh evidence directory. `--definitions` overrides
the worker-adjacent data directory. No translator is used. Output records source,
cell, script, worker and definition hashes; no package installation is performed.

Initial external evidence uses worker3fdf7ebd, SHAd72b59ef, distinct from source
inspection baseline02d5ca3f. All seven compositions and84 stage/copy pairs pass;
maximum projected residual6.3e-16 and S-orthonormality error2.3e-16. The reusable
script passes all nine policy checks and90 native stage/copy pairs, including
native empty-selection checks and authored prevalidation checks.
Evidence is retained in `cleanup-audit/math-lane-20261104/dev12-composition/`.

Earlier ordinary1×1 matrix attempts failed because the constructor collapsed to
scalar. Those attempts, a diagnostic scalar-only workaround and direct route
controls remain preserved. The final native route resolves the harness shape
problem using existing operations; no native eigensolver defect is claimed.
The coordinator's unchanged-original-function execution is separate in
`cleanup-audit/coordinator-20261104/dev12-regularized-overlap/`.

Independent final review, later combined-worker replay and actual GUI/session
acceptance remain pending. Coordinator owns distribution registration, central
coverage updates, integration and releases.
