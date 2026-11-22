# Measuring computational cost

The candidate evaluated all 170 formula occurrences in the source notebook. The ledger records each position, source hash, notation and Copy result. The Windows replay passed 1,870 checks. All 170 restored inputs and second Copy results matched the independent worker. Another 165 Windows checks exercised the two meanings of epsilon and the indexed circuit-size equations. [Source ledger](ibm024-formula-audit.jsonl)

Run the replay with the calculator worker and the original notebook.

```text
python replay-ibm024-formulas.py WORKER measuring-computational-cost.ipynb
```

The replay verifies 278 bound results. In the encoding table, Binary word notation gives ε value zero and width zero. In the growth estimates, ε remains a scalar. Set notation lets a circuit family member retain its index in the cost equation. Binding n to 4 selects the circuit C₄. Its measured size can then be compared with either adder's predicted gate count. The replay also tests endpoint inequalities, integer division ranges, modular powers, bit lengths inside complexity bounds, and the distinction between linear and quadratic circuit costs. [Replay script](replay-ibm024-formulas.py)

The supporting replays cover the two encoding tables, the gate matrices and division equations, the deferred measurement diagram, and the Boolean circuit drawings. The four-bit adder truth tables check all 256 input pairs for both gate sets, counting 31 gates with native XOR and 73 with the expanded XOR. [Encodings](replay-ibm024-encodings.py) · [Gates and division](replay-ibm024-gates-division.py) · [Deferred measurement](replay-ibm024-deferred-measurement.py) · [Boolean circuits](replay-ibm024-adders.py) · [Cost bounds](replay-ibm024-costs.py)

The six figure files matched at notebook revisions `f842259423a7adc9adeafd54153cdb5d3c5b680b` and `079769d205eb3b60e077820060274c7b0359c123`.

| Source figure | SHA-256 |
|---|---|
| standard-computation.svg | `9e5ebec265e9dff30cb00a80a56b66daff3cf7b08221863fc4da60894fcd9cc0` |
| deferred-measurement.svg | `83df1b30d9aeb6926942716db1ce1c1e37bcf0f07814178f98b8496cb5255fa3` |
| Boolean-circuit-XOR.svg | `514e2a7827b87c79b0cd2585fd452c7ab6660c46b48e03cbf702f9189792c3f8` |
| half-adder.svg | `bd2a73833fd8238d633634bcb56cac1e26f83e9408c1e55f8d13e5d38d1d9478` |
| full-adder.svg | `16b9d6b3d7a8780f7e0de0e76ca2ee0982abb61d2d73e27705efa2d75f37fedf` |
| addition-circuit.svg | `69d87124345de80b93bd4cb18050a9ee764341ed8447b81f36b3d71f1926364b` |

Published-package verification remains open.
