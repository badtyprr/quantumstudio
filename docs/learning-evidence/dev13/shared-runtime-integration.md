# Shared notebook runtime integration

This integration restores the 51 runtime files from preserved revision
`060aaa0712b99b5f368dca790f6bedef1d947713` onto the current development stack.
The original source bytes and SHA-256 hashes are indexed in
`cleanup-audit/learning-coverage-20261117/dev13-shared-runtime/import-manifest.json`.
These are implementation and validation inputs, not newly completed lesson audits.

## Runtime boundaries

The public entry point remains `windows/dev13-notebooks/run.py`. Contracts bind
source notebook bytes, cell indexes, dependencies and authored verification.
Unknown or changed sources are rejected. Only these finite contracts are exposed:

| Contract | Execution scope |
| --- | --- |
| ibm052 | Runs the complete entanglement lesson on Windows and Linux. Checks teleportation, superdense coding and both CHSH strategies. [Notebook results](ibm052-notebook.json) |
| ibm023 | Runs the complete factoring and GCD lesson with SymPy. The Windows and Linux profiles verify the original printed results and independently check the final divisor. [Notebook results](ibm023-notebook.json) |
| ibm019, ibm020 | Original IBM code cells with authored verification; Windows or Linux profile |
| qb007 | Selected Cirq cells; excluded cells remain outside acceptance |
| qb011 | Runs the original Qiskit, Braket, Cirq, PyQuil and pytket conversions and checks every entry of the final operator. Uses the Windows profile `transpiler-pyquil-win-py312` with PyQASM 1.4.0. |
| qb012 | Runs the default and custom Qiskit-to-Braket routes, saves both conversion graphs and checks both operators. Uses the Windows profile `transpiler-win-py312` with PyQASM 1.3.0. [Run evidence](qb012-notebook-route.json) |
| qb013 | Original Cirq/Stim source with observed conversions and explicit output audits |
| qb017 | QIR source contract with explicit semantic rejection when unsupported |
| qb027 | Selected Braket local simulation cells; provider work remains outstanding |
| qb030 | Selected Pulser local pulse/solver cells; hardware work remains outstanding |
| qb019 | Eight unchanged Bernstein-Vazirani cells use a separately recorded local Qiskit sampling step to supply the displayed histogram. AWS verification remains open. [Run evidence](qb019-public-run.json) |
| qb020 | Eleven unchanged IBM Runtime notebook cells run on Aer. A recorded configuration step selects the simulator. The runner checks the Bell state, estimator, shot counts and both source plots. [Run evidence](qb020-public-run.json) |
| qb026 | Six original cells read the published benchmark cache from the run directory, calculate the summary and render the two population curves. [Both verified revisions](qb026-cache-runs.json) |
| qb036, qb038 | Original Qiskit GHZ construction and drawing cell. CPU Aer checks the three-qubit statevector and samples three widths through 100 qubits in two bases. Provider execution remains open. [Recorded runs](qb036-qb038-ghz-routes.json) |
| ibm-timing | Finite timing observations with authored reference and retained artifacts |

Windows launch ownership is established at process creation with a job-list
attribute and a suspended launcher. Identity and membership are checked before
resuming it. The launcher PID is distinct from a possible redirected engine PID.
Cleanup retains errors; an access-denied termination race is accepted only after
terminal state is confirmed using the same continuously held process handle.
Linux uses the owned service backend and requires its documented capabilities.
Neither platform constitutes a security sandbox or network isolation.

Selected routes can now opt into [reviewed first-cell setup](selected-setup.md).
The setup cell must be selected first; pip exit status and metadata/RECORD
inventory checks gate later execution. This does not make a selected route a
whole-notebook execution or resolve source-specific shell compatibility.

## Current verification

Fresh validation logs are retained under the evidence directory above. The
34 injected Windows launcher tests passed. The execution suite passed 81 tests
in 142.615 seconds, including real Windows lifecycle fixtures and injected cases.
The framework contract suite passed 255 tests in 17.206 seconds using retained
original QB027/QB030 notebooks for source-identity checks. These source checks
do not execute those notebooks. The first contract run lacked those two source
settings and exposed an archived-prefix hash assertion: the archived reference
had one CRLF, while the Git file has LF. Complete normalized files match; the
corrected assertion binds the full Git file. Raw failed logs remain retained.
Original notebook execution, fresh dependency installation, Linux execution,
hosted CI, packaged verification and release remain pending for this integration.
No DEV-13, DEV-14, DEV-15, AUD-04 or individual source row is closed by importing it.

The [earlier execution interface](execution-interface.md) describes the initial
two-contract runtime and its historical acceptance. Its old launch details and
contract count are superseded by this integration; its recorded test outcomes
are historical, not evidence for the new runtime.

## Deutsch lesson revisions

Pass either recorded notebook revision to the existing `ibm019` or `ibm020` contract. Each revision retains the same eight executable cells. The runner verifies the full file and the cell manifest for that revision. A fresh offline Windows installation ran both revisions of both lessons. The runs preserved every original cell, produced the required figures and text, and passed the reference state, sampling and error checks. Changing a code cell in either pinned notebook produced a source hash mismatch. All 121 execution and Windows lifecycle tests passed. Published-release checks remain open. [Four runs and reference results](deutsch-notebook-revisions.json).

The Linux runner at `d0ec0f57` ran the same four notebooks in a fresh Python 3.12.10 environment installed from 54 hash-verified wheels on Ubuntu 24.04 x86-64. Each execution preserved all eight original code cells, used its own systemd service and finished with zero remaining processes. The two altered source controls failed hash validation before execution. For IBM-019 each of the four oracles produced its predicted result on all 256 samples. For IBM-020 the generated oracle matched the independently computed operator and state, the 4,096 samples occupied the predicted support, and all five Bernstein–Vazirani secrets were recovered. The run records include image hashes and output text. [Linux results](deutsch-linux-runs.json).

## Preparing the Windows transpiler environments

Run `prepare_transpiler_wheels.py qb011 WHEEL_FOLDER` or
`prepare_transpiler_wheels.py qb012 WHEEL_FOLDER` with 64-bit Windows Python
3.12.10 and a new destination. This online preparation step checks the source
and build backend hashes before building rpcq. Two builds produced the same
wheel, with the same 17 member files as the earlier cached copy. The normal
offline environment command installed 117 distributions for each profile.
Both original notebooks passed using those installations.
[Build and replay evidence](transpiler-wheel-rebuild.json).

The Windows package staging directory at revision `c637aa12` ran QB-011,
QB-012 and both supported revisions of IBM-019 and IBM-020. The staged
native worker also passed all 237 source formulas from the two IBM lessons.
Package creation stopped when the domain GUI test could not read the copied
result. The standalone retry reproduced the clipboard failure. Extracted-ZIP
verification remains open. [Staged package results](staged-windows-notebook-runs.json).
