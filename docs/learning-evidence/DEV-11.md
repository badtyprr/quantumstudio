# DEV-11: error-correction lesson operations

Scoped implementation is merged and publicly verified in [214e6866](https://github.com/badtyprr/quantumstudio/releases/tag/checkpoint-214e6866).
**DEV-11 remains Partial:** all 16 source rows are inventoried, but zero rows
are certified as fully audited. The 286 executable adaptations do not equal
whole-source coverage. See the [source inventory](dev11/primary-inventory.md),
[example map](dev11/source-map.json) and [remaining scoped tasks](#remaining-work).

## Implementation and review

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

DEV-11a is released; the following scoped tasks remain open with acceptance in
the [inventory queue](dev11/README.md#ranked-development-and-audit-queue):

- **DEV-11b:** compact 18-qubit toric Paulis/checks, dependencies, distance,
  syndromes and logical loops. Dense constructor capacity is a confirmed limit.
- **DEV-11c:** encoded two-block 14-qubit Steane transversal CNOT; investigate
  existing compact/circuit execution before adding a representation.
- **DEV-11d:** jointly degenerate stabilizer instruments and coherent recovery,
  including entangled-reference/channel witnesses. This is an unaudited surface,
  not a confirmed absence of the released DEV-09 instrument capabilities.
- **DEV-11e:** transcribe and independently check original encoder/syndrome
  diagrams and wire conventions; validate import/export when used.
- **DEV-11f:** remaining code families, toric decoder, fault-tolerance gadgets,
  thresholds, parameterized proofs and linked media. Split confirmed failures
  into individual implementation tasks with original reproductions.

The variadic `tensor(X,Y,Z)` spelling was an invented adaptation, not an original
source feature: nested binary/Unicode tensor forms pass. The 14/18-qubit
constructor rejections remain intentional finite boundaries. DEV-09's unresolved
fourth tetrahedral conditional state for `|i>` and DEV-10's documented domain
limits are unchanged. DEV-13/AUD-02 and DEV-16 retained work was not modified.
