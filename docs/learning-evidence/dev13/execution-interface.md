# DEV-13 reviewed notebook execution interface

This increment executes the original IBM-019 and IBM-020 notebook cells in an
explicit, pinned external Python kernel. It is not a QuantumStudio runtime
adapter, QASM import, manual adaptation, or a claim of whole-notebook AUD-04
completion. Existing `execute_ibm019.py` and its dependency lock remain unchanged.

## Reproducible entry points

From the repository root, using a Windows CPython 3.12.10 interpreter:

```text
python windows/dev13-notebooks/run.py environment --profile qiskit-aer-win-py312 --python BASE_PYTHON --wheelhouse RETAINED_WHEELS --destination NEW_ENV
python windows/dev13-notebooks/run.py run --contract ibm019 --source ORIGINAL_NOTEBOOK --environment NEW_ENV --output NEW_OUTPUT
python windows/dev13-notebooks/run.py run --contract ibm020 --source ORIGINAL_NOTEBOOK --environment NEW_ENV --output ANOTHER_NEW_OUTPUT
python windows/dev13-notebooks/run.py cancel --run NEW_OUTPUT
```

The environment command creates a new directory, installs only local wheels with
the unchanged 51-package hash lock, checks exact installed versions and `pip check`,
and retains the wheel hashes and installation log. The retained custom
`pylatexenc==2.10` wheel is required: this lock is not a promise of reconstruction
from PyPI alone. Failed installs retain evidence and are not resumed or reused.

The public library seam is `execution.execute(request, events=None)` with the four
run fields above. It returns terminal evidence only after owned process cleanup.
The optional event callback receives supervisor state updates; detailed per-cell
records are in `cells.json`. CLI exits are 0 success, 1 failure, and 2 cancellation.
The cancel command records a request; its own exit 0 does not certify termination.
Inspect the run's terminal `status.json` and cleanup evidence.

## Original source and finite acceptance

| Contract | Original source | Exact byte SHA-256 | Original cells / code |
| --- | --- | --- | --- |
| IBM-019 | [IBM Deutsch algorithm notebook](https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-algorithm.ipynb) | `c9d818b01277230bc0b7ecb64dc41fe54a53de8fcfc84c08818a5051d039567f` | 17 / 8 |
| IBM-020 | [IBM Deutsch–Jozsa notebook](https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm.ipynb) | `513398ae77d7502e7e8c2f2d4bdc85d4a7b5474d25f88a00eb1a2e8a8777586f` | 20 / 8 |

The checked-in contracts include every original cell's exact UTF-8 text hash and
type, required drawings and original displayed results. Original source bytes are
never normalized or overwritten. Authored witnesses and the dependency lock use
LF-normalized hashing to tolerate Git checkout line endings. The reviewed checkout
is the trust root; these hashes detect mismatched source and witness artifacts,
not an attacker changing the runner and its contracts together.

IBM-019 executes all eight original code cells and validates both original PNG
drawings and the original `balanced` result. Its separate witness checks all four
Boolean functions, 16 basis mappings, full complex states including phase,
probabilities, deterministic counts and two invalid-input errors.

IBM-020 retains all 20 original cells and adds a clearly tagged NumPy seed-0
preamble. It validates three original drawings, cell 12's `balanced` and cell 17's
`1011` results. Its separate witness reconstructs the actual generated oracle's
classical truth table, compares the full operator, derives the complete Walsh
state independently, and compares probabilities and 4096 sampled counts. Five
Bernstein–Vazirani secrets additionally check operator/state/counts/classification.
The original random notebook is not claimed to be inherently deterministic.

## Retention and owned cleanup

Each new output directory retains exact `source-original.ipynb`, an execution copy,
the engine request and dependency identity, per-cell state/elapsed time/errors,
rich outputs, engine stdout/stderr, supervisor events and final status. Authored
cells have separate tags and null original indexes. Execution clears saved code
outputs/counts and timing metadata, then checkpoints before and after each code
cell. Later cells remain `not_run` following errors, timeout or kernel death.

A non-inheritable Windows Job Object owns the gated engine and its local kernel.
The gate opens only after assignment; kernel membership is checked. Cancellation
uses the private stdin control pipe and an event-loop cancellation request, then
bounded job termination if needed. Cleanup records the actual remaining job
process count, engine exit and graceful/forced method. A hard kill can retain only
the last atomic checkpoint. Jupyter's underlying cancellation error is retained
even when the supervisor marks the interrupted cell from its cancellation record.

This is not OS sandboxing or network isolation. Only the two reviewed local-source
contracts are exposed. Provider submission, arbitrary notebooks, runtime package
installation in source cells, remote kernels and other frameworks are outside
this finite implementation. The job uses CPython's Windows `Popen._handle`; the
supported interpreter/profile and 64-bit structure layouts are checked.
Validation, engine and kernel all use Python isolated startup (`-I`), so inherited
`PYTHONPATH` cannot replace the validated packages. Checkpoint replacement retries
brief Windows reader locks for up to two seconds while preserving the old file.

## Verification and remaining work

Evidence root: `cleanup-audit/notebook-lane-20261104/runtime-tests/` in the shared
audit workspace. `ibm019-01` and `ibm020-01` passed using the retained environments;
both `*-clean-replay` runs passed using the new environment installed by this
interface entirely offline. Both `*-isolated` runs then passed with the corrected
isolated kernel invocation. All runs recorded kernel job membership and zero
remaining owned processes. All original cells were compared to retained source;
source result assertions and authored witnesses passed.

Run the real lifecycle suite with the locked environment's interpreter:

```text
NEW_ENV/Scripts/python.exe windows/dev13-notebooks/test_execution.py
```

Set `DEV13_TEST_EVIDENCE` to a new directory to retain fixture artifacts. The final
`lifecycle-06.log` records 12 passing tests: source error with previous outputs,
timeout, kernel crash, cooperative and forced cancellation with a kernel-created
child and unrelated-process survival, failed job assignment, unknown/changed
source, existing output preservation, wrong interpreter, and wrong original
displayed result, inherited Python-path contamination, and transient Windows
reader locks. Forced cancellation also requires an `incomplete` aggregate when
original cells already executed. `review-red.log` reproduces both independent
review findings before their fixes. Earlier failures remain retained, including
the test assertion correction and Jupyter cancellation classification regression.

External markdown SVG/page rendering and full lesson/native-mathematics
interpretation remain outstanding. The external-resource manifest records HTTP403
for Deutsch-circuit.svg and Deutsch-Jozsa.svg, and verifies the previously retained
Deutsch-circuit-states.svg hash without claiming a new rendering review.
The five source-generated circuit drawings
were inspected in prior source probes; this runner verifies their PNG output
presence, not pixel equivalence. No provider/hardware verification, QIR/CUDA-Q,
pulse adapters, non-Qiskit frameworks, GUI execution, or completed AUD-04 claim
follows from these tests. Source-distribution registration is owned by integration.
