# Deutsch–Jozsa lesson candidate audit

Revision `788296be` evaluated all 168 displayed and inline formula occurrences in the pinned notebook. The ledger records each source span, its SHA-256, the selected input mode and the exact Copy result. The replay verifies 443 bound results, including altered inputs and intermediate expressions. For 24 occurrences the ledger also links to the larger formula-specific checks. [Formula ledger](ibm020-formula-audit.jsonl) · [Standalone replay](replay-ibm020-formulas.py)

The Windows app evaluated each literal, copied its result, saved and reopened its session, and recalculated both the restored input and the copied expression. All 1,848 checks passed. Every restored result and every re-entered Copy string matched the worker. The tests used the GUI with SHA-256 `11ea710947706d2020be8a0e60ee5c9d798f5d624859492075fa4e240244ae0d` and the candidate worker with SHA-256 `04b222c48ed660ec916a8e094a69c02548f02ced2aac747932d5e9e8b03037b6`.

Binary word mode retains the width of the all-zero word and accepts both the numeric bit and one-bit word forms of the Hadamard input in M028. Binary oracles mode supplies the binary alphabet in the phase and interference sums. Scalar algebra mode in M126 preserves the bit named `c`. In M041 the repeated zero ket takes its width from the Hadamards applied directly to it. Supplying only `n` gave a true equation at widths one through four.

The circuit figure starts its input register in the all-zero state and the bottom auxiliary qubit in the one state. Every wire receives a Hadamard before the oracle. The second layer of Hadamards and the measurements apply only to the input register, which produces the word `y`. The original SVG was rendered and its SHA-256 matched both audited repository revisions. The candidate also reran the eight source cells and the native circuit replay for all 72 promised three-bit Deutsch–Jozsa functions and all 16 four-bit Bernstein–Vazirani secrets. The largest absolute probability error was 3.51 × 10⁻³³. [Original circuit figure](https://raw.githubusercontent.com/Qiskit/documentation/079769d205eb3b60e077820060274c7b0359c123/public/learning/images/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/Deutsch-Jozsa.svg) · [Circuit results](ibm020-query-algorithms.json) · [Circuit replay](replay-ibm020-native.py)

The eight original code cells were verified on Windows and Linux. The formula audit used notebook SHA-256 `eb5801cde14e135802785c00092569b141deba7f3c091550b0ef0826654fc0a4`, which is identical at the two audited source revisions. Published-package verification remains open. [Pinned notebook](https://raw.githubusercontent.com/Qiskit/documentation/079769d205eb3b60e077820060274c7b0359c123/learning/courses/fundamentals-of-quantum-algorithms/quantum-query-algorithms/deutsch-jozsa-algorithm.ipynb) · [Windows notebook runs](../dev13/deutsch-notebook-revisions.json) · [Linux notebook runs](../dev13/deutsch-linux-runs.json)

Run the replay with the built worker, the pinned notebook and the original circuit SVG.

```text
python replay-ibm020-formulas.py WORKER NOTEBOOK --figure Deutsch-Jozsa.svg
```
