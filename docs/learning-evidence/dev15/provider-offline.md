# DEV15 offline provider protocol adapter

This increment implements deterministic protocol and gate-count handling derived
from the pinned qBraid SDK sources. It does not execute an original notebook,
submit a job, verify hardware, or implement CUDA-Q's different native REST route.
The four added files are independent of the notebook runner and its environments.
Integration base: `244681403225583af607d6839ec39511d83fc2ab`.

## Source provenance

`windows/dev15-provider/fixtures.json` carries the five original installed-source
paths and SHA-256 values for qbraid 0.13.0 / qbraid-core 0.6.42. Those hashes were
rechecked before fixture preparation. Source paths identify the retained audit
environment; they are not required to run these portable standard-library tests.
The package source is the primary authority, not generated fixture output.

| Primary file | SHA-256 |
|---|---|
| qbraid/runtime/native/job.py | `97fefd4974818428534cd3df7db8e47fce2c5098897434c7be99da7922aaa9e6` |
| qbraid/runtime/native/device.py | `e57e38c9cd4c14e8bf0599dab9433ba2ae8880d78518c73091201c8fa56c530e` |
| qbraid/runtime/job.py | `084cd3a355bb03eac03e2c4a7535b21c368261e60e94894a508d8f91d2b76dd7` |
| qbraid/runtime/result_data.py | `5f6442eaab6bedde52c36e36687f2d5d16ade079e13eb838ab423532dec2a34b` |
| qbraid_core/services/runtime/schemas/enums.py | `ad480477ff25499a76ea8e933c0ab8a700010b4931cca4660272f8bacd89f553` |

The source exposes get_job, cancel_job, get_job_result and raw measurement_counts.
Its ten status tokens include HOLD: results withheld for account attention, even
though the SDK terminal_states helper lists only COMPLETED, CANCELLED and FAILED.
The adapter's explicit HOLD stopping policy prevents indefinite polling. This is
a policy based on source inspection; no live service behavior was observed.

Fixtures are authored synthetic data, not captured server responses. Their
canonical payload SHA-256 is
`704b22b2cec12857518b217c9fc47c423eb0d285f0b30410a83d6d5ca2a34361`;
the test module checks both this digest and the exact set of 40 scenario IDs.
Parameterized negative cases live visibly in the test source and are printed
individually by its direct runner. Full implementation and test-file hashes must
also be retained with integration evidence; the fixture digest alone does not
bind the whole test suite.

## Interface and semantics

`OfflineJob(handle, transport, clock, sleeper)` accepts an already known identity
and an injected deterministic transport. `poll`, `cancel`, `fetch_counts`,
`snapshot` and `export_handle` operate on that identity. `from_handle` restores
identity without proving that a remote job exists. `record_submission_unknown`
records an unresolved outcome and correlation ID without sending anything.
There is no submit method, SDK import, client constructor, credential lookup,
network implementation, or automatic resubmission/reconciliation.

The injected transport has only get_job(job_id), cancel_job(job_id), and
get_job_result(job_id). Its finite fixture responses are reduced SDK-derived
shapes: `{status: token}`, `{acknowledged: true}`, or
`{experiment_type: gate_model, measurement_counts: histogram_or_list}`.
They are not asserted to be the complete live API schema. A future live adapter
must map and verify the actual SDK/service schema separately.

Snapshots copy remote_state, local_wait_state, result_state, cancellation_request,
history, last_error, result_attempt_error, and count_evidence. Input mutations and
snapshot mutations cannot alter retained successful count evidence. Remote
terminal states are not silently downgraded: later conflicting observations enter
history and set conflict while preserving the accepted terminal state. An
explicit subsequent poll may recheck even a terminal job, enabling conflict
detection; HOLD may be explicitly resumed after account resolution.

Polling requires positive finite timeout/interval and a positive integer request
limit. It checks time before and after requests, bounds sleep, and stops at the
request limit even with a constant clock. A response observed after the deadline
is retained, but local_wait_state reports deadline. A synchronous transport that
hangs cannot be preempted here: only bounded deterministic transports are
supported. Any future live transport needs its own per-request deadline.
Local deadline never means remote cancellation.

Cancel acknowledgment does not imply CANCELLED. CANCELLING remains pending;
COMPLETED may win a cancellation race. Already terminal jobs send no cancel
request. Lost cancel responses produce outcome_unknown and are not retried.
401/403/404/429 retain distinct categories; arbitrary transport messages and
headers are excluded from evidence. A 404 is not proof that no paid job exists.

Result fetch requires observed COMPLETED, makes at most one request per explicit
call, and never manufactures an empty successful histogram. An explicit retry is
a result read only. Malformed or unavailable later results cannot overwrite
previously validated evidence; result_attempt_error records the failed attempt.

Count specifications declare width 1..4096, exact positive shot total, binary or
decimal encoding, and result bit order. Binary keys require exactly width ASCII
bits; decimal keys require Python integers in range. Decimal expansion is padded
before the declared order is applied. Canonical keys are MSB-left result bits,
not a claim about physical qubit wiring. Original entries and zero counts are
preserved. Batches retain circuit position and require per-circuit totals.
Malformed keys, fractional/boolean/negative counts, mixed encodings, unavailable
results, mismatched totals and unsupported shapes fail explicitly.

Strict handle schema v1 contains exactly schema, source_id, provider, device_id,
job_id, client_correlation_id and submission_state. Provider is qbraid-sdk;
submitted requires job_id; outcome_unknown requires a correlation ID. Duplicate
JSON fields, unknown keys/schema and malformed identities are rejected without
echoing input. IDs are caller-supplied credential-free strings (1..256 characters,
no control characters); the schema cannot recognize a secret deliberately placed
inside a valid ID field. Handles do not persist observations, results or tokens.

## Finite acceptance and reproduction

Run from the repository root with Python 3.12.10 (no third-party packages):

```text
python -B windows/dev15-provider/test_offline_adapter.py
python -B -O windows/dev15-provider/test_offline_adapter.py
```

The 40 named scenarios comprise S01–S10 (every status), L01–L10 (history,
deadlines/request bounds, cancellation and conflicts), C01–C08 (independent
asymmetric counts/order/batches and malformed controls), H01–H05 (strict durable
identity and unknown submission), E01–E07 (typed failures and unavailable results).
Each checks observable state and the exact fixture operation/ID trace. Expected
01/10 asymmetry prevents symmetric Bell results from concealing a bit reversal.
Normal and optimized execution must both pass; validation uses explicit branches,
not Python assert statements. Independent Standards/Spec review must bind final
files and integration commit before this increment is accepted.

This finite adapter does not establish provider API compatibility, authentication,
paid-job authorization, cost limits, remote cancellation guarantees, notebook
completion, state coherence, hardware wiring, postselection, pulse/analog results,
QIR execution, or CUDA-Q transport compatibility. Those remain separate gates.
