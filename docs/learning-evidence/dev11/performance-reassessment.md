# DEV-11a current-baseline performance reassessment

The historical finite exact matrix-multiplication issue is already resolved in
the tested current baseline. No product patch, global reassociation, new release,
measurement feature or named partial-trace implementation is part of this work.
Both fresh serial runs pass all 286 original fixture expectations and eight cost
controls: **588/588 comparisons, zero timeouts**.

## Baseline and ownership

Fetched baseline: `2fb33c4d4` (2026-11-02). It already contains
`f8747a1f6`, the finite exact numeric zero-skipping optimization merged by PR #416.
The released worker used here is `52c37a2abe8fce9770ad610f56bd5118a1d4bc39`,
SHA-256 `ea0467a5ca5ce58d043c08bed80043361aca4305a5bb92d029781e4035e76913`.
Its recorded release hash was verified before execution. The diff from that
release to the fetched baseline changes only three documentation files and
`Makefile.am` distribution entries, with no runtime source or build-option change.
The hash-verified released source archive also matches 272 available runtime,
test and data files in the checkout, normalizing Windows line endings.

The coordinator reserved `MathStructure-calculate.cc` for this workstream.
`QuantumAlgebra.cc` remains subject to coordination; neither file was changed.
DEV-17 retains its named-trace files. The coordinator owns central checklist,
shared distribution registration and release integration. Root README changes,
existing releases and retained DEV-13/DEV-16 work were preserved.

## Fresh serial worker measurements

Host: Intel Core i5-7600K, four cores/four logical processors, Windows 11 Pro
10.0.22631, about 32 GiB RAM, High performance power plan. The published native
build uses MSYS2 UCRT64 GCC 16.2.0, `-g -O2`, static libqalculate, no curl/ICU/NLS.
These are elapsed single-host measurements, with background desktop applications
present and no fixed CPU-frequency or thermal control. Heavy builds were held
until both serial runs finished. One mid-run `Win32_Processor` snapshot reported
100% load; its process inventory contains no compiler or make process. This is
not an idle-host benchmark. Host/process snapshots and full logs are retained.

Each worker starts in a fresh process with its packaged definitions. Timing ends
immediately after process completion, before independent output validation.
It includes startup, definitions, parsing, construction, evaluation, formatting
and pipe capture. The original 90-second fixture limits and 12-second diagnostic
limits are unchanged; neither is a universal performance contract.

| Control | First run (s) | Second run (s) |
|---|---:|---:|
| `qidentity(512)` alone | 1.694 | 1.638 |
| Nine-qubit Y alone | 1.699 | 1.630 |
| `qidentity(512)*qidentity(512)` | 3.114 | 3.074 |
| Nine-qubit Y square | 3.087 | 3.014 |
| Nine-qubit X square | 3.335 | 3.030 |
| Trace of identity square | 1.648 | 1.531 |
| Trace of Y square | 1.682 | 1.538 |
| Trace of X square | 1.722 | 1.535 |

All full-matrix controls match every independently generated identity/Pauli
entry with zero residual. Trace results are exactly `512`. Every successful
fixture reports `approximate=false`. The original 12 timed-out left-associated
Shor fixtures complete twice in **5.492–6.420 seconds**, without changing their
expressions. Both complete logical columns, leakage and one common global phase
are compared; separate column phases are never allowed. Radical-output comparison
uses the existing independent numeric oracle at tolerance `1e-12`.

Each repetition retains 280 supported results and the same six intentional
capacity/syntax/invalid-input rejections. Rejections require exit code 2 and the
specific expected diagnostic. The two rejection-oracle unit tests also pass.

The historical worker timed out on identity/Y/X squares and trace-Y at 12 seconds.
Those observations remain in [the original follow-up](performance-followup.md).
This is a fresh verification of the already-released implementation, not a new
patched-versus-unpatched A/B experiment or a claimed speedup ratio across builds.

## Native cost separation and correctness

The dedicated clean build of the fetched baseline passes **316 quantum-algebra
checks**. Existing regressions compare complete products to an independent scalar
reference that includes every zero term: sparse operands on either side, dense
controls, rectangular products, fractions, complex signs, cancelling sums, zero
matrices, symbolic values and positive/negative infinity. Precision-bearing zero
entries are tested on both sides. Full 512-dimensional identity, singleton/scalar
behavior and incompatible dimensions are covered. The cancellation test verifies
pre-aborted evaluation restores the operand and permits retry; it does not prove
interruption latency or every mid-operation cancellation point.

The released optimization excludes matrix/row/cell and Number approximation or
precision metadata, non-numeric cells and real/imaginary infinity. Each output
cell retains its original inner-index summation order. No unrestricted symbolic
reassociation is introduced. Independent source review found no concrete defect
in these scoped boundaries.

The six serial phase cases all pass full exact 512-by-512 identity comparisons.
Immediately before this run, host load was reported as 1%, no compiler/make or
worker process was present, and DEV-17/AUD-01 explicitly held their jobs.

| Operands | Repetition | Construct both (s) | Copy/multiply/evaluate (s) | Native print (s) |
|---|---:|---:|---:|---:|
| Identity | 1 | 0.492575 | 0.745946 | 0.179721 |
| X Pauli | 1 | 0.527290 | 0.758398 | 0.176679 |
| Y Pauli | 1 | 0.494746 | 0.737021 | 0.177253 |
| Identity | 2 | 0.495413 | 0.721360 | 0.172568 |
| X Pauli | 2 | 0.498042 | 0.695414 | 0.172552 |
| Y Pauli | 2 | 0.497698 | 0.696282 | 0.172915 |

The standalone [phase probe](matrix-cost.cc) times two translated constructor
evaluations, then result copy/multiply/evaluate, then `MathStructure::print()`.
Definitions loading and complete exact identity validation are outside those
intervals. All six cases run serially in one process with one calculator and no
discarded warmup. Native print timing is not the worker's complete JSON formatting
cost, and these stage intervals should not be subtracted from fresh-worker times.

## Reproduction and evidence

[Serial runner](reassess-performance.py), [all fresh run records](reassessment-run.json.gz)
and [summary/provenance](reassessment-results.json).
Full stdout/stderr and provenance are outside the disposable build clone under
`F:/src/libqalculate/cleanup-audit/matrix-performance-20261102/`.
The executed runner is preserved there with its hash. Its integer controls used
the original `1e-12` comparison; the committed runner tightens those controls to
zero residual. All 10 full-matrix control results have zero residual, so the
recorded output also satisfies the stricter comparison without another timing run.

```powershell
python docs/learning-evidence/dev11/reassess-performance.py `
  --worker F:/src/libqalculate/dist/releases/52c37a2a/QuantumStudio/quantum-worker.exe `
  --sha256 ea0467a5ca5ce58d043c08bed80043361aca4305a5bb92d029781e4035e76913 `
  --output F:/src/libqalculate/cleanup-audit/matrix-performance-new
```

Use a new output directory. Run serially without concurrent compilation. The
runner returns failure for any timeout, wrong output, crash or wrong rejection.

The exact native build commands, configuration, binaries' hashes and raw stage
output are retained as `build.sh`, `config.log`, `native-manifest.json` and
`phases.tsv` in the external evidence directory. Native executables, the executed
harnesses, changed files and non-ignored untracked files/patches have verified copies
at `D:/Archives/libqalculate-recovery/matrix-performance-20261102/`.
All checkout refs already exist in the main repository. Automatic approval review
blocked removal of `.tools/finite-matrix-performance` with “blocked by policy”;
the clone remains, with `recovery.json` explicitly recording `removed=false`.
The managed `codex/finite-matrix-reassessment` worktree retains the review commits.

## Integration proposal

Keep DEV-11a released; link this current-baseline reassessment rather than queue
another finite matrix optimization. DEV-11 overall remains Partial, with zero
whole source rows certified. No other workstream or source-coverage status changes.
The coordinator must register the new reproducibility files in `Makefile.am`
`EXTRA_DIST`. Final review status and exact paths will accompany the handoff.
