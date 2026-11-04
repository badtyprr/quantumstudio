# AUD-01: IBM-021 Simon finite native evidence

This package consolidates two reviewed native increments without adding acceptance:
**44 observations, 35 complete value/copy pairs and nine original rejections**.
It preserves the lesson's original n=3 input bits, m=5 output bits and secret011.
IBM-021 and AUD-01 remain open.

## Source and inventory

The [pinned official notebook](https://raw.githubusercontent.com/Qiskit/documentation/a500b17f8b1f156a6bba42ab11f90f3104cad6d4/learning/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/simon-algorithm.ipynb)
is from Qiskit/documentation revision
`a500b17f8b1f156a6bba42ab11f90f3104cad6d4`, Git blob
`6db27732a25e8c47911b1dc9a3d89f4f72499ea6`, 19,423 bytes, SHA-256
`2a53c7740281662c4c68fd9b3a9492c3615ea3bbfead3c0d3cce9f2fab698f7a`.
This is a retrieval of that immutable repository revision, not a claim about
historical cloud bytes or the body consulted for REL-26.

`source-inventory.json` retains the entire Markdown cell `e17fb8b5`: 177 math
occurrences (18 display, 159 inline), one image reference and one textual Figure.
There are zero code cells. All 179 records retain original text, offsets and
hashes. Inventory is not acceptance. The shipped inventory preserves its original
source-only classifications; execution dispositions are in the fixtures and
baseline summary, not silently written back as whole-source coverage.

Original table M029 maps inputs000..111 to five-bit outputs
`10011,00101,00101,10011,11010,00001,00001,11010`, respectively. REL-26 already
verified selected domain/image adaptations; the four-element image result is
not counted again here.

## Finite observations

| Group | Requests | Native observation |
|---|---:|---|
| Original bodies M045/M049/M050/M054/M060/M070/M074/M075/M088 | 9 | All reject; exact diagnostics retained |
| Typed preimages | 4 | Complete three-bit sets and ordinary copies pass |
| Output-register columns | 8 | All 32 entries, including zero columns and signs, pass |
| Measurement probabilities | 8 | Exact squared norms and copies pass |
| Initial, query and final joint states | 3 | All 256 entries and copies pass |
| Authored GF(2) controls | 12 | Ranks, complete kernel spans and candidate syndromes/copies pass |

The original literal attempts remove only outer display delimiters and add the
route prefix. Successful adaptations do not replace their rejections.

Finite expressions bind the original table and dimensions. Table lookup uses
one-based indexing of decimal output labels; typed preimages use `bitstrings(3)`
and `bitvalue`. Amplitude expressions retain native binary parity and explicitly
qualified output basis dimension32. Joint expressions use finite integer binders
0..7, qbits(width3) for parity, output basis32 and data basis8. These are disclosed
adaptations, not literal acceptance of unresolved source domains or functions.
No dense256-by-256 matrix or new parser/algebra operation is introduced.

## Independent expectations

The source preimages are19->{000,011},5->{001,010},26->{100,111},1->{101,110}.
Each pair differs by011, and the pairs partition all inputs. This checks more
than the already-released image cardinality.

For each data outcome y, the complete output-register column is
`T_y[z]=sum_{x:f(x)=z} (-1)^popcount(x AND y)/8`, z=0..31. Pairing w and w XOR011
independently gives the signed coefficients. The column is zero for001,010,101,110.
For y=000,011,100,111 it has four entries of magnitude1/4, with their signs and
positions retained. Thus p(y)=1/4 on those four allowed outcomes and zero elsewhere.
The zero columns are not normalized or postselected.

Joint index is **8*z+y**, with the five-bit output register leftmost. The initial
state has sqrt(2)/4 at rows0..7. The queried state has sqrt(2)/4 at rows
152,41,42,155,212,13,14,215, in input order. Final joint entries are T_y[z].
An independent XOR scatter and three exact Hadamard butterfly steps checked all
768 reference entries; independent review compared every native entry and copied
entry. No register-width reduction, numerical tolerance or global-phase fitting
is used. All values lie in exact Q(sqrt(2)).

GF(2) controls use deterministically authored rows100 and011, whose kernel is
{000,011}. A second matrix adds their XOR111 and a zero row. Rank and nullspace
are checked for both matrices, plus full two-entry syndromes for all eight
candidate secrets. The verifier compares the binary span and basis independence,
not a particular presentation. These are 12 authored controls related to
M126/M135, not actual sampled shots, original random-row instances, or evidence
for the sampling theorem.

## Reproduction and provenance

Run on one line:

```text
python probe.py --worker ACTUAL_WORKER --definitions MATCHING_DATA --source PINNED_NOTEBOOK --output FRESH_DIRECTORY
```

The probe is self-contained and uses Python's standard library. Worker runtime
DLL dependencies must already be on PATH. Optional `--worker-revision` records an
externally verified revision. No installation, SDK, build or GUI is invoked.
Each worker request has a20-second timeout.

The runner verifies all source-inventory intervals, original formulas and table
hashes before execution. It saves the exact probe and raw responses, and records
source, inventory, fixture, script, worker and definition hashes before/after.
Rejected originals pin return code and full diagnostic, normalizing CRLF to LF
only. Changed rejection behavior, including a newly accepted original, requires
review and fails the baseline replay. Wrong values, lost shapes, failed copies or
changed inputs/worker/data also fail. Zero exit means these finite observations
reproduced; it does not make the nine original rejections mathematical passes.

All matrix entries are checked from complete canonical text, including the
256-entry columns for which the worker omits its JSON cell array. Ordinary copies
consume the actual canonical output. Display rounding is not the exact oracle:
for example, displayed0.25 is backed by canonical1/4. Typed preimages retain
three-bit labels, and all exactness flags and dimensions are checked.

The two existing native runs used revision
`577dbb6572a9442e1d654e4b2264709f603d77ab`, worker SHA-256
`1d9fbc1e42a1b001d73665fee5f7cbf46df02fdf5eb180f9ebd73345bd1daff9`.
All recorded definition hashes remained unchanged. Each increment passed
independent Standards and Spec reviews. Source package base is
`7a0c6720143d3dc0e8250362d834b75ec6d141d1`; this does not relabel the worker revision.
`baseline-summary.json` identifies the actual native records and their hashes.
The consolidated packaged probe has not yet had a new native run. Recorded-output
verification reproduces all44 observations and detects injected unrelated
diagnostics, wrong joint-state entries and altered bit widths. These verifier
tests remain external and are not additional native acceptance.

External failed verifier attempts and synthetic fault injections are not native
baseline results. The pilot verifier's decimal parser was corrected and full
canonical rational entries checked. A joint-proposal synthetic test exposed a
missed original-copy execution failure; it was fixed before the native run.
Those attempts remain outside this shipped baseline, identified in the summary's
history. No failed native input is silently replaced or reclassified.

## Media, remaining scope and distribution

The original Simon.svg was recovered from the same pinned repository revision,
blob46fa8df5994bcee266b6ede0d5fb82af1e23e6de, SHA-256
`d310a30cf1768134b0105f0dfa757cc2346a1a41b6ab3e03fc42724a1e3d8e8f`.
It was rendered unchanged and independently inspected: only top n data wires
have Hadamards and measurements; bottom m output wires enter in zero, without
minus-state phase kickback. The source's algebra orders that bottom register
leftmost. Historical cloud-byte equivalence remains unverified. This separate
media interpretation does not establish calculator GUI or Figure rendering.

Remaining source notation, unrestricted dimensions/families, random sampling,
independence and recovery guarantees, classical lower-bound claims, actual GUI
Clipboard, saved sessions and whole-lesson acceptance remain open.

Proposed distribution is exactly these five files under
`docs/learning-evidence/aud01-ibm021/`: `README.md`, `probe.py`, `fixtures.json`,
`baseline-summary.json`, `source-inventory.json`. The coordinator owns their
Makefile/source-distribution registration, central coverage updates, final
packaged native replay, integration and releases. This increment edits none of
those shared controls.
