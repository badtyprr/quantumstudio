# Runtime subroutine source fixtures

`measured-parity.qasm` retains the OpenQASM specification's parity operations and `parity(c ++ c2)` call. Disclosed completions: header/include, typed n=2, missing bit declarations, explicit result output, H/H preparation, and explicit zero initialization of the parity accumulator. Expected parity probabilities: 0=1/2 and 1=1/2.

The pinned/reference grammar does not accept concatenation inside call arguments. QuantumStudio adds a compatibility extension for this documented example: `++` has the lowest expression precedence and copies the left sequence into lower register indices. See [DEV-08b4 evidence](../../../docs/learning-evidence/DEV-08b4.md). Source-prototype checks pass; packaged acceptance remains pending. This is not an unchanged full source program or notebook.
