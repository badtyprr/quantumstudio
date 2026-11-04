# IBM-019 external notebook execution contract

This development contract runs the original eight Qiskit code cells in a real,
separate notebook kernel. It is not QuantumStudio Python support, an importer,
a manual QASM adaptation, or complete DEV-13/AUD-04 coverage.

## Original source

IBM's [Deutsch algorithm notebook](https://quantum.cloud.ibm.com/endpoints-docs-learning/raw/learning/en/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-algorithm.ipynb),
SHA-256 `c9d818b01277230bc0b7ecb64dc41fe54a53de8fcfc84c08818a5051d039567f`.
The pinned bytes are retained in the source audit, not rewritten by this runner.
The digest, not the mutable endpoint, identifies the tested source. A changed
source is rejected before kernel launch or output-directory creation.

All 17 source cells were inspected. Code cells 2,3,5,7,9,11,13,15 run in their
original order and text. Existing saved outputs are cleared in an execution
copy. A tagged eighteenth cell contains authored verification; it is never
represented as original IBM code. Original source text is checked after execution.

| Source cells | Route and interpretation |
|---|---|
| 0 | Narrative, truth tables and phase-kickback analysis retained; native mathematical acceptance belongs to the math lane. Two linked SVG diagrams remain external display dependencies. |
| 1,4,6,8,10,12,14 | Setup/algorithm/drawing explanations read and retained. They explain which code follows; no executable setup magic or provider requirement exists. |
| 2 | Prints the actual Qiskit version. |
| 3 | Imports Qiskit and local AerSimulator. |
| 5 | Defines four Boolean-function query circuits. |
| 7,11 | Original matplotlib circuit drawings produced as notebook PNG outputs; inspected first-run images show the expected CX/X oracle and complete H/query/H/measurement circuit. |
| 9 | Defines Deutsch circuit construction, including barriers and measurement. |
| 13 | Defines a one-shot local simulation and constant/balanced classification. |
| 15 | Original example returns `balanced`; this output is required. |
| 16 | IBM copyright notice retained. |

## Setup and reproduction

The tested environment is Windows x64 CPython 3.12.10, Qiskit 2.2.3 and
Qiskit Aer 0.18.2. The adjacent hash lock pins all 51 notebook, plotting and
simulation dependencies. Original source imports are unchanged. The notebook
kernel's `display` capability is supplied by IPython; no display call is rewritten.
[Aer installation documentation](https://qiskit.github.io/qiskit-aer/getting_started.html)
describes the separate local simulator package. No GPU/provider credentials are used.

Use a fresh Python environment; download the hash-locked wheels or use the
retained wheelhouse, then install with `--no-index --find-links WHEELS
--require-hashes -r windows/dev13-notebooks/ibm019-requirements.lock`.
The pylatexenc 2.10 wheel was built from its source distribution using a
pure-Python build; its exact resulting wheel, source archive and build log are
retained separately. The wheel lock is an artifact identity, not a claim that a
fresh rebuild yields identical wheel bytes. The acquired wheelhouse is 105,348,254
bytes. No shared environment was modified.

Run the environment's Python with:

```text
windows/dev13-notebooks/execute_ibm019.py --source ORIGINAL.ipynb --output NEW_DIRECTORY
```

The runner checks source identity and every locked installed version, creates a
private kernel specification using that exact interpreter, and saves the executed
notebook plus per-cell result JSON. Output must be a new directory. Errors retain
the partially executed notebook and error report. The kernel is cleaned up on
completion or failure. Original notebook files are never written.

## Independent acceptance

The authored witness defines the four truth tables independently as 00,01,10,11.
For each function, all four basis inputs must map to the exact expected amplitudes
under `(x,y) -> (x,y XOR f(x))`. Before measurement, the full Deutsch state must be
`(-1)^f(0) |-> |f(0) XOR f(1)>` in Qiskit q1,q0 order, within 1e-12 per amplitude.
The q0 marginal must be deterministic. A separate seeded 256-shot local run must
return only the expected bit; the original one-shot function must return constant
for cases 1/4 and balanced for cases 2/3. Invalid inputs 0/5 must raise ValueError.

This extends the original example with independently expected states/counts/errors;
the extra cases and shot count are authored tests, not unchanged notebook cells.
Eight original execution counts, both drawing outputs and the original balanced
result are required. The actual kernel executable is checked against the launcher.

## Evidence and remaining limits

External evidence lives in `cleanup-audit/notebook-lane-20261104/ibm019/` in the
main project: wheel/source acquisition and install logs, manifest, and run-01/02/03
outputs. Run-03 includes the full amplitude witness. Earlier runs are preserved.
Clean replay in a second fresh environment installed exclusively from the 51
hash-locked retained wheels and reproduced all cell execution/output classifications,
package versions and independent numerical/error results. Source tampering was
rejected before output/kernel creation. An injected authored-witness failure
retained the failed notebook and error report; it did not alter original cells.
Independent Standards and Spec reviews of implementation `2860d9f13` found zero
actionable findings. Source-distribution registration remains coordinator-owned.

First-run circuit images were visually inspected; later runs enforce image output
presence, not pixel identity. Source text and display objects remain in the notebook.

A Windows ZeroMQ selector-thread warning and local TCP kernel warning were emitted;
they did not prevent execution. No unsupported SDK operation was observed in this
finite source. External SVG rendering and integration evidence remain pending.
Markdown was preserved and
read, but this runner does not render IBM-specific page components. Do not mark the
whole lesson, all notebook external requirements, DEV-13 or AUD-04 complete.
