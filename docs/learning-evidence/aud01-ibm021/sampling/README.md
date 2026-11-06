# IBM021 sampling and rank reference evidence

Coordinator-assigned documentation package base:
47668f733467260233b1aa6e65b4abc42c3c0b26. Original reference analysis base:
874c0f9588fd827dbaa6110ceb863e4da7f1c411, comparison integration:
985faaeeedf80e8e3c4a7430c08f930b16d9e12c. These historical bindings are preserved
unchanged in bindings.json. No product, central checklist, worker, SDK, GUI or
release changes. This evidence establishes independent exact mathematical
expectations, not native sampling acceptance.

## Source and bindings

The original official notebook is pinned at Qiskit/documentation revision
a500b17f8b1f156a6bba42ab11f90f3104cad6d4, path
learning/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/simon-algorithm.ipynb.
SHA256: 2a53c7740281662c4c68fd9b3a9492c3615ea3bbfead3c0d3cce9f2fab698f7a.
Original cell e17fb8b5 has 177 mathematical occurrences, one image and one text Figure,
zero code cells. Existing source-inventory.json remains the whole structural inventory.
source-claims.json adds exact original paragraph intervals and hashes; it does not
replace that inventory. Offsets are Unicode codepoints, end exclusive.

The n=3,m=5,s=011 table [19,5,5,19,26,1,1,26] is original source data.
For each measured y, independently sum squared exact Walsh amplitudes over all
32 output labels. This gives probability1/4 on 000,011,100,111 and zero elsewhere.
All additional secrets, short sample sequences, invalid data and n=1 controls are
disclosed authored extensions. Rows use high-to-low bits; integer4 is 100.
The original function table uses high-to-low input labels in ascending order.
Previously validated joint-state indexing was 8*z+y; no register-order change.

## Exact independent expectations

Assume ideal independently repeated circuit executions with the promised function.
Outcome support is a binary vector space of dimension d=n for zero secret, and
d=n-1 for nonzero secret. For k independent uniform rows, full-support rank has
probability0 if k<d, otherwise product(i=0..d-1, 1-2^(i-k)). Empty product is1.
This exact formula is our derivation, not an original displayed formula.
Proof: choose coordinates in the support. Columns of the resulting uniform k*d
binary matrix are independent uniform vectors; column i must avoid the 2^i
vectors spanned by the previous columns out of 2^k possibilities.

Independently, each nonzero linear functional annihilates k rows with probability
2^-k. Union over 2^d-1 functionals bounds failure by (2^d-1)/2^k. At k=n+r,
r positive integer, this proves the original lower bound1-2^-r. For r10,
1023/1024 > 999/1000, establishing the claimed greater-than99.9% rank success.
All arithmetic here is exact rational/integer; no numerical tolerance applies.

reference.py independently enumerates all ordered samples for n1 and n3, every
secret and k0..4 (50 cases,7104 sequences). It compares the complete rank histogram
with a rank-transition count: at rank j, 2^j next rows preserve rank and 2^d-2^j
increase it. Separately420 cases cover n1..12, both secret cases, k0..n+10,
comparing the recurrence against the product and checking the claimed bounds.
These finite checks corroborate the proof; they do not replace its assumptions.

## Finite proposed acceptance contract

1. Retain explicit n and row bit order; reject values outside0..2^n-1, booleans
   masquerading as integer samples, inconsistent row widths or malformed tables.
   Empty sample lists are valid evidence of no observations, not a fabricated row.
2. Return rank and the full GF(2) nullspace (or equivalent independent basis).
   Repeated, dependent and zero rows do not falsely increase rank. Source controls
   [100,011] and [011,111,100,000] have rank2 and kernel{000,011}.
3. Distinguish insufficient_rank (kernel size>2), nonzero_candidate (size2),
   and zero_candidate (size1). Candidate means an inference from samples under
   the stated assumptions, not an unconditional proof about an unknown oracle.
   The rows[100,011] can arise under s000, in which case candidate011 is wrong.
   At n1,s1,k0 the conditioned rank event succeeds but zero queries cannot solve
   both possible promises; no universal zero-query recovery claim is made.
4. Promise validation is available only when the complete function table is
   supplied, not inferred from samples. Constant n3 tables, multiplicity3 and
   out-of-range m-bit outputs are invalid controls. A known secret is used only
   by reference verification, never passed to a proposed inference procedure.
5. Exact distribution/support and rank probabilities must match this oracle.
   Actual sampling, random independence, noise, SDK behavior and GUI interactions
   require separate future execution; no arbitrary seed or stochastic score is
   made a golden exact result. Nonuniform or correlated rows invalidate the iid
   formula. Pure reference calculations do not establish sampler independence.

## Scope and dependencies

No failing native reproduction or missing parser/algebra operation is demonstrated
by this work. Existing qbitdot and GF(2) rank/nullspace routes already cover the
earlier finite controls. Do not introduce a parser feature or label this DEV05
completion on this evidence. General symbolic widths remain a separate contract.
This six-file documentation package occupies
docs/learning-evidence/aud01-ibm021/sampling/. Native tests should reuse the existing
finite operations and only expand after reproducing a concrete gap. A future
sampler/decoder API requires a separate product design and explicit file scope.
Notebook execution must be coordinated with the notebook lane. Any native or
GUI run requires a new reservation; actual Clipboard and saved-session gates
remain open. No Linux regression work is duplicated here.

Existing35 value/Copy pairs and9 original rejections are historical finite native
evidence, not new sampling observations. This reference has no native failing
reproduction, implementation, product regression or newly accepted formula.
General families, other original notation, original Figure rendering, classical
complexity lower bounds and whole-lesson acceptance remain open.

The source's classical lower-bound sentence needs a worst-case or explicitly
distributed input interpretation. It cannot apply to every promised input: a
constant-guess algorithm succeeds on inputs with that secret. The source labels
its following discussion intuition, not a proof. Our rank counts do not verify
the classical lower bound or repair the source's unspecified quantifier.

## Reproduction and reviews

Validation: reference.py exit0, reference-results.json exact receipt. The external staging packet preserves the script, bindings, claims, result and
original plan-review record byte for byte. Git normalizes CRLF to LF in
source-claims.json, reference-results.json and reviews.json; distributed copies
therefore have different byte hashes but identical JSON content. Historical
hashes in reviews.json identify the retained external raw files, not normalized
Git blobs. reviews.json certifies the original plan's five hashes, including PLAN.md
(external original); it is not a review of this adapted README. Final package
reviews are separately retained by the integration owner.

The retained reference.py is a historical standard-library audit script with an
absolute SOURCE path, recorded in bindings.json. It reads only pinned notebook
bytes and writes source-claims.json and reference-results.json beside itself.
Run a copy of the script in a fresh output directory with Python3.10 or later on
the retained audit host, where the recorded source path exists. Compare generated
JSON semantically with the retained files: Windows text writes may use CRLF.
For another host, provision the exact source at that path or make a separately
identified path-only adaptation; do not relabel modified script bytes as the
original receipt. No third-party packages, native worker or SDK are required.

Source snapshots are external prerequisites, not included in these six files.
The source SHA256 is asserted before any reference calculation. Package scope is
README.md, bindings.json, source-claims.json, reference.py, reference-results.json
and reviews.json. Distribution registration, integration and coverage updates
belong to the coordinator. No source-original formula acceptance or release is
implied by this package.
