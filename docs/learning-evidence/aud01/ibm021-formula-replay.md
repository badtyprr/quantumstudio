# Simon lesson formula replay

The Simon notebook at revision `079769d205eb3b60e077820060274c7b0359c123` consists of one Markdown cell. Its 177 math occurrences form 174 complete inputs. Occurrences M034 through M037 make up one ordered list split across four inline math delimiters. The ledger keeps the complete list and its original punctuation. [Formula ledger](ibm021-formula-audit.jsonl)

Run the replay with the candidate worker and the original notebook. It verifies the notebook hash, reads each formula at its recorded position, evaluates it and re-enters its Copy result in the same notation. The Windows application also passed 1,914 checks on candidate revision `99981c7c`. Each restored input and each second Copy matched the independent worker. [Standalone replay](replay-ibm021-formulas.py)

```text
python replay-ibm021-formulas.py WORKER simon-algorithm.ipynb
```

The replay verifies 462 concrete results. It checks the promise for every pair of three-bit inputs against the printed oracle table, including a wrong period. The checks also cover range and preimage identities, two-bit input registers with two- and three-bit output registers, all amplitudes before and after the oracle and final Hadamards, and the signed sums over each output's preimages. The probability equations accept the correct weights and reject changed weights. Set notation keeps the five-bit function outputs intact. The matrix equations use the GF(2) matrix products mode. [Matrix checks](ibm021-gf2-products.json)

The source circuit starts both registers at zero, applies Hadamards to the input, calls the oracle once, then applies Hadamards and measures the input. The source SVG hash matched the recorded figure at both pinned revisions. A fresh import of the eight-qubit OpenQASM circuit produced exactly four outcomes on the candidate worker. The probabilities for 000, 011, 100 and 111 were each 1/4, as required for the period 011. [OpenQASM circuit](ibm021-simon.qasm) · [Circuit and figure evidence](ibm021-circuit.json)

Published-package verification remains open.
