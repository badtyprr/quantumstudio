# DEV-11: error-correction lesson operations

Current scoped delivery is publicly verified in [c575cb7e](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-c575cb7e); historical DEV-11a release evidence is retained below.
**DEV-11 remains Partial:** all 16 source rows are inventoried, but zero rows
are certified as fully audited. The 286 executable adaptations do not equal
whole-source coverage. See the [source inventory](dev11/primary-inventory.md),
[example map](dev11/source-map.json) and [remaining scoped tasks](#remaining-work).

## Current scoped delivery: DEV-11b/c and parallel audits

Verified release [c575cb7e](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-c575cb7e), revision `c575cb7e70d8b952c18d0a297a7784e246c34381`, integrates reviewed PR #419 and
PR #420, including the unchanged reviewed DEV-11e/f commit from PR #421.
DEV-11 remains **Partial: 16 source rows inventoried, zero whole rows certified**.

- **DEV-11b:** separate compact Pauli values preserve exact phases and ordering
  without dense 18-qubit matrices. The adapted 3×3 torus passes commutation,
  exactly two dependencies, rank 16, dimension 4, distance 3, all 54 one-site
  syndromes and noncontractible logical-loop relations. Independent group
  enumeration and all 1,431 weight-one/two errors establish the finite result.
  [Contract, conventions and oracle](dev11/compact-toric.md).
- **DEV-11c:** existing numerical execution handles transversal CNOT on two
  encoded Steane blocks. All four complete columns, relative phases, leakage
  and a complex witness pass 163,910 native comparisons at tolerance 1e-12.
  No dense limit was raised. [Routes and adaptation](dev11/steane-transversal.md).
- **DEV-11d:** 60 finite full-state/channel cases and 35 GUI assertions cover
  jointly degenerate ZZ measurement and a disclosed known-site three-qubit
  discretization/recovery adaptation with an entangled reference. This is not
  execution of the original nine-qubit Shor instrument.
  [Instrument evidence and limits](dev11/instrument-audit.md).
- **DEV-11e/f:** 216 manual diagram cases, 50 actual unitary serializer/importer
  round trips, 1,920 expanded Shor recovery adaptations and 24 exact scalar
  examples pass. Dynamic diagram suffix imports/GUI, general topology/decoders,
  larger families, noisy gadgets, threshold certification, media and proofs
  remain open. [Diagram audit](dev11/diagram-audit.md),
  [remaining source ledger](dev11/remaining-source-triage.md).

Separate Standards and Spec reviews passed on the exact integration head;
required CI and guarded merge parent/tree checks passed. GitHub refused the
separate #421 merge because its base was behind master; its exact reviewed
commit was instead included unchanged through the current-base #420 merge.
The final merged revision passed all required CI before publication.

PowerShell 7 native validation: Fresh clean native build and tests; no resumption. The package run
passed **73 native tests, one existing skip, zero failures/errors**. Actual packaged validation preserved all 286 original
expectations (280 supported plus the same six verified rejections), all 405
exact compact results and serialized re-entries, 52 compact GUI assertions
with nine independent clipboard comparisons, and 40 Steane GUI assertions
across five import/save/reopen/export/execution cases. The final instrument
and e/f audits also ran fresh against the packaged binaries and final source.
Thirteen specifically identified final captures were inspected. File-dialog
interaction is not claimed. All payload/ZIP entries and both anonymous public
archive downloads matched their tested hashes and sizes. The first anonymous
download returned HTTP 404; retrying the same published assets succeeded.
Both publication attempts remain preserved.

The development native run had 71 passes/one skip plus two separately run new
targets; it is not mislabeled as the final clean combined run. Launcher setup
failures, an initial supplementary Automake setup failure, and Steane GUI
harness failures remain preserved. The GUI harness compared JSON property
order incorrectly; structural comparison retained full circuit/source checks.
No failed candidate was published. Exact toric arithmetic uses no tolerance;
Steane amplitude comparisons are numerical at 1e-12. Sampling is supplemental.

Windows ZIP SHA-256: `2a42415bec616bed4174cf1e1e39bdf0b7a82ae6982a3a3d2326b3baf3f1d7d9`.
Source archive SHA-256: `0bf9f2b6ce8619ec90d65c8b419d2bf932a4ccc7e20e1a94269253f120a137f0`.
[Machine-readable release and provenance](dev11/dev11bc-release-summary.json).
Full evidence remains outside disposable checkouts in
`F:/src/libqalculate/cleanup-audit/dev11bc-20261102/`.

Historical DEV-11a evidence below is retained unchanged. Dense 14/18-qubit
constructor rejections are still intentional and are not counted as new
supported fixtures. DEV-09's unresolved symbolic tetrahedral conditional case
and DEV-10's documented limits remain unchanged.

## Historical DEV-11a implementation and review

[PR #416](https://github.com/badtyprr/quantumstudio/pull/416), merge `17388f64`,
implements DEV-11a: exact finite numeric matrix products visit nonzero
contributions while preserving each output cell's inner-index order. Symbolic,
non-finite, approximate and precision-bearing operands retain the existing path.
Dimensions, singleton handling, cancellation, signs and complex values remain
covered. Aborting evaluation restores the original operand; subsequent evaluation
is tested. No global reassociation or unconditional omission of zero times infinity.

[PR #418](https://github.com/badtyprr/quantumstudio/pull/418), merge `214e6866`,
fixes the actual GUI Copy/re-entry blocker found during release validation:
a 512-by-2 Shor result exceeded the ordinary parser budget. Explicit matrix
entry lists now share 4096 nodes; each entry keeps 512 nodes. Nested lists cannot
reset the allowance, arithmetic after the list uses the ordinary budget, and
input length, expanded length and nesting limits remain. This is bounded support,
not unlimited matrix serialization. The native translator keeps its 32768-byte
input limit; the GUI enforces its existing 32000-byte UTF-8 input limit.

Both changes received separate Standards and Spec reviews with zero outstanding
findings, all three required CI checks, and guarded merges with actual parents
and trees verified. Spec review caught an initial allowance extending past the
closing list; that was corrected and regression-tested before merge. Exact heads,
CI links and binary provenance are in [release-summary.json](dev11/release-summary.json).

## Source evidence and results

The original pinned inventory contains 16 Foundations rows IBM-053 through
IBM-068, 88 headings, 118 displayed-equation blocks and 61 image references.
Official notebooks contain markdown and linked media, not executable code cells.
Locations, adaptations, independent expected results and original inputs are
retained in [fixtures.json.gz](dev11/fixtures.json.gz) and the source map.
Parameterized proofs, original diagrams, linked videos/slides and wider families
remain explicit audit surfaces. Fetching notebooks does not certify them.

| Run | Supported | Timeouts | Capacity | Syntax | Valid invalid-input rejection | Expectations passed |
|---|---:|---:|---:|---:|---:|---:|
| Original released 35d9e753 audit | 268 | 12 | 2 | 1 | 3 | 274/286 |
| DEV-10 packaged 7d8b5c15 reassessment | 253 | 27 | 2 | 1 | 3 | 259/286 |
| Final packaged 214e6866 | 280 | 0 | 2 | 1 | 3 | 286/286 |

All source fixtures retain their original 90-second limit and unchanged input
expressions/independent expectations. The current-release reassessment overlapped
other local work: its counts describe observed host behavior, not an isolated
benchmark or a replacement claim about the historical 268/12 run. Every one of
its six rejection diagnostics was independently checked against exit 2 and the
specific expected error. Crashes and unrelated errors cannot satisfy rejection
expectations.

All 280 successful final results report `approximate=false`. Independent numeric
comparison of exact printed radicals uses tolerance 1e-12. Recovery compares both
complete logical columns and leakage, allowing only one common global phase.
The finite tables include 70 syndrome columns plus 60 repetition-code partition
cases, all 16 two-qubit Pauli CNOT conjugations, repetition/phase encoding, Steane
CSS cosets/encoder and logical X/Z/H/S, and Shor logical X/Z. These are algebraic
adaptations, not certification of original circuit imports or encoded two-block
Steane CNOT.

Separate 12-second diagnostics confirmed the Shor bottleneck on DEV-10: original
left association timed out twice while right association completed in 7.128/5.669 s;
the 512-dimensional identity square also timed out. Development exact sparse
multiplication completed the paired forms in 7.812/8.246/8.232/7.795 s and identity
in 4.159 s. Those single-host timings are not universal performance contracts.

## Release validation and failure history

The first clean candidate 17388f64 passed 71 native tests (one existing skip),
its package gates and 286 source expectations, but failed actual GUI Copy/re-entry.
It was withheld and never published. Its 94 archived build, source-audit and GUI
evidence files, including the exact copied matrix and GUI failure, were
hash-verified under `cleanup-audit/dev11-20261102/candidate-17388/`. Subsequent
red/minimized parser probes remain in the parent audit directory.

The corrected release used a new checkout and the established PowerShell 7
packaging environment. Its native run was fresh and uninterrupted:
71 passes, 1 existing skip,
zero failures/errors. Final package checks include 316 algebra assertions,
538 notation checks, 2180 general worker checks, and all standard packaging gates.
Standalone diagnostic O0/default-stack notation runs overflowed; larger-stack
and optimized tests passed. Those diagnostics are preserved separately and are
not represented as successful package runs.

After the clean build, the source-audit launcher failed before executing any
fixtures because it attempted to write Unicode through Windows CP1252. The
launcher was corrected to write UTF-8, its partial output and failure were
preserved, and the source audit then ran fresh. The already-passing clean
build, payload audit and packaged GUI results were retained, not rerun.

Actual packaged GUI validation passed 28 checks: Calculate, Copy/re-entry,
session save/open through application serialization, source syndrome,
operator-assumption guard and invalid replacement, incompatible dimensions,
noncommuting generators, signed Pauli multiplication and minimum layout.
Four copied matrices were independently checked in full, including both 512-by-2
Shor outputs. Six captures were visually inspected. File-dialog interaction is
not claimed. Application and worker hashes were checked before and after testing.

The final payload manifest and ZIP entries were checked byte-for-byte;
388 payload files and 389 ZIP files. Required CI also
passed on the merged release revision. Both public release downloads were read
anonymously and matched their local SHA-256 values and sizes. The first immediate
public fetch returned HTTP 404; a retry succeeded before verification was recorded.

- Worker SHA-256: `42126088fd76b9dfa5c7787f9bf66a6429c1baa0985ca9543b508322d4dc955d`
- Windows ZIP SHA-256: `401ee642a5d1a180e4955444c383785ce3d148ea9371e910a6ed5821b598b19c`
- Source archive SHA-256: `c3908cc3ffd8344ed96c4fd5ab7526b62011ca791c0269552cd55d2a6befbbe7`

## Reproduction

`dev11/probe.py` remains pinned to the historical audit. For this final release,
use `dev11/probe-release.py` with the extracted worker, pinned source snapshots,
and a new output directory. Its worker hash and source hashes are mandatory.
For example, from the repository root with the pinned snapshots already present:

```powershell
python docs/learning-evidence/dev11/probe-release.py --worker F:/src/libqalculate/dist/releases/214e6866/QuantumStudio/quantum-worker.exe --sources F:/src/libqalculate/cleanup-audit/dev11-20261101-a7c4/sources --output F:/src/libqalculate/cleanup-audit/dev11-recheck-214e6866
```

The final raw output is [results-release.json.gz](dev11/results-release.json.gz);
DEV-10 reassessment is [results-dev10-reassessment.json.gz](dev11/results-dev10-reassessment.json.gz).
The pinned inventory runner revision is separately recorded from the product
revision. Offline replay must not be described as fresh execution.

Automated product regressions: `src/quantum-algebra-test.cc`,
`src/quantum-notation-test.cc`, and `src/quantum-worker-test.py`.
The strict audit rejection contract is covered by `dev11/test_probe.py`.
External full evidence and capture files remain in
`F:/src/libqalculate/cleanup-audit/dev11-20261102/`.

## Remaining work

DEV-11a and scoped DEV-11b/c are released. Finite DEV-11d/e/f audits are
recorded above; the wider task remains open:

- General toric decoding, L=9/source topology and larger code families.
- Original nine-qubit Shor instruments and broader arbitrary-error recovery.
- Remaining original circuit/media cases, dynamic diagram suffix import and GUI.
- Fault-tolerance gadgets, physical thresholds and parameterized proofs.

The variadic `tensor(X,Y,Z)` spelling was an invented adaptation, not an original
source feature: nested binary/Unicode tensor forms pass. The 14/18-qubit
constructor rejections remain intentional finite boundaries. DEV-09's unresolved
fourth tetrahedral conditional state for `|i>` and DEV-10's documented domain
limits are unchanged. DEV-13/AUD-02 and DEV-16 retained work was not modified.
