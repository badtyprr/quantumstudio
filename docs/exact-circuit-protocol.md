# Exact circuit worker protocol

Invoke `quantum-worker --exact-circuit` with one binary UTF-8 request on stdin.
This mode cannot be combined with other flags. A successful request produces one
JSON object on stdout; failure produces a diagnostic on stderr, exit code 2 and
no partial JSON. The GUI integration is separate from this worker interface.

The header is `QEXACT1` followed by LF. Every integer is unsigned decimal followed
by LF, with no spaces or signs. The remaining fields are:

1. Quantum register size (0–10).
2. Classical register size (0–64).
3. Number of selected output bits, then their indices in display order.
4. Number of top-level operations, followed by those operations.

An expression is its UTF-8 byte length followed by LF, then exactly that many
bytes (1–4096), with no implicit trailing separator. Expressions use Quantum
Notation in exact mode. Expressions must resolve to certified physical operators
or probability tables; unproved symbolic physical constraints are errors.

Each operation starts with its code:

| Code | Fields |
| --- | --- |
| 0 | Target count, target indices, unitary matrix expression |
| 1 | Quantum wire, destination classical bit |
| 2 | Quantum wire to reset |
| 3 | Classical mask, value, then the fields of code 0 |
| 4 | Target count, target indices, vector of Kraus matrices expression |
| 5 | Classical target count, target indices, readout probability matrix expression |
| 6 | Classical mask, value, true-body count and operations, false-body count and operations |

Qubit zero is leftmost in a state. Classical bit zero is the least significant
mask bit. A branch selects its whole body once on entry using
`(record & mask) == value`. The first output bit is leftmost in result labels.
Targets must be distinct. Readout supports 1–8 targets; its table row is the
actual record and column the reported record, with the first target most
significant. Reset leaves classical memory unchanged. Measurement overwrites its
destination and merges records without normalizing their individual masses.

The state starts at all-zero quantum and classical registers. There is no
implicit final measurement. Empty output selection returns total probability
under the empty string label. Zero-probability outcomes are omitted when proved
zero; symbolic expressions are retained. All bodies, even untaken ones, are
validated. Limits are 512 total operations, 32 nested branches, 1,100,000 input
bytes, 1,048,576 stored density-matrix cells per record map, and 1,048,576 Kraus
entries per operation. Temporary matrices and symbolic expression storage are
additional. Code 3 expands to a branch containing a map and counts as two steps
against the evaluator's 512-step limit. The caller should enforce a process timeout and may terminate the
worker on cancellation, as with other worker modes.

Response fields are `qubits`, `classical_bits`, `bits` (selected indices), and
`probabilities` (bit-string keys to exact scalar strings). Probability values are
strings to preserve symbolic formulas and rational values without JSON number
rounding. For example, measuring a Hadamard-prepared qubit returns
`{"qubits":1,"classical_bits":1,"bits":[0],"probabilities":{"0":"0.5","1":"0.5"}}`.

Certified unitary circuits followed only by computational measurements can use
bounded exact phase arithmetic instead of density-matrix expansion. Unsupported
gate expressions, channels, resets, intermediate measurements and control flow
retain the general evaluator. This selection does not add implicit measurements
or change classical bit ordering or overwrite semantics.

The phase route retains literal rational angles and coefficients exactly; it
does not snap decimal angles to multiples of pi. Large probabilities may be
returned as sums of `abs(exact_amplitude)^2` factors. These are exact scalar
expressions, not numerical estimates. Small rational results retain terminating
decimal text such as `0.5`; nonterminating rational results retain fractions.
Exact text is serialized without precision-dependent display formatting.

The phase route bounds each compiled plan and live state at 262,144 terms,
individual rational numerator/denominator sizes at 4,096 bits, and cumulative
arithmetic work at 100,000,000 charged operations. At most two states coexist
during a gate; compiled gate storage is separate. Probability text is limited
to 1,000,000 characters per outcome and 4,000,000 characters in total. Resource
or cancellation failures produce no partial result and do not retry through an
unbounded route. Callers still need the process timeout described above.
