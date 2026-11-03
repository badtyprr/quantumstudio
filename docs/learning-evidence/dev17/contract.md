# DEV-17: named subsystem partial traces

Implementation and validation are in progress; this is not a release claim or a
whole-lesson audit. The central checklist remains owned by the coordinator.

## User contract

`subsystems(matrix, [A,B], [2,3])` attaches an explicit ordered mapping to a square
matrix. The first label names the leftmost tensor factor; the last factor varies
fastest in the computational basis. Names do not imply positions or dimensions:
`[B,A]` binds B to the first factor. Labels are case-sensitive literal identifiers
of 1–64 ASCII letters, digits and underscores, starting with a letter. They may
be quoted. Gate names, constants, function names and assigned scalar variables
do not change their meaning in label positions. `AC` is one label, not A and C.

Dimensions are positive integers, one per label, whose product equals the square
matrix dimension. There are 1–32 factors and at most 512 matrix rows. Dimensions
of one are permitted. A mapping does not assert positivity, unit trace or a
physical density matrix; the operation is the linear partial trace of a matrix.

`ptrace(subsystems(matrix,[A,B],[2,3]),B)` traces **out B**, retaining A. A list such
as `[B,C]` traces out both; its order does not reorder the output. The remaining
factors keep their original relative order. The equivalent source operator form
is `\operatorname{Tr}_{\mathsf{B}}(subsystems(matrix,[A,B],[2,3]))`. Multiple labels
are comma-separated, for example `\operatorname{Tr}_{\mathsf{B},\mathsf{C}}(...)`.
An empty selection retains the input matrix; tracing every factor returns the
ordinary scalar trace, consistently with explicit-dimension numeric traces.

Scope is the value, with no global label registry or implicit declaration based
on surrounding prose. Evaluating a declaration preserves its matrix, ordered
labels and dimensions together. Copy of that declaration must re-enter as the
same mapped value; saved sessions preserve it in the expression/history. Mapping
two separate values with the same names is allowed; they cannot affect each
other. Nesting a declaration around an already mapped value is rejected, even
if the two mappings are equal. Numeric selectors and additional dimension
arguments on a mapped value are rejected, avoiding mixed conventions.

A trace result is an ordinary matrix (or scalar when all factors are removed),
without mapping metadata. Copy/re-entry of that result preserves the full exact
value, not an implicit declaration. To chain named traces, explicitly attach a
new mapping to the result, using only its retained factors and dimensions. Using
an old name directly on the ordinary result is an error. This intentional
boundary also avoids guessing metadata for general matrix arithmetic.

Unknown selected names, duplicate declared names, duplicate selected names,
incompatible dimensions, invalid identifiers and conflicting nested mappings
produce specific errors. Existing numeric `ptrace(matrix,indices,dimensions)`
remains available independently.

## Source and independent expectations

Primary source: [IBM-005, Multiple systems and reduced states](https://quantum.cloud.ibm.com/learning/en/courses/general-formulation-of-quantum-information/density-matrices/multiple-systems),
sections **Reduced states and the partial trace** and **An alternative
description of the partial trace**. The source operator prefix is preserved;
explicit numeric matrices and mapping declarations adapt prose definitions.
This does not execute the complete original lesson or its linked notebook.

Original failure, with no mapping (must never acquire an implicit B-to-1 rule):

```text
\operatorname{Tr}_{\mathsf{B}}([1/2,0,0,0;0,0,0,0;0,0,1/4,1/4;0,0,1/4,1/4])
```

The Bell marginals are `diag(1/2,1/2)`, because tracing either orthonormal factor
removes the cross terms. The asymmetric source mixture is half `|00><00|` plus
half `|1+><1+|`: tracing the first factor gives `[3/4,1/4;1/4,1/4]`, and tracing
the second gives `diag(1/2,1/2)`. Neither result is inferred from calculator
output. Product controls use independently normalized outer products and tensor
products; surviving basis digits specify the expected projectors. A correlated
2-by-3 control uses an independent Python basis-contraction sum with rational
arithmetic. Tests compare every cell and the matrix shape, not just trace or
normalization.

## Evidence and integration

Original workspace evidence is outside disposable checkouts at
`F:/src/libqalculate/cleanup-audit/dev17/`. `baseline.py` / `baseline.json` record
16 complete exact numeric matrices and the original named rejection on released
revision `52c37a2abe8fce9770ad610f56bd5118a1d4bc39`, worker SHA-256
`ea0467a5ca5ce58d043c08bed80043361aca4305a5bb92d029781e4035e76913`.
This is baseline evidence, not validation of DEV-17 implementation.

The isolated branch is `codex/dev17-named-traces`, based on fetched upstream
`2fb33c4d435adaf3518b5c79da38392030c957ce`. The coordinator confirmed ownership of
QuantumNotation, QuantumTeX as needed, QuantumSubsystem and dedicated tests/docs;
shared build registration, central checklist, CI integration and release remain
with the coordinator. Root README/dist and retained DEV-13/DEV-16 work are outside
this change. No cleanup or publication is authorized by this implementation.

Validation entry points:

- `src/quantum-named-subsystem-test.cc`: native exact values, immutable metadata,
  symbol conflicts and error contracts.
- `src/quantum-named-subsystem-test.py --worker PATH --output REPORT --revision SHA`:
  full rational matrix checks, renamed/permuted mappings, mixed dimensions,
  multiple traced factors, evaluated declaration Copy/re-entry and result copies.

Pending: compilation, exact-head regressions, real GUI entry/Copy/session
reopening, independent Standards and Spec reviews, central integration and
released-artifact validation. Symbolic dimensions, named symbolic matrix
identities, set-indexed sums, block-matrix syntax and notebook execution remain
outside this finite feature.
