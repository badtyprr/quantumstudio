# QB-005 selected local notebook execution

The selected local route passes. QB-005 remains open: provider, job, result and
histogram execution, complete notebook workflow and delivery gates remain outside
this evidence. Historical native/GUI inverse-QFT acceptance remains documented in
[QB-005](../../QB-005.md); this change does not reopen its resolved timeout.

The source is `qBraid-Algorithms/qft.ipynb` at revision
`86787e1ba372facc224f925189755e69c479828b`, SHA-256
`bc648239a475fbfead15b185e201e821498369ff5d133ba928603bb1319fc3d3`.
The contract records all 31 cells and selects original code cells
1, 2, 4, 6, 7, 9, 10, 12, 14, 16, 18 and 24. These twelve cells execute with
unchanged source text. Cell 18 imports the provider class without constructing it.
Cells 20, 22, 25, 27 and 29 have explicit exclusion reasons.

## Windows route

The route reuses the 71-distribution `algorithms-win-py312` profile and QB-004's
hash-bound compatibility lifecycle. Both notebooks have exactly the same setup
command and `%cat` requirements. The authored adapter translates that one pip
command's single quotes into Windows argument quoting and defines `cat` as
`type`; it does not replace SDK methods. Setup observes actual exit status and
checks installed distribution metadata before and after. Cleanup restores the
original system handler and alias.

The retained artifact is named `qb004-compatibility.json` because the adapter is
shared from that contract. It describes command adaptation, not the notebook's
identity; source and contract identity are separately bound by the runner.
The module files have no final newline. IPython adds one to their displayed
text; the output check permits exactly that additional newline. An initial
prerequisite probe rejected this formatting difference after all source cells
had succeeded; the failed attempt is retained.

## Independent numerical checks

The witness preserves all five original generated files and verifies their
hashes. It interprets the three-qubit primitive programs independently of the
native importer or worker. For the four-qubit program, it loads a fresh copy and
unrolls it in a separately authored verification step, preserving the original
gate-definition program. It then interprets that primitive output.

| Program | Basis inputs | Primitive gates | Comparison |
|---|---:|---:|---|
| QFT, three qubits | 8 | 55 | Positive Fourier matrix, one global phase |
| Inverse QFT, three qubits | 8 | 55 | Negative Fourier matrix with both index orders reversed, one global phase |
| QFT, four qubits | 16 | 108 | Positive Fourier matrix, one global phase |

All 32 columns agree within `2e-15`; the acceptance tolerance is `1e-12`.
The state-vector convention treats source wire zero as the most significant
tensor bit. Each comparison uses a single phase for its entire operator, not
independently chosen phases per column. Decimal rotations are evaluated literally
in double precision; they are not replaced with ideal multiples of pi. These
are approximate comparisons with an ideal matrix, not exact symbolic proofs.
The inverse program's three terminal measurements are checked structurally and
excluded from unitary-prefix evolution. No composition identity is claimed
across the different QFT and inverse-QFT conventions.

The three-qubit generated file hashes match the previously audited source.
This route supplies new Python execution evidence; it does not claim a fresh
native or packaged run. Tests reject reversed controlled gates, changed rotation
signs/angles, missing swaps, altered measurement destinations and unsupported
operations. The focused runtime/adapter/Fourier suite passes 54 tests.

The [artifact index](index.json) binds 59 retained files by size and SHA-256.
All 31 original cell hashes were verified against the pinned contract.

External records are under
`cleanup-audit/learning-coverage-20261117/qb005-notebook/`. Dependency closure
checks 71 installed distributions and 127 active requirements. A real-kernel run
passes the authored witness and leaves zero owned processes. 
A second replay retained identical bytes and sizes for all 24,915 inventoried
files (557,628,885 bytes) across the environment, base interpreter and notebook
runtime. All six generated/authored QASM files match the first run. Printed
source excerpts and module displays were verified. This interval comparison does
not rule out transient writes. Exact-head reviews are still pending. Required hosted
CI, new packaging, GUI acceptance and release are not claimed.
