# IBM-028 phase-estimation lesson review

The [open binary fraction checks](ibm028-open-bits.json) verify M074 and M076 in Binary fraction mode for all eight printed prefixes with five different tails. The two formulas accept the same phase, including when the doubled phase exceeds one. Substitution of the fifth digit before the fourth preserves both positions. Windows restored the selected mode and the Copy text for both original formulas.

## Earlier checks

The [pinned source and worker baseline](ibm028-inventory.json) records 396 mathematical expressions, 17 figures and zero code cells. At 0f9dd907, 371 expressions returned exact results and 25 produced diagnostics.

The [percentage replay](ibm028-percentages.json) covers all seven TeX percentages. At c30f7c06, 378 expressions returned exact results and 18 produced diagnostics. Copy changed on first re-entry for 33 of the exact results.

The [probability-plot checks](ibm028-probability-plots.json) compare all 14 curves in five source figures with the phase-estimation distribution and evaluate 28 reference calculations in the worker.

The [circuit and geometry checks](ibm028-figures.json) cover the other 12 figures, including all 32 inputs to the recursive Fourier circuit. At ebb26847, the printed Fourier matrix M191 evaluates to true and a changed coefficient gives false.

The [M214 eigenstate set checks](ibm028-ket-families.json) verify the inclusive endpoint N-1 through the source, display and Copy, with N set to 1, 2 and 4. At 05e3845e, 380 expressions returned exact results and 16 produced diagnostics.

The [one-bit fraction checks](ibm028-bit-fraction.json) at 318f1a9f verify both rows of M039 and independently falsify each row by changing its value.

The [Windows sessions](ibm028-bit-and-dimension-sessions.json) restored M039, M214 and six bit substitutions with stable Copy. Matrix dimensions mode preserves both axes for M125 and M178.

The [two-bit arithmetic checks](ibm028-two-bit-arithmetic.json) cover 11 expressions and 270 substitutions across source, display and Copy. At c24ab0d4 all 11 displayed expressions reopen with the same meaning as their sources in Windows, including finite-domain membership. For M111 through M114 select Binary fraction digits.

The [four phase estimates](ibm028-fraction-digits.json) evaluate to 0, 1/4, 1/2 and 3/4 from either the source math span or the span with its preceding point. All eight inputs restored and re-entered correctly in Windows.

The [single-control state checks](ibm028-kickback-states.json) verify M014, M015, M017, M021 and M022 for eigenphases 0, 1/4 and 1/2 from display and Copy, with a false-state control for each.

The [Fourier checks](ibm028-fourier-names.json) distinguish the family name M132 from the four-dimensional operator M130, verify the displayed matrix definition M128, and reject replacing any one coefficient with zero in the six printed matrix identities. Substituting four angles into M217 and M219 verifies both phase-gate definitions and rejects the gates with a half-turn offset. At 7534e791, 381 source expressions returned exact results and 15 produced diagnostics. For M103 select Binary word.

The [ordered-bit checks](ibm028-bit-word.json) preserve the two-bit width and verify x = 2a_1 + a_0 for all four assignments, including after Windows save, reopen and Copy re-entry.

The [M215 orthogonality checks](ibm028-orthogonality.json) verify all 29 ordered column pairs of the two-, three- and four-dimensional Fourier transforms and reject a mismatched state for every pair. The symbolic equation survives Windows save, reopen and Copy re-entry.

The [geometric-series checks](ibm028-geometric-series.json) verify M201 and M329 for 32 ratio and count pairs, including ratio one and empty sums.

The [M328 probability checks](ibm028-phase-probability.json) verify 84 on-grid and six off-grid outcomes using the display, Copy and Copy after re-entry. Windows save and reopen preserve the formula. Copy changes the bound index name and multiplication spelling on re-entry.

The [four-dimensional Fourier basis checks](ibm028-fourier-basis.json) verify M118, M119 and M123 against all four columns, and M128, M130 and M133 against the Fourier transform. For M119 append a dimension subscript of 4 to each numeric ket, using the two-qubit register specified in the text. For M123 declare V as a 4 by 4 unitary before pasting the original expression. M119 with dimension subscripts and M123 with this declaration both preserve their Copy text after Windows save, reopen and re-entry.

The [arc and chord checks](ibm028-signed-endpoints.json) distinguish M337 (the closed interval, including zero) from M339 (only its two endpoints). M338, M341 and M342 agree with exact substitutions at both endpoints and on either side of zero. M341 excludes zero because its denominator vanishes there. The arc-to-chord ratio reaches π/2 at both endpoints.

The [ordered ket lists](ibm028-ket-lists.json) in M127 and M134 preserve all four Fourier labels in order. M135 enumerates the four-dimensional computational basis. M179 keeps the dimension symbolic until supplied. Entry-by-entry checks cover dimensions 1, 2, 3, 4 and 8, and all four lists preserve their Copy text after Windows save, reopen and re-entry.

The [rounded-value checks](ibm028-rounded-values.json) verify all seven roots in M176 and distinguish the exact probability bound in M358 from its decimal approximation. For a printed decimal following ≈, compare at its stated number of decimal places, component by component for complex numbers. The probability 0.4051 falls below the exact lower bound even though it exceeds the printed 0.405. Both source expressions retain stable Copy text across Windows save, reopen and re-entry.

The [M224 state-mapping checks](ibm028-state-action.json) compare the printed mapping with a circuit assembled from controlled-phase gates on every basis input for two through five qubits. Removing the gate on the most significant bit changes the output exactly when the control and that bit are both 1. M199 and M265 also retain their meaning with explicit multiplication in copied exponents. At e0bafac0 the default-mode inventory has 393 exact results and 3 diagnostics.
