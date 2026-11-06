# IBM024: measuring computational cost — finite reference evidence

This documentation package is prepared against integration base
`78bf6cf7fb6ca52c884320cc7ec2a53958627109`. It combines reviewed source accounting,
exact finite reference calculations, six pinned repository figures and their
reviewed visual/wiring audit. It establishes no new calculator, SDK, GUI or
release acceptance, and does not mark the lesson complete.

## Source and provenance

The [official notebook](https://raw.githubusercontent.com/Qiskit/documentation/a500b17f8b1f156a6bba42ab11f90f3104cad6d4/learning/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/measuring-computational-cost.ipynb)
is pinned to Qiskit/documentation revision
`a500b17f8b1f156a6bba42ab11f90f3104cad6d4`. Its SHA256 is
`554cc9694595ec167fb501776310e6bfdfe0a87a5c638d2c79ba8a4fdf09bbcd`,
38,061 bytes, Git blob `64cad0ea97326a7b997b171ae529a15a46322312`.
The original notebook is an external prerequisite and is deliberately not copied
into this package. The complete original cell text remains in the
[source inventory](source/inventory.json), joined by exact text offsets/hashes.

The [source manifest](source/manifest.json) records the upstream source identity;
[media locators](source/media-locators.json) join each image reference to its exact
repository path, size and Git blob. The six SVGs in [assets](assets/) are the
unchanged acquired originals, not reconstructed diagrams. Acquisition used only
those six immutable public URLs and verified size/Git blob/SHA256. Its separately
retained manifest is `0dd8a62ad176057577dfef7c6cfe7d9057a8137abd60032353c728d16d6572b2`.
No equality with historical or current IBM cloud-served image bytes is claimed.

The [figure audit](figures/REPORT.md) explains the observed diagrams and finite
interpretations. Its [render manifest](figures/render-manifest.json) binds each
original SVG to a derived PNG, renderer versions and command. PNGs use 180 dpi on
white; they are disclosed viewing derivatives. Original labels/wires were viewed
by the author and independent reviewers. This packaging step does not rerender or
reinterpret them.

## What the evidence covers

The notebook has one Markdown cell and zero code cells. The inventory accounts
for 170 math occurrences (8 display, 162 inline), six SVG references, four textual
problem Figures, 17 headings and two tables. Contextual variables count as math
occurrences; 170 is not a count of executable acceptance cases.

[Source research](source/research.md) and [reference results](source/reference-results.json)
retain 2,258 exact comparisons: nine original encoding-table rows, 256 authored
four-bit additions, 97 authored binary-length boundary occurrences, 528 authored
signed Euclidean divisions and 1,368 authored modular-power cases. Exact integer
oracles use distinct calculation methods; there is no floating tolerance.
The nine ambiguous `0^0` cases are omitted. Empty string, numeric zero, empty set
and the singleton containing the empty word remain distinct. Earlier released
zero-width evidence is reused in the source research, not claimed as a new feature.

[Diagram checks](figures/check-results.json) separately retain four XOR cases,
four half-adder cases, eight full-adder cases and all 256 pairs of four-bit inputs,
with fixed five-bit outputs. This is an authored transcription of the inspected
wiring, checked against ordinary integer arithmetic. It is not original notebook
code or native calculator execution. These 256 additions are a separate model
from the source-reference additions, not additional native coverage.

For the pictured four-bit construction, gate counts are 73, 31 and 17 under the
three disclosed gate/fanout conventions. Least-significant-first weights in the
addition picture are inferred from preceding prose and wiring, not printed wire
labels. Conceptual computation and local deferred-measurement diagrams are kept
separate from Boolean truth-table acceptance. Finite checks establish neither
optimality nor arbitrary-width or arbitrary adaptive-circuit correctness.

## Historical records and reproduction

The 23 supplied source/figure/asset files preserve their external packet bytes;
this README is new. Historical reports intentionally retain their original bases,
absolute audit-host paths, relative sibling references and preparation wording.
For example, source research says media was uninspected at that checkpoint;
the subsequent figure audit records its inspection. Source and figure packets
later passed independent Standards and Spec reviews, retained outside this
24-file package. Those reviews do not automatically review this new README or
its eventual integration. Their hashes and all origins are bound in the external
package manifest for the integration owner.

Git text normalization may convert CRLF to LF. Historical hashes identify retained
external raw files, not necessarily the normalized Git/distribution copies.
Compare JSON content semantically where line endings differ; never relabel a
changed-byte file as the original raw artifact. SVG/PNG identities in the render
manifest remain bound to the original acquisition and rendering records.

Reproduce in a new directory, not in these retained evidence directories:

- Copy [reference.py](source/reference.py) and provide the exact original notebook
  beside it as `source.ipynb`; the script checks its SHA256 before calculation.
  Run with ordinary Python 3.10 or later and compare its newly written
  `reference-results.json` to the retained result. Script-byte and newline changes
  must be recorded separately because the result includes the script hash.
- Copy [check.py](figures/check.py) into a different fresh directory and run normal
  Python, without `-O`: its checks use assertions. It writes `check-results.json`
  beside itself and records its script hash. It transcribes an already reviewed
  diagram; running it alone does not inspect or prove the original SVG wiring.
- [render.cjs](figures/render.cjs) is a historical host-bound renderer: it imports
  Sharp from an absolute Codex runtime path and reads the external acquisition
  directory and exact acquisition manifest. Those dependencies are not included
  here. Copy it to a fresh output directory before any authorized reproduction;
  it writes the six PNGs and render manifest beside itself. On another host,
  identify any path-only adaptation separately and retain renderer versions and
  new output hashes; do not claim changed renderer bytes or pixels equal the old
  record. The retained script rejects its listed active/external SVG references
  before rasterizing the pinned buffers; this is not a general sanitizer claim.

No reproduction was run merely to package these files. The source reports'
`source.ipynb` link refers to the external original; the figure report's sibling
`ibm024-source-analysis` reference refers here to the packaged `source` directory.
Historical absolute paths in manifests are provenance records, not portable
installation paths. Acquisition receipts and independent review reports remain
external evidence, not missing implied files in this package.

## Remaining scope

Calculator notation/routes, native values and Copy/re-entry, actual Clipboard,
saved sessions and relevant GUI acceptance remain separate. No failing native
reproduction or new parser/algebra defect is established by this packet.
Universality, deferred measurement, general circuit families and uniformity,
asymptotic bounds, contemporary algorithm/timing claims and whole-lesson
interpretation require their own source-backed evidence. Finite examples cannot
certify these claims. Distribution registration, checklist reconciliation and
integration review belong to the coordinator; master merge and release remain
separate states.
