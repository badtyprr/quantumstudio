# DEV-10: symbolic domains, sets and indexed families

Development in progress from `95b0e34448bebfe2260b087728df74a44fdd86ea`.
No implementation, merge, release, or whole-lesson completion is claimed here.

## Source-driven scope

The pinned catalog is `docs/learning-source-inventory.json` (2026-10-14).
Its URLs identify lessons, not immutable body revisions. The following bodies
were consulted on 2026-11-01; do not label these newly retrieved bodies as the
2026-10-14 snapshot.

* [General formulation: multiple systems, opening section](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/multiple-systems):
  density matrix indices use Cartesian products of the component classical sets.
  The partial-trace section also uses a sum indexed by `b` in `Gamma`.
* [Fundamentals: query model, Description of the model and Examples](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/query-model-of-computation):
  source inputs include `x in Sigma^n`, with `Sigma={0,1}`, and the image
  `{f(x):x in Sigma^n}`. These require symbolic widths and indexed images.
* [Fundamentals: Simon's problem and Analysis](https://quantum.cloud.ibm.com/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/simon-algorithm):
  the displayed eight-input function has four distinct outputs; its analysis
  sums over binary strings with an unresolved width.

The Basics multiple-systems classical-information lesson is a supplementary
definition of Cartesian tuples, not a replacement for the requested sources.

## Scoped change A: unresolved equality

Source membership `x in Sigma^n` is diagnostically reduced to `member(x,Σ)`;
`Σ` represents the not-yet-specified domain. The first baseline used `S`, which
is the phase gate in quantum notation and therefore was an invalid adaptation;
the corrected `Σ` probe also fails, with the finite-flat-vector diagnostic.
`member(x,vector(y))` and
`cardinality(vector(x,y))` are authored equality witnesses. They are not literal
lesson expressions. Independent expectation: membership remains a proposition
until equality is known; a two-entry set has one element if its entries coincide
and two if they differ. A sum over that set likewise must not count an uncertain
duplicate twice. Empty sets have zero elements and singleton sets one.

Released `e5ed358a` observations: both membership witnesses error; cardinality
returns 2 and the sum returns `x+y`, losing the equality condition. Root evidence
`cleanup-audit/dev10-baseline.json` records original inputs, exact output, worker
hash and revision. Failing fixtures: `src/quantum-domains-test.py`, added before
implementation. Includes substitution, copy/re-entry, empty/singleton, known
duplicates and nested binder controls.

DEV-05a-e are released prerequisites; this equality change needs no additional
register-width implementation. Symbolic widths, Cartesian alphabets and indexed
families are subsequent required scopes, not covered by this change. DEV-09's
fourth tetrahedral conditional state and all existing whole-source boundaries
remain unresolved and unchanged.

## Scoped change B: Cartesian alphabets and indexed images

Failing source-adapted fixtures were committed as `764b8041` before implementation
in `src/quantum-cartesian-test.py`; released-worker failure is retained as
`cleanup-audit/dev10-cartesian-red.log`. The wider baseline also records symbolic
binary width, nonbinary alphabet and symbolic integer-range failures.

Adaptations and independent expectations:

| Source location/input | Executable adaptation | Independent oracle |
| --- | --- | --- |
| General formulation, Multiple systems: Cartesian product of component state sets | `cartesian(vector(0,1),vector(2,3,4))` | Six ordered pairs; `(1,4)` belongs, `(4,1)` does not. Concrete alphabets are authored dimension witnesses. |
| Same general Cartesian requirement | `cardinality(\{0,1,2\}^{2})` | Nine ordered pairs; the ternary alphabet and repetition are authored controls. |
| Query model: `Sigma={0,1}`, `x in Sigma^n` | `\{0,1\}^n`; then substitute `n=3` | Preserve the width condition until known; eight strings at width three. Replaces the prose-defined alphabet with its literal definition. |
| General formulation ensemble indices `0,...,m-1` | `\{0,\ldots,n-1\}` | Substitute three to obtain three indices; zero yields the empty set. `m` renamed `n`. |
| Query model minimum: `{f(x):x in Sigma^n}` | `setimage(k%2,vector(0,1,2,3),k)` | Authored concrete function and scalar-index adaptation: image `{0,1}`, size two. This is not a full oracle or algorithm execution. |
| Simon's problem: eight displayed function outputs | `setimage(bitstring(k,5),vector(19,5,5,19,26,1,1,26),k)` | Decimal transcription of original five-bit outputs; four distinct strings, retaining width. No input circuit is claimed. |

Other tests are authored edge and scope witnesses: zero-fold products contain
one empty tuple, a positive power of the empty set is empty, a singleton power
is singleton, tuples preserve order, image binders shadow nested indices, and
invalid counts/probes reject even when another field remains symbolic.

The required DEV-05 prerequisite extension is narrowly the symbolic domain of
binary strings and deferred integer ranges. It does not complete general
register-width equations or expand numerical state-vector limits. Pending domain
descriptors retain validity constraints rather than replacing them with an
unconditional cardinality formula. Concrete materialization remains bounded.

Follow-up reproductions within change B:

* The query model's parity example filters an alphabet with a predicate.
  The authored reduction `cardinality(\{k\in\{0,1\}:k=x\})` errored in
  `select()` before filter implementation. Fixtures were committed as `c257f5fc`;
  `cleanup-audit/dev10-filter-red.log` retains the error. Independent expectations
  are one element at `x=0` and zero at `x=2`; otherwise retain the predicate.
* A generated singleton Cartesian set copied as its lone tuple; a constant
  image copied as its scalar. The literal `\{7\}` also copied as `7`.
  `dev10-singleton-copy-red.log`, `dev10-literal-singleton-red.log` and
  `dev10-literal-fixture-red.log` preserve those observations. Explicit set
  descriptors retain empty and singleton collections through copy/re-entry.
* Existing nested-filter/intersection parser fixtures caught a regression from
  introducing typed image results. Set union/intersection/difference now accept
  those descriptors and preserve unknown equality. These operations preserve
  existing notation compatibility; no additional whole-source coverage follows.

Intermediate validation failures are retained outside the checkout. One
unoptimized native TeX test process overflowed its Windows stack; subsequent
native tests use the release's `-O2` compilation setting. A build made near edits
was explicitly excluded from exact-input evidence; later development builds use
immutable input snapshots. Development GUI previews use the released e5ed358a
GUI with a development worker and are not packaged-release evidence.

The v9 development snapshot passes 112 Cartesian/family checks in exact and
approximate modes, 76 equality checks, 2178 general worker checks, 249 TeX,
100 indexed and 1523 parser-integration checks. Four parser expectations were
updated from vectors to typed sets; expected members remain unchanged. A GUI
preview passed 33 checks including actual Copy, re-entry and session save/open.
Its first attempt encountered Windows clipboard lock `0x800401D0`; that failure
is retained. The driver now retries only that lock or stale clipboard content,
at most ten attempts, and reports its count. The successful retry used zero
clipboard retries. These observations remain development validation, not a release.

A final singleton audit reproduced loss of set type for the zero-width binary
alphabet `\{0,1\}^0` and singleton range `\{3,\ldots,3\}`. These are authored
boundary adaptations of the binary alphabet and integer-family source forms,
with independent cardinality one (the empty binary word and integer 3).
Fixtures were committed as `f4f3f95e` before correction; the failure is retained
in `cleanup-audit/dev10-singleton-red.log`. Binary alphabets and integer ranges
now return the same typed set descriptor, including empty reversed ranges.
The v10 immutable development snapshot passes 124 Cartesian/family checks,
249 TeX, 100 indexed and 1523 parser checks. Three direct range expectations
now assert typed sets with the same members. Actual preview GUI validation
passes 43 checks, including both singleton copies, with zero clipboard retries.
These are development observations; final packaged validation remains pending.

Independent Spec review of `02dafd38` caught a compatibility regression:
`unique(bitstrings(1))` and three-argument legacy multiset operations rejected
typed domains. Failing fixtures were committed as `f061fae9`; retained log:
`cleanup-audit/dev10-vector-compat-red.log`. The notation adapter now unwraps
set descriptors only at legacy `unique`, `select` and optional-multiset call
boundaries, preserving those builtins' vector validation and duplicate rules.
The v12 immutable worker passes 136 Cartesian/family checks. The full v10
worker regression passed 2178 checks before this compatibility correction;
v12 regression and exact-head review/CI are separate gates.

The follow-up Spec review reproduced singleton copy loss after
`unique(qindexrange(3,3))`; failing fixtures `a4c3d340` and
`cleanup-audit/dev10-legacy-singleton-red.log` precede the correction.
A result adapter preserves typed-set results of `unique` and `select` when
their source is a typed set, including empty and singleton outputs. Genuine
vector inputs retain their vector behavior. Explicit three-argument multiset
operations continue to return vectors so that requested multiplicities survive;
these are multiset operations, not the two-argument set operations.
The immutable v14 worker passes 148 Cartesian/family checks in both modes.

The next independent Spec review found that typed `unique` and `select` still
rejected unresolved equality/predicates. Fixtures `5076fe9c` and the retained
`dev10-legacy-symbolic-red.log` record that failure. Typed unique now preserves
the canonical set; typed select uses the conditional-aware filter (including
pending index ranges). Genuine vector inputs and explicit first-match select
retain legacy behavior. Copy parsing avoids wrapping an existing compatibility
adapter twice; v15's failed copy test is retained. Singleton set display now
renders braces even after presentation formatting collapses its inner vector.
The immutable v18 worker passes 174 focused Cartesian/family checks, including
unknown predicates, pending ranges, default predicates and first-match controls.

Required native CI on `e6bb0dc6` failed an existing notation rejection fixture:
`|\{0,1\}>` was accepted after the literal-set descriptor changed. The merge
guard stopped; no merge or release occurred. The complete job log is retained
as `cleanup-audit/dev10-e6bb-native-ci-failure.log`. Collection recognition now
includes the typed domain constructors, preserving the existing distinction
between set cardinality bars and ket syntax. Immutable v19 passes all 526
notation checks and 174 Cartesian/family checks. Full worker/native/GUI v18
results precede this parser correction; final-head CI and final packaged tests
are required separately. No failed CI result is represented as a passed gate.

## Scoped release-gate correction

The clean PowerShell 7 build at `a950cdd0` stopped in the existing exact
rotation-chain test: 70 native tests passed, one existing thread test skipped,
and one test exceeded its 20-second subprocess ceiling. The failure and original
suite summary remain in `cleanup-audit/dev10-release-initial-rotation-chain.log`
and `dev10-release-initial-test-suite.log`. No package was published.

An isolated run reproduced the same first-request timeout on both the new worker
and released DEV-09 worker `e5ed358a`, using identical request bytes, data and DLL
settings. Diagnostic runs with a longer ceiling completed in 25.06 and 24.06
seconds respectively. These diagnostic completions are not passes of the
original 20-second gate. The saved request SHA-256 is
`331905f963ba8dc9d5521e336192ef0e55d510e0b85abb816d034163ac187ab8`.

The test now allows 60 seconds for exact-circuit evaluation on Windows, retaining
the four cancellation cases, their independent identity/probability oracle and
the `1e-10` numerical tolerance. Linux keeps its 20-second ceiling, and numeric
readback keeps its existing timeout. Packaging additionally runs this test on
the actual packaged worker. This is a test scheduling margin, not an algorithmic
performance improvement. Product sources are unchanged by this correction;
review, CI and accurately recorded build resumption are still required.
