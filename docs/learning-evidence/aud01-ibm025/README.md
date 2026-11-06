# IBM025: simulating classical computations — finite evidence

This package records reviewed source accounting and finite mathematical checks,
plus eight pinned diagrams and their visual/wiring audit. It is prepared against
integration base `88f58b9123c5d67da2425c6ccaff0dda039d70ab`. It establishes no
native calculator, SDK, GUI, release or whole-lesson acceptance.

## Source and media provenance

The [official notebook](https://raw.githubusercontent.com/Qiskit/documentation/a500b17f8b1f156a6bba42ab11f90f3104cad6d4/learning/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/simulating-classical-computations.ipynb)
is pinned to Qiskit/documentation revision
`a500b17f8b1f156a6bba42ab11f90f3104cad6d4`. Its 14,004 original bytes have SHA256
`ec06bb65c2b394c9d5053a3dcbcf9407972a8fdca1fed4f0de8c357e91a72df7`
and Git blob `7060659cf1b57309a9119cb95a46ae2a7b9e0b09`. The notebook itself is
an external reproduction prerequisite, not a file in this package.

The [source inventory](source/inventory.json) retains the complete Markdown cell
and exact Unicode intervals and hashes: 91 math occurrences (4 display and 87
inline), eight image references and seven headings. There are no code cells.
Occurrences are source-accounting units, not executable acceptance cases.
[The source manifest](source/manifest.json) and [original locators](source/media-locators.json)
preserve the earlier acquisition identities and uninspected-media checkpoint.

The eight unchanged SVGs in [assets](assets/) were subsequently acquired from
their exact paths at the same pinned revision. All 395,390 bytes matched their
repository sizes and Git blobs. The separately retained acquisition manifest is
`6377ceb37b0e164ac2c89905360ca3946bcbd00e9e6ae2cec0314b98cd9e8ad7`.
This does not establish equality with historical IBM cloud-served images.

The [render manifest](figures/render-manifest.json) records original SVG identities,
derived PNG hashes, renderer versions and command. The eight PNGs are disclosed
180-dpi, white-background viewing derivatives. Author, independent reviewers and
coordinator inspected the diagrams; labels and wires were readable without
observed clipping. Packaging does not rerender them.

## Finite checks and their limits

[Source research](source/research.md) and [its results](source/reference-results.json)
retain 520 exact finite cases. The original Toffoli matrix is distinguished from
authored basis enumeration, Boolean constructions, clean-query and inverse-map
examples. The source-only constructions preceded image inspection and must not
be presented as transcriptions of the diagrams.

The later [figure plan](figures/PLAN.md), [report](figures/REPORT.md) and
[results](figures/check-results.json) retain 254 exact cases:

- Eight Toffoli basis columns and eight columns of the pictured 15-gate
  decomposition, checking all 64 amplitudes including phase against the original
  matrix. Amplitudes use rational coefficients in `Q[z]/(z^4+1)`; no numerical
  tolerance or phase normalization is used.
- Four AND, four OR, two FANOUT and four SWAP inputs, checking complete states.
  The pictured OR leaves both control inputs negated. FANOUT uses an initially
  zero target and does not assert arbitrary-state cloning.
- 128 authored clean-query instances and 96 authored inverse-query instances.
  These instantiate symbolic register diagrams; they do not verify arbitrary
  families, their internal clean workspace or asymptotic costs.

The pictured final construction applies `Q_f`, swaps registers, then applies
`Q_(f inverse)`. Earlier source-only examples erased before swapping. Matching
selected final outputs does not make those sequences identical. Likewise, the
earlier authored OR restores its controls while the pictured OR does not.
The packets explicitly preserve these differences. Shared schematic instances
are counted once, and the 520 and 254 counts do not represent native coverage.

## Historical records and reproduction

All 28 supplied source/figure/asset files preserve their external raw bytes;
this README is new. Independent source, visual-plan and final-figure reviews are
retained externally. The integration package manifest binds their identities and
the file origins. Earlier reports intentionally retain their historical bases,
absolute host paths, sibling references and statements that later steps were
pending. In particular, the source report's uninspected-media statement predates
the figure audit, and the figure report's pending final reviews predates the
completed independent reviews. Those statements do not describe this package's
latest state.

Git may normalize text line endings. Historical hashes identify external raw
artifacts, not necessarily normalized Git or distribution bytes. Keep both
identities; never label changed bytes as the original. Binary PNGs and the pinned
SVG identities remain bound by the acquisition/render records.

For reproduction, use a fresh output directory and retain the exact original
notebook and bound prerequisites. Both Python scripts write result files beside
themselves and bind their own bytes. The source reference requires its original
`source.ipynb` and research-plan bytes. The figure checker also binds the frozen
plan, original notebook and original/derived images; its historical paths and
the renderer's absolute Sharp/acquisition paths are host-specific. Read the
retained scripts before reproducing them. A copied package alone does not supply
all external prerequisites. Record any path adaptation, script changes, renderer
version changes and new output hashes separately. Do not overwrite retained
evidence or claim changed output is byte-identical without comparison.

The renderer's finite rejection checks for active/external SVG content are not
a general sanitizer certification. No reproduction was performed merely to
package these files. Historical `source.ipynb` and sibling-directory links refer
to the original audit layout; the equivalent packaged source records are under
`source/`. Acquisition receipts and independent review files remain external.

## Remaining acceptance

Native expressions, exact values and actual Copy/re-entry, Clipboard, saved
sessions and GUI acceptance remain separate. This packet demonstrates no new
parser defect or implemented feature. General reversible-simulation,
uncomputation, inverse-discovery and cost claims require their own evidence;
finite instances cannot certify them. Whole-lesson interpretation, master
integration and release remain open.
