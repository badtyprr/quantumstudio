# DEV-11a: dense multiplication cost isolated

This follow-up diagnoses the existing audit's timeouts without changing symbolic or quantum implementation code. Original inventory commit: `b67443d645ce245a0f4d729e37941fe499033852`. Product source base remains `0fed41cb5637c578737278bf13f59590a56d6cf4`; all probes use released worker `35d9e753af19372a8f6472404726955eeba2190e`, SHA-256 `a62b058870263d33c979a84a274f6a0b37779c8a72fd91e146e2ec201aa194a8`. No new binary, build, GUI, merge or release is involved. DEV-09's active measurement/instrument work is untouched.

## Reproduction and minimization

The original Shor expression computes `C*E*V`, with C a minimum-weight correction, E an error, and V the complete 512-by-2 encoding isometry. Its mathematically equivalent form is `C*(E*V)`. Both logical columns, including leakage and one common global phase, are compared with the independently specified expected result.

The new loop runs each form twice, serially, with a 12-second per-process budget. Original left association timed out in both trials; right association completed correctly in 5.568 and 5.235 seconds. This shorter deadline diagnoses the same slowdown previously observed with 90-second timeouts; it is not a new product performance contract.

Removing the encoded state still times out. Replacing the decoder with its independently validated Pauli result still times out. The reduced expression is:

```text
quantum:pauli("IIIIIIYII")*pauli("IIIIIIYII")
```

The independently expected result is the 512-by-512 identity. At the 12-second observation boundary, nine qubits are needed for this timeout; reducing the dimension to eight completes. This is a minimal dimension for this measured deadline, not a claim that eight-qubit execution is suitably fast.

| Probe | Worker wall time | Outcome |
|---|---:|---|
| Decoder C alone | 4.988 s | Full matrix equals the expected Y Pauli |
| C*E, removing V | >12 s | Timeout |
| E*E, removing decoder | >12 s | Timeout |
| Same Y square, 8 qubits | 11.219 s | Full identity matches |
| Same Y square, 7 qubits | 1.255 s | Full identity matches |
| Same Y square, 6 qubits | 0.195 s | Full identity matches |
| Same Y square, 5 qubits | 0.066 s | Full identity matches |
| Same Y square, 4 qubits | 0.048 s | Full identity matches |
| Same Y square, 3 qubits | 0.045 s | Full identity matches |

A final reduction removes Pauli construction too: `quantum:qidentity(512)*qidentity(512)` also times out at 12 seconds, while either identity alone completes in 1.421 seconds. Thus neither stabilizers, encoding, Pauli parsing nor imaginary entries are required. The power-of-two dimension boundary is the smallest one tested for this deadline; arbitrary matrix dimensions were not exhaustively minimized.

## Competing explanations and evidence

Before the follow-up probes, the ranked explanations were (1) dense cubic multiplication despite sparse operands, (2) expensive exact complex arithmetic from Y, and (3) large-result formatting. Each follow-up changed a single relevant feature.

- A real X square at nine qubits also exceeds 12 seconds. Complex arithmetic is not necessary for the slowdown.
- `trace(Y*Y)` at nine qubits still exceeds 12 seconds. At eight qubits it completes correctly with 256 in 11.355 seconds, essentially the full-matrix product time. Large-result formatting is not the dominant cause.
- Producing the nine-qubit Y matrix alone takes 1.363 seconds; producing the 512-dimensional identity takes 1.421 seconds. Construction/output alone cannot explain the product timeout.
- The seven-to-eight-qubit product time grows by about 8.9 times, consistent with cubic work as dimension doubles; startup and other work prevent interpreting this as an exact asymptotic measurement.

Static source inspection identifies the matching path: [QuantumAlgebra.cc](../../../libqalculate/QuantumAlgebra.cc) at lines 658–676 routes concrete qmul operands to `multiply`, whose lines 312–323 invoke generic multiplication and evaluation. [MathStructure-calculate.cc](../../../libqalculate/MathStructure-calculate.cc) at lines 1799–1825 performs row/column/inner-index loops, calling `calculateMultiply` and `calculateAdd` even for zero entries. The 512-square product visits 512³ = 134,217,728 inner terms. Right-associated 512-by-512 times 512-by-2 products visit only 524,288 terms each.

**Finding:** the slowdown is localized to the concrete dense multiplication path, independently of the stabilizer decoder and encoded state. There is no sampling-profiler attribution or patched-binary A/B result; the conclusion combines controlled executable comparisons with the explicit source loop. This is not a numerical-correctness failure or evidence that stabilizer recovery is missing.

## Proposed implementation task and ownership

Refine DEV-11a to a finite exact sparse-matrix multiplication optimization. The narrowest ready regression seam is `quantum:qidentity(512)*qidentity(512)`, with the Pauli, real-X and trace-only variants retaining the source-derived connection. A fix may belong in the numeric matrix core (`MathStructure-calculate.cc`); a quantum-specific specialization would also touch `QuantumAlgebra.cc`. The latter is shared registration/evaluation territory: coordinate with DEV-09 before editing it. Do not modify measurement, ensemble, instrument, POVM, Naimark or partial-trace implementation as part of this task.

Acceptance proposal:

1. The reduced identity product and all three nine-qubit variants finish within the 12-second observed regression budget on the same host and return the full expected identity or trace. Retain two serial repetitions to separate noise from consistent behavior.
2. The original 12 Shor timeout fixtures complete under their original 90-second audit budget and match both complete logical columns. Re-run the full finite DEV-11 fixture set, retaining exact signs, dimensions and relative phases.
3. Exercise both left/right sparse operands, rectangular products, signed/complex Paulis, zero matrices and dense controls. Preserve singleton-matrix/scalar rules, cancellation behavior, approximation/precision metadata, and errors for incompatible dimensions.
4. Restrict zero-skipping or specialization to a domain where it preserves semantics. Symbolic or non-finite operands require separate treatment: blindly skipping `0*infinity` or unresolved terms can change behavior. Do not globally reassociate arbitrary symbolic products as an untested shortcut.

No fix was attempted because this work retains the user's inventory/fixtures-only boundary. The red regression signal remains intentional; the original issue is not marked resolved. No temporary product instrumentation was added.

## Reproduce and evidence

From the isolated checkout, using fresh output directories:

```powershell
python docs/learning-evidence/dev11/timing_probe.py --root F:/src/libqalculate --output F:/src/libqalculate/cleanup-audit/dev11-perf-new --timeout 12
python docs/learning-evidence/dev11/product_cost_probe.py --root F:/src/libqalculate --output F:/src/libqalculate/cleanup-audit/dev11-min-new --timeout 12
python docs/learning-evidence/dev11/product_cost_probe.py --root F:/src/libqalculate --output F:/src/libqalculate/cleanup-audit/dev11-hyp-new --timeout 12 --suite hypotheses
```

The timing loop returns 1 for reproduced slowdown, 0 only when every original/equivalent result completes correctly, and 2 for inconclusive outcomes. The product-cost script is a measurement tool; inspect `correct` and `status`, not its exit code, to assess observations. Timeouts terminate only that probe's worker subprocess.

[performance-results.json](performance-results.json) contains full paired-loop stdout and the minimization/hypothesis timings with hashes of larger stdout files. Full output files remain outside the clone in `cleanup-audit/dev11-20261101-a7c4/perf-loop-01`, `perf-minimize-01`, `perf-hypotheses-01`, and `perf-identity-01`. Timing begins before process launch and ends after process completion; matrix-result validation is outside the reported worker duration in the minimization script. These are single-host elapsed measurements, not universal deadlines or throughput benchmarks.

The final identity reduction is reproducible with the product-cost helper using `--suite identity`. The follow-up records 19 observations: 12 completed correct comparisons and seven timeouts. These are additional diagnostic observations, not additions to the original 286 source-audit fixtures.
