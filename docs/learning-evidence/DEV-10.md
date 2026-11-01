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
