# QB013 original notebook replay

The restored runtime at `4c1e36d4a2f9782483232c6f80e4e91ebde3772d`
executes the pinned Cirq/Stim notebook's 17 original code cells, preserving all
24 source cells. The independent host audit accepts finite semantics and all
18 authored controls. [Evidence index](index.json) binds the external raw files.

The source remains pinned to qBraid revision
`86787e1ba372facc224f925189755e69c479828b`; its notebook SHA-256 is
`5b5ae29f1a5813111d1474d60a13aac6c06c2ef1904f75de73ec75a7224c8145`.
Authored controls are separate from original source acceptance. They compare
finite zero-input states and sample results; they do not prove all-input unitary
equivalence or hardware behavior. The ten original random samples are checked
for allowed support, not balance or coherence.

## Environment and outputs

Before/after inventories cover 31,735 files across the retained environment,
base interpreter and runtime. No files were added, removed or changed. The
76 installed distributions have 16,159 module files checked against available
package RECORD hashes. Their metadata/module inventories are identical. Exact
pins, Python requirements and 117 active dependency requirements, including
requested extras, pass. This reuses a retained environment; it is not a fresh
wheel installation or supply-chain authenticity claim.

Both graph PNGs were decoded and visually inspected. The second graph highlights
the added Cirq-to-Stim edge. Some central arrows overlap; exact edge mapping is
verified from captured conversion records. The original circuit display shows
H on q0, CX to q1, and measurements into the added meas register, leaving the
initial c register unused. The path query returns true and conversion returns a
Stim circuit, with the original barrier-removal warning preserved. Cell21 calls
`diagram()` inside an if block without displaying its return value; no displayed
diagram is claimed. Markdown content is preserved and read separately from code.

The Windows kernel belongs to the owned job. Final population is zero; cleanup
used forced termination and the launcher exited0. This is not a claim of graceful
cleanup, an app-integrated notebook UI, network isolation or Linux acceptance.

## Remaining gates

Independent review of these actual artifacts, hosted CI, packaging and release
verification remain open. QB-013, DEV-13 and AUD-04 remain unchecked. Earlier
failed replays and the two measurement-order/reference corrections remain in the
audit workspace; no failed evidence is overwritten or relabeled.
