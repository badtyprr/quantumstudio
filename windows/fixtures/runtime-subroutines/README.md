# Runtime subroutine source fixtures

`measured-parity.qasm` retains the OpenQASM specification's parity operations and `parity(c ++ c2)` call. Its header, typed n=2 constant, missing declarations, explicit output and H/H preparation are disclosed additions. Expected output: parity 0 and 1 each with probability 1/2.

This fixture currently fails parsing in the pinned compiler. It is acceptance evidence, not a passing test. See [DEV-08b4 evidence](../../../docs/learning-evidence/DEV-08b4.md) for provenance, observed failure and remaining work. Do not simplify the call to remove the unsupported concatenation.
