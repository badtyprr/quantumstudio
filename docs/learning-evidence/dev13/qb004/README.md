# QB-004 selected local notebook execution

The selected local route passes; QB-004 remains open. This
does not establish whole-notebook, provider, GUI, packaged or released acceptance.

The pinned `qBraid-Algorithms/bernstein_vazirani.ipynb` at revision
`86787e1ba372facc224f925189755e69c479828b` has SHA-256
`9a9ed236328a272a4858f5ac6af1019c8857eeee4fbf41544bf01bb140d34cce`.
The contract preserves the hashes and dispositions of all 33 source cells.
Original code cells 1, 2, 4, 6, 8, 10, 12, 14, 16, 18 and 24 execute unchanged
in a dedicated Windows Python 3.12.10 environment with 71 pinned distributions.
Cell 18 imports the provider class; it does not initialize a provider or submit a job.

## Explicit Windows compatibility

Original setup uses Unix-style single quotes around `qbraid[visualization]`.
Unadapted Windows execution produces pip exit 1, hidden by `%%capture` even
though IPython reports cell success. A separately labelled bootstrap translates
only the exact reviewed setup command into Windows argument quoting. The
existing setup observer still checks command identity, actual exit status and
installed distribution metadata/RECORD equality. Pip runs against the already
installed offline environment; this is not a general network-isolation claim.

Windows IPython also lacks the notebook's `%cat` alias. The bootstrap defines
`cat` as `type`, records both command forms, and restores the prior system
handler and alias during lifecycle cleanup. SDK methods remain unchanged.
The standalone probe checked that both displayed module files match their
generated contents. A real-kernel replay records successful bootstrap,
observation, cleanup and witness execution, with zero owned processes remaining.

## Mathematical and native checks

The witness strictly checks declarations, gates and measurement destinations for
the two generated complete programs. Integer-state evolution retains exact
Hadamard normalization and compares the unitary-prefix state against the
Bernstein–Vazirani answer with the ancilla in the minus state. These are authored
state calculations, not native observations of phase.

The source secret is listed in q0-first order. Native high-to-low classical
display is therefore `1101` for secret `1011`, and `101` for secret `101`.
Mutation tests reject missing ancilla preparation, changed oracle gates,
changed register width and changed measurement destinations.

Separate native controls retain the generated `oracle.qasm` and `bernvaz.qasm`
bytes. Authored wrappers prepare all 16 basis inputs for each module and measure
all four wires. Both exact and sampled execution pass: 64 checks. Oracle
expectations use parity of the three data bits; algorithm expectations account
for both input ancilla states. Sampling checks support, total 10,000 shots and
probability tolerance; it does not require an exact 50/50 random count.

The native worker is the clean build of revision
`ae30847d2c5033638027097ee6966134b42742b4`, SHA-256
`89694175ee99a6aa3a968c7f694c24c676ec7c8c0b88f5c82941f9dc8dd6c1ed`.
File-based compiler output retains its source bundle; the test adapter consumes
the bundle's `Circuit` field. This does not test a new frozen compiler package.

## Outstanding acceptance

Provider initialization, device discovery, submission, result retrieval,
postprocessing and histogram cells remain explicitly excluded. A separate
authored collision probe shows that cell 29 overwrites rather than sums counts
when removing the last bit merges keys; no actual provider collision or provider
bit-order convention has been established. The fresh run retained identical bytes and sizes for all 24,909 files
(557,610,171 bytes) in the environment, base interpreter and notebook runtime
between its before/after inventories. This does not exclude transient writes.
Exact-head review, required CI, packaging and release remain pending.

The [artifact index](index.json) binds 170 evidence files by size and SHA-256.
Dependency closure verifies 71 distributions and 127 active requirements.

External working evidence is under
`cleanup-audit/learning-coverage-20261117/qb004-notebook/`, with prerequisite
probes under the adjacent `qb004-prerequisites/`. The current implementation has
49 passing focused tests. Initial driver failures are retained: a misplaced lock
before the first kernel run, an unsuitable Python environment for the broad test
suite, and passing a complete source bundle to the circuit-only native adapter.
None is counted as a successful verification run.
