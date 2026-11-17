# QB-006 local execution preserves a source failure

The selected local execution route passes verification, but the intended
algorithm does not pass. The witness explicitly reports
`intended_algorithm_passed: false` and `QB006-SOURCE-01`. QB-006 remains open.
Historical native/GUI evidence for the original three-counting-qubit program is
retained in [QB-006](../../QB-006.md); no new native execution is claimed here.

The pinned notebook is `qBraid-Algorithms/qpe.ipynb` at revision
`86787e1ba372facc224f925189755e69c479828b`, SHA-256
`cf52622e2ca5abcdf2e93ef055543c093fca44810b3d2c09e0e9d56c8b882b06`.
All 31 cell identities are recorded. Original code cells 1, 2, 4, 6, 8, 10, 12,
15 and 22 execute unchanged. Provider construction, device discovery, submission,
result processing, result printing and histogram cells remain excluded. Importing
the provider class in cell 15 does not construct a provider or submit a job.

## Staging and command compatibility

A separately labelled preamble stages the two original companion files into the
new run directory. It verifies their pinned hashes and uses exclusive creation;
existing files are not overwritten. The unitary input defines Z and the
preparation input defines X. Their hashes match the historical source audit.
The witness rechecks those bytes after all selected original cells execute.

The route reuses the `algorithms-win-py312` profile and QB-004's unchanged
Windows adapter, setup observer and cleanup. The adapter translates only the
reviewed pip command's quoting and defines `%cat` as `type`, then restores the
previous shell handler and alias. `qb004-compatibility.json` retains that shared
adapter's provenance; the notebook identity comes from its own contract.
The generated module has no final newline, so the display check permits exactly
the one newline IPython adds. The initial prerequisite display assertion failed
after all nine cells succeeded; its evidence is retained separately.

## Preparation discrepancy

In qbraid-algorithms 0.1.3, `_get_psi` supplies a renamed preparation gate
definition. The template inserts this definition but does not invoke it before
calling `qpe(q, psi)`. Both generated programs therefore leave `psi` in zero.
The generated primitive operations involving `psi` are controlled-Z gates only.
The independently interpreted unitary prefix reproduces the discrepancy:

| Counting qubits | Original zero input, dominant output | Authored psi=1 control, dominant output |
|---|---|---|
| 3 | `000` | `100` |
| 4 (default) | `0000` | `1000` |

The authored control changes only the initial state in the independent numerical
calculation. It does not modify the original generated QASM or claim an original
notebook result. Source qubit zero is the most significant tensor bit; `psi` is
the least significant. Output labels use `b[n-1]...b[0]`. Literal decimal angles
are retained and evaluated in double precision. The dominant probabilities are
within `1e-12` of one; this does not assert exact zeros or ones for rounded-angle
programs. The prior high-precision exact-execution evidence remains separate.

Current default and three-counting-qubit generated programs match historical
programs after CRLF normalization. Their raw hashes differ, and that distinction
is recorded rather than claiming byte identity. No importer fix invents the
missing preparation operation.

Tests reject hidden preparation, missing phase controls, reversed measurement
destinations, unsupported widths and overwriting staged input files. The
independent witness verifies all six staged/generated files by hash. Two real-kernel runs and 60 focused tests pass. The replay retained identical
bytes and sizes for all 24,920 files (557,650,871 bytes) in the environment, base
interpreter and notebook runtime. All six staged/generated files match between
runs, and both printed source outputs were checked. This endpoint comparison
does not exclude transient writes. Dependency closure verifies 71 distributions
and 127 active requirements. The [artifact index](index.json) binds 68 retained files by size and SHA-256.
All 31 notebook cell hashes and both companion hashes were verified. Exact-head
reviews remain pending.

External evidence is retained in
`cleanup-audit/learning-coverage-20261117/qb006-notebook/`. Remaining acceptance
includes a supported source correction or generator version yielding the intended
result, default/prepared exact execution, generated module/editor routes,
provider workflow, required CI, packaging and release. A successful local
diagnostic does not close those requirements.
