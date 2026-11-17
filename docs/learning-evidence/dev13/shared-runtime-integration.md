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
| ibm019, ibm020 | Original IBM code cells with authored verification; Windows or Linux profile |
| qb007 | Selected Cirq cells; excluded cells remain outside acceptance |
| qb013 | Original Cirq/Stim source with observed conversions and explicit output audits |
| qb017 | QIR source contract with explicit semantic rejection when unsupported |
| qb027 | Selected Braket local simulation cells; provider work remains outstanding |
| qb030 | Selected Pulser local pulse/solver cells; hardware work remains outstanding |
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
