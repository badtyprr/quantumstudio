# QB027: original Bell construction with authored native Braket execution

Prepared on `2ece476d92b58d2cf786e8f62c7ac4457e01f689`. This four-file candidate
adds a contract, witness, SDK-free tests and this evidence description. Actual
Braket execution is pending. The integration owner separately owns the single
`qb027` addition to `execution.py`'s public allowlist and distribution registrations;
without that integration the public command correctly rejects the new contract.
No other engine, lifecycle, profile, lock or source changes are proposed.

## Original identity and execution boundary

[Original notebook](https://github.com/qBraid/qbraid-lab-demo/blob/86787e1ba372facc224f925189755e69c479828b/Provider-Jobs/qbraid_runtime_braket_provider.ipynb),
revision `86787e1ba372facc224f925189755e69c479828b`, stable ID QB-027.
Original SHA256 `475fd081135e5611fceb1f362a4845657251f948fda73ad51bfb55e5814fc090`.
Cell6 SHA256 `8c3c0187eab2a7b828c0d8b00c11bb3f6ee89c5b1c07417bbc17dd7eeec28c1b`.

The existing selected-cell route executes only unchanged cell6: import Circuit,
construct H(0), CNOT(0,1), explicit measurement[0,1], and print. A separately
authored witness executes this measured circuit on the native Braket local
state-vector simulator. Its unmeasured state and algorithm controls are separately
authored circuits, not additional original notebook cells or a rewritten SV1 job.

All ten original cells retain identities and dispositions:

| Cells | Disposition |
|---|---|
| 6 | Selected unchanged original code |
| 1 | Unpinned install excluded; pinned retained environment replaces setup |
| 3 | AWS credential reads/provider construction excluded |
| 4 | Remote device discovery excluded |
| 7 | Original SV1 100-shot provider job excluded |
| 8 | Remote-result histogram excluded |
| 0,2,5,9 | Markdown retained, not executable |

Keep `original_execution=not_executed_as_whole`, `whole_notebook_complete=false`
and the separate selected-execution outcome. Full source bytes remain unchanged.
Original provider setup, jobs, histogram and interpretation are still required for
whole-notebook acceptance. Existing QB017 Braket construction/QIR evidence is not
being relabeled as native simulator evidence.

## Pinned route and API boundaries

Reuse the existing Windows Python3.12.10 `qir-win-py312` exact94-package superset:
Braket SDK1.127.7, default-simulator1.43.1, schemas1.32.1.post0. Lock LF SHA256
`70faf49c835ed96a1d6bf6941690536af4c47515b91659d908a7b57efaabb282`.
This is not a minimal environment or an installation/replay claim for this candidate.
Reverify package, wheel and source identities before and after reserved execution.

Construct an explicit local `StateVectorSimulator` and pass its instance to
`LocalSimulator`; no provider, AWS client, remote backend or credential object is
constructed. Record the actual backend class and versions. The SDK internally
serializes Circuit into OpenQASM before local execution. This is native SDK
execution with its internal serialization, not manual QASM adaptation or QIR.
The original measured circuit's serialized representation must remain unchanged.

Pinned source inspection shows StateVector requests require zero shots. State
controls therefore use separately authored unmeasured circuits. The simulator
owns an unseeded NumPy default_rng; setting global np.random.seed would not make
its counts reproducible. Do not patch the private generator or promise count
identity across runs. Preserve raw results and use the declared statistical bound.

## Frozen finite matrix and independent expectations

| Cases | Native execution and criterion |
|---|---|
| Original measured Bell | 4096 shots, only00/11, exact total; each frequency within0.05 of0.5 |
| Authored Bell+ and phase Bell | Two zero-shot full complex state checks, respectively (00+11)/sqrt2 and (00+i11)/sqrt2 |
| Authored three-qubit one-hot controls | X on q0 or q2, full zero-shot state plus128shots each; exactly100 or001 |
| Eight n=2 Deutsch–Jozsa truth tables | Both constants and all six balanced tables; full three-qubit state and128data-only measurement shots each |
| Six Bernstein–Vazirani cases | Every two-bit secret00,01,10,11 plus three-bit001/100; full state and128data-only shots each |
| Three pinned negative API cases | Empty circuit; zero shots without result types; StateVector at positive shots: ValueError with pinned diagnostic fragment |

There are18 state executions and17 sampling executions requesting6144shots total,
plus three calls expected to fail validation. State tolerance is1e-12. All14
algorithm cases have exactly one supported data result: every promised two-bit
DJ function is affine. Require all128shots to match that result, rather than
applying a statistical tolerance to an ideal deterministic outcome. Measure only
data qubits, retain ancilla in full state checks, and verify measured-qubit order.

For Bell, assuming independent ideal samples, the conservative two-outcome
Hoeffding union bound is `4 exp(-2*4096*0.05^2)`, below1e-8 per run. It is not a
promise that stochastic acceptance can never fail; retain any failed run unchanged.
No whole-family or hardware error guarantee follows.

Algorithm oracle circuits implement reversible Boolean truth permutations on
[data bits, ancilla]. Expected amplitudes use independent scalar Walsh sums:
`a_y = sum_x (-1)^(f(x)+x.dot(y))/2^n`, tensored with the unchanged |-> ancilla.
Tests cross-check those sums against separate scalar basis-vector H/X/permutation
updates, including constant-one global phase and asymmetric bit-order mutations.
Expected amplitudes never come from Braket matrices or a conversion of its output.
The phase-Bell control also checks a non-real relative amplitude; counts alone do
not establish coherence.

## Preparation checks and remaining acceptance

Set QB027_ORIGINAL_SOURCE to the retained immutable original file, then run
`python -B -m unittest -v test_qb027` normally and with `-O`. Ten SDK-free tests
cover all source/cell identities, selection/exclusions, witness hash, finite case
coverage, independent oracle comparison, phase/order sensitivity, malformed truth
and count rejection, predeclared shot/tolerance constants, and NaN/Infinity state rejection before residual reduction. They import only
standard-library witness helpers; they do not execute its guarded SDK entrypoint.

Final review must cover the four new files plus the coordinator's allowlist token
and registrations. Only after that review and an execution reservation may actual
original source/SDK/witness acceptance run. Retain states, raw counts, errors,
all10dispositions, original bytes, environment, stdout/stderr and owned cleanup.
Reuse established lifecycle semantics; do not claim actual Braket compatibility
from these synthetic tests. No provider/hardware, wholeQB027, current-version,
Linux, noise or general gate-compatibility acceptance is established here.
