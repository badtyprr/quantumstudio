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
