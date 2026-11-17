# QB-018: PyQIR, Cirq and direct Squin execution

The `qb018` contract runs every original cell through the existing owned notebook
runner. It uses the new `squin-win-py312` profile and adds a distinct GHZ witness.
This is local development evidence; QB-018, DEV-13 and DEV-14 remain open pending
independent review and CI/package/release acceptance.

Source: [pinned notebook](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/qBraid-QIR/qir_to_squin_conversion.ipynb),
revision `86787e1ba372facc224f925189755e69c479828b`, SHA-256
`cc18a95943ff2196e1cc1103fab25862c9e5a15999172c3b764a12519f1014a6`.
All 19 cell types and source strings are preserved. Twelve code cells run,
including the empty cell 17. Authored setup-observer/check and witness cells are
added explicitly; this is instrumented execution, not an untouched notebook file.

## Original-cell interpretation

| Cells | Purpose and observed disposition |
|---|---|
| 0, 3, 6, 10, 14 | Section introductions; read as non-executable context. |
| 1 | Original installation magic succeeds offline against already installed exact dependencies; before/after distribution metadata and RECORD inventories match. |
| 2 | All original imports succeed. |
| 4–5 | Four-qubit QIR GHZ construction and lowering; printed kernel shows allocation, H and three chained CX operations. |
| 7–9 | Cirq GHZ definition, circuit output and Squin lowering; printed circuit and kernel inspected. |
| 11 | Both original printed vectors pass the separate captured-output GHZ audit. |
| 12–13 | Comparison explanation and printed dot magnitude `1.000000`; complex-state limitation below. |
| 15–16 | Direct Squin kernel and its original displayed state vector pass. |
| 17 | Empty code cell executes without output. |
| 18 | License notice; non-executable. |

## State semantics and limitations

The expected normalized state has equal amplitudes at indices 0 and 15 and zero
interior amplitudes. Comparisons permit a common global phase and use tolerance
`1e-6`, appropriate to observed simulator precision. They check finite values,
shape, norm, overlap and amplitude residual; agreement between two wrong results
is insufficient. This symmetric source does not establish general wire ordering.

The installed `StackMemorySimulator.state_vector()` starts another task. The
authored witness therefore reports `authored_rerun_routes`, not original cached
vectors. Separately, `audit_source.py` parses the original printed vectors in
cell 11 and displayed vector in cell 16 from the retained notebook. All three
have equal endpoints, zero interior support, and norm errors below `1.2e-7` in
the corrected run. The original cell-13 comparison also performs fresh calls.

Its unconjugated dot product remains unchanged. It works for these GHZ rays but
is not a general complex-state fidelity check: `(1,i)/sqrt(2)` dotted with itself
is zero, while its dot with the orthogonal conjugate is one. The witness uses a
conjugated overlap and includes three authored oracle controls. Those controls
test the comparison function, not additional SDK circuits. Four unit tests reject
wrong relative phase in every route, wrong support, malformed/nonfinite vectors
and incorrect normalization, while accepting independent global phases.

## Reproducible dependencies and execution

Python 3.12.10, Windows x64; 172 exact distributions in
`windows/dev13-notebooks/squin-requirements.lock`. Key versions are Bloqade
0.37.0, Bloqade Circuit 0.15.6, PyQrack CPU 1.89.0, PyQIR 0.12.6, qBraid-QIR
0.6.1 and Cirq 1.7.0. The lock preserves Cirq's requested `contrib` extra.
The complete installed closure passed 400 active dependency requirements,
including propagated extras and Python version constraints.

All 172 wheel hashes were checked before a fresh isolated offline installation.
Two source-only dependencies required local wheels: ffmpeg 1.4 retains all five
module files; PyLaTeX 1.4.2 retains 23 modules and regenerates its version metadata
for version 1.4.2. Both wheel RECORDs were verified. These Python packages do not
install or prove execution of external ffmpeg or LaTeX applications. Earlier
failed/backtracking resolutions are retained; they do not establish that every
older package combination is incompatible.

Use `run.py environment` with profile `squin-win-py312`, the specified base Python,
verified wheelhouse and a new destination; then use `run.py run --contract qb018`
with the pinned source, that environment and a new output directory. Original
setup uses the runner's offline pip configuration; no provider job is submitted.

## Evidence and remaining gates

External evidence is in the main repository's
`cleanup-audit/learning-coverage-20261117/qb018-prerequisites/`, outside the worktree.
It includes resolution reports, source/wheel bindings, local build audits,
installation log, dependency closure, both runs, and captured-output audits.
`run02` uses the corrected witness label; `run01` is retained as historical.
Both runs succeeded with kernel job membership and zero remaining processes after
forced cleanup. This is not graceful-shutdown evidence.

Validation: four witness tests, 24 request/profile tests, and the complete source
run. The JSON index binds actual artifacts. Full file integrity across a run,
packaged UI behavior, hosted CI, release verification, general Squin/CUDA-Q support
and the wider source inventory remain separate work.
