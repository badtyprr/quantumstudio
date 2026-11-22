# Deutsch lesson candidate audit

The candidate at `7e3b4a6d` evaluated every math occurrence in the pinned Deutsch notebook. The 69 occurrences include repeated names, the two truth tables, aligned derivations and the final piecewise state. Each ledger entry records its cell and offsets, literal input, digest, evaluation mode, intended meaning, worker Copy result and applicable substitution checks. The worker SHA-256 was `48605a02a1afa9ba83754d9741c4b8c8d5e8cf24edc4cb3e88f416a27a09f5a5`. [Formula ledger](ibm019-formula-audit.jsonl)

The Windows app saved and reopened each original formula in its selected mode, copied its result, and evaluated the copied text again. All 759 checks passed across the 69 inputs. Binary word mode preserves the concatenation in M010. Binary oracles mode preserves the function calls in twelve scalar and state expressions. Scalar algebra keeps the bit named c formal in M045, M047 and M048. At M046 the worker and Windows app printed the two terms of an addition in different orders. Both recorded forms survived re-entry and gave the expected truth value for all four bit assignments.

The standalone replay checks the notebook digest and source spans before evaluating the formulas. Its 195 binding checks cover the four truth tables, valid and invalid membership claims, the sign for negative and positive integer exponents, and correct and altered states and gates. For the circuit shown in both original figures, it checks the state after each pair of initial Hadamards, the query and the final top-wire Hadamard, followed by both measurement probabilities. All 20 circuit checks passed. The top wire is the rightmost tensor factor. [Replay script](replay-ibm019-formulas.py)

Both SVGs were verified against Git blob IDs in the pinned tree and inspected in a rendered view. The first shows a zero result for a constant function and one for a balanced function. The second labels the three intermediate states. Their blob IDs are `f501e6439c2806b97d0765814ab14bdbbce8cc56` and `0845a7ceb89ccf34b0bb79b089e88ab41c3b04b1`, respectively. [Circuit](https://raw.githubusercontent.com/Qiskit/documentation/079769d205eb3b60e077820060274c7b0359c123/public/learning/images/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/Deutsch-circuit.svg) · [Intermediate states](https://raw.githubusercontent.com/Qiskit/documentation/079769d205eb3b60e077820060274c7b0359c123/public/learning/images/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/Deutsch-circuit-states.svg)

The pinned notebook SHA-256 matches the earlier Windows execution record for cells 2, 3, 5, 7, 9, 11, 13 and 15. That run checked the original output figures, classification and reference results for all four oracles. Published-package verification and Linux execution of the pinned notebook remain open. [Notebook](https://raw.githubusercontent.com/Qiskit/documentation/079769d205eb3b60e077820060274c7b0359c123/learning/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-algorithm.ipynb) · [Windows execution](../dev13/deutsch-notebook-revisions.json)

Run the following command from this directory with the worker, pinned notebook and directory containing both SVGs.

```text
python replay-ibm019-formulas.py WORKER NOTEBOOK --figures SVG_DIRECTORY
```
