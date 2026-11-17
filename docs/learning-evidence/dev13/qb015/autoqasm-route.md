# QB-015 selected AutoQASM construction and failure diagnostics

The pinned original notebook's cells 8, 10, 11 and 18 now execute unchanged
through the owned notebook runner. This covers imports, `n = 4`, and both
algorithm definitions. The complete 23-cell original is retained; each omitted
code cell has an explicit disposition in `contracts/qb015.json`. QB-015 remains
open. This is not whole-notebook, provider, or successful circuit acceptance.

The `autoqasm-win-py312` profile pins 89 distributions including pip, with
retained wheel hashes. Dependency verification found 145 active requirements
satisfied. The actual installed AutoQASM version is 0.7.0; qbraid-qir is 0.6.1.
The runner's before/after metadata inventory passed. A before/after hash of every
environment file was not performed, so that stronger integrity claim is absent.

## Authored observations after original definitions

Both `.build()` calls and `.to_ir()` serialization succeed. Generated OpenQASM
declares five qubits and measures data qubits 0–3 into four scalar registers.
The witness saves both OpenQASM programs and their converted QIR text/bitcode.
These calls are authored observations; original cells 14 and 19 combine build
with cloud submission and remain excluded in their entirety.

Two failures are preserved, not silently repaired:

* Braket's local simulator rejects both programs because measurements occupy
  four separate classical registers. No successful counts are reported.
* The generated QIR passes LLVM verification but declares four result slots and
  records IDs 0–4. Slot 4 is out of range. The installed Base profile iterates
  `module.num_qubits` when generating output records. LLVM verification is not
  evidence that these result references are semantically valid.

Separate prerequisite diagnostics show QuantumStudio's current importer rejects
both original QIR forms at its four-qubit limit. Increasing that limit alone
would not repair the invalid output record. No importer limit or external package
was changed here. No cloud job was submitted and no provider bit order is inferred.

`accepted: true` in this diagnostic witness means the selected definitions build
and the pinned failures are reproduced. Its `qir_semantically_accepted` fields
are false, counts are null, and `whole_notebook_complete` remains false. A change
to either expected failure stops this diagnostic for investigation; it is not a
requirement that future corrected compilers continue to fail.

## Runner correction and validation

The first integrated run exposed a runner defect: SDK warnings on stderr were
concatenated into the stdout JSON protocol. The runner now parses stdout alone
and retains stderr separately in `witness_stderr` and in the executed notebook.
Warnings cannot provide acceptance. Invalid stdout still fails parsing.

Six focused tests cover interleaved streams, stderr-only rejection, invalid
stdout, and result-reference distinctions. All passed, as did 24 existing
selection/profile tests. Final run02 executed all four selected cells and both
diagnostic observations successfully, with forced cleanup confirming zero active
owned processes. Run01's parsing failure remains retained.

Evidence is under `cleanup-audit/learning-coverage-20261117/` in the main
repository: `qb015-autoqasm-prerequisites` and `qb015-autoqasm-route/run02`.
The adjacent `autoqasm-route.json` binds retained artifacts. The earlier
[mathematical audit](README.md) is separate evidence. GUI, native five-qubit
execution, original provider cells, CI, packaging and release remain open.
