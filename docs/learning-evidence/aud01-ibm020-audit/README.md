# AUD-01: IBM-020 source inventory and finite analysis audit

The first Deutsch–Jozsa analysis section has 46 math occurrences:8 display blocks
and38 inline occurrences. The remainder inventory covers the complementary
source regions with 122 more occurrences,15 display and107 inline. Together they
inventory 168 occurrences without duplication. An earlier coordination proposal
said 49 for the first section; that was a counting mistake, not three additional
formulas. The pinned source offsets and hashes remain authoritative.

Pinned [original notebook](https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm.ipynb)
SHA-256: `513398ae77d7502e7e8c2f2d4bdc85d4a7b5474d25f88a00eb1a2e8a8777586f`.
The first section is cell 0 `17463a96`, character interval [2760,7763), with no
code or diagrams inside that interval. `inventory.json` retains every original,
offset and occurrence hash. Its classification is an inventory, not a passed
coverage ledger. The original inventory file hash is retained separately.

The remainder includes the prelude, classical-query argument, implementation,
Bernstein–Vazirani discussion and final remarks. `remainder-inventory.json`
retains 122 formulas, 8 original code cells, 1 source image reference, 3 stored-output
image references and 2 textual Figure containers. Reference hashes are not image
byte hashes or visual inspection. `remainder-analysis.md` is an independent
source-only mathematical review; references there to planned first-section
checks predate the native results below and do not claim native execution.

## Exactly what was executed

| Cohort | Requests | Observed outcome on frozen worker 3fdf7ebd |
|---|---:|---|
| Original unmodified display/expression bodies | 10 | Nine reject; M09 remains a deferred tensor power. None is counted as complete literal acceptance. |
| G1 extracted/adapted terms | 14 | Twelve exact full-value checks pass; two width-erasing scalar-set adaptations fail. |
| G2–G4 finite adaptations | 150 | All exact full-value checks pass. |
| Explicit dimension/domain controls | 10 | All pass, including bindings after copying a deferred expression. |
| Deferred typed-domain expressions | 2 | Both retain their domain through ordinary copying; their later numerical bindings are among the controls. |

The 186 fixture records do not represent 186 original source examples. Successful
numerical values have 172 ordinary canonical Copy/re-entry checks; the two
deferred contexts have separate copy checks. The original deferred tensor power
also receives an unverified copy observation in the reusable runner. Source
[repetition M24](../aud01-ibm020-repetition/README.md) is linked as prior finite
evidence and contributes zero new requests here. No source occurrence is silently
dropped because another route passed.

G2 comprises 52 matrix/column requests: all entries of n=2/n=3 Hadamard tensor
matrices, and all four finite forms of each corresponding source column. G3
comprises 66 full-state requests: two preparations, 16 phase expressions, 16 double
sums, 16 explicit oracle-permutation cross-checks and 16 final-layer cross-checks.
The latter 32 are authored operator controls, not extra source equations. G4
comprises 32 probability requests: source scalar sums and full-state marginal
controls for all 16 two-bit Boolean truth tables.

`fixtures.json` records each source occurrence, input or dependent-copy template,
transformation and full expected result. Copy-dependent fixtures consume actual
native canonical output, not a hand-written substitute. Bit strings are ordered
with x0 least significant and ancilla leftmost. Truth-table characters mean
f(00),f(01),f(10),f(11), in that order. Explicit dimensions, finite sum/ellipsis
expansion and integer-label conversions are disclosed adaptations.

## Independent expectations and limits

For N=2^n, the full Hadamard matrix entry is
`W[y,x]=(-1)^popcount(x AND y)/sqrt(N)`. This follows from independent scalar
Hadamard entries. Let s_x=(-1)^f(x), and w_y=sum_x s_x(-1)^popcount(x AND y).
At n=2, the initial, queried and final amplitudes at row 4b+y are respectively
`(-1)^b sqrt(2)/4`, `(-1)^b s_y sqrt(2)/4` and `(-1)^b w_y sqrt(2)/8`.
The oracle-control input is independently constructed as the permutation
`|b,x> -> |b XOR f(x),x>`; it is not a native-generated oracle claim.

Every coefficient, dimension and global sign is compared in the exact rational
field Q(sqrt2). No numerical tolerance or phase alignment is used. Constant-one
and constant-zero functions have opposite full-state signs even though their
probabilities agree. All data marginals are retained in the fixture reference.
Eight tables satisfy the promise (two constant, six balanced); the other eight
have zero-data probability 1/4 and receive no promised classification claim.
The full-string dimension expansion for n=2 avoids duplicating overlapping
endpoint notation in the source's written indexed family.

The two failed G1 adaptations replaced Sigma with ordinary scalar set {0,1} and
thereby discarded binary width. Their failures remain `mathematical_pass=false`.
Adding dimension 2 works. Existing complete-integer-range binders also supply
that dimension. Alternatively, typed `bitstrings(1)` supplies width, and
`bitvalue` supplies the scalar used in a phase. Both context routes pass without
changing global bare named-ket semantics. No new parser API is proposed.

An initial harness incorrectly reparsed canonical deferred output through
quantum notation again and rejected. The actual ordinary copy route retains it
and permits later domain binding. Both failed and corrected attempts remain in
the external evidence referenced by `baseline-summary.json`; they are not
reclassified as a native regression. The original full derivations' ellipsis,
aligned syntax and unresolved context still have separate unsupported outcomes.

## Reproduction and acceptance gates

Run `probe.py --source PINNED_NOTEBOOK --worker ACTUAL_WORKER --output FRESH_DIR`.
The script uses Python's standard library, verifies notebook/occurrence hashes,
and records source, fixture, script, worker and definition hashes. Optional
`--definitions` supplies data; `--worker-revision` records an externally verified
revision. No translator, installation or build is performed.

A zero exit means the finite audit reproduced its documented observations with
no unexpected failures. It does **not** turn the two failed primary value
attempts or nine literal rejections into mathematical passes. Results retain
those statuses separately; any unrelated diagnostic or incorrect full value
fails the run. Each original fixture pins its return code and diagnostic; M09
also pins its deferred shape and canonical text before and after ordinary re-entry.
A changed literal outcome requires review, including a newly accepted expression.
These baseline comparisons are observation checks, not mathematical acceptance.
Old-worker evidence is 3fdf7ebd, SHA-256
`d72b59ef52188cbf7b1603daecbe03649eec7f1e8e31d712d9e1de2d337cee12`.
Later combined-worker replay, independent final reviews and actual GUI/session
acceptance remain pending. Coordinator owns registration and central coverage.

The notebook lane separately executed all 8 original code cells at this same
source hash, with unchanged cell text/order and a disclosed seed 0 preamble;
its oracle/Walsh/count witnesses and offline replay are not native literal
acceptance. The source-code on_states list is not itself the final oracle truth
set: the actual X/MCX/X gates trigger complements, and the notebook witness follows
the gates. The remainder review also preserves the with/without-replacement
sampling qualification instead of silently rewriting the source probability.

IBM-020 and AUD-01 remain open. Finite n=2/n=3 values do not prove unrestricted
native symbolic families. Remaining literal notation, Bernstein–Vazirani native
acceptance, source images/media, historical claims and complete application
workflows are not certified by these cohorts.
