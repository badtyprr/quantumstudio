# IBM-022 and IBM-023 source audit

The IBM-022 introduction at Qiskit documentation revision `f842259423a7adc9adeafd54153cdb5d3c5b680b` has one Markdown cell, `6a9965ad`. It introduces explicit inputs, computational cost and classical subroutines. The cell contains no delimited formulas, executable cells or circuit diagrams. It embeds IBM video 134056222 and links the corresponding lecture and slides. [Pinned introduction](https://github.com/Qiskit/documentation/blob/f842259423a7adc9adeafd54153cdb5d3c5b680b/learning/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/introduction.ipynb)

| Slide pages | Content | Checklist coverage |
| --- | --- | --- |
| 1 | Title | IBM-022 |
| 2–6 | Prime factorization and greatest common divisors | IBM-023 |
| 7–25 | Encoding, operation counts, circuit depth and asymptotic cost | IBM-024 |
| 26–30 | Toffoli gates and reversible simulation of Boolean circuits | IBM-025 |

The introduction notebook SHA-256 is `57bff76fa779ad3f46c72ae08daf1fb31fe0731d8e4d823ab0c26e1541df99ea`. The linked 30-page deck SHA-256 is `7c4207ec2e3bbf2bb6b399709995a9d682ec6281965b50a8cfd8f1d0124d1d9b`. The table records slide topics from the downloaded PDF. Diagram-by-diagram and video replay remain open. [Lecture slides](https://ibm.box.com/public/static/yic6g33o4xn103oaay8xqbbwyc64d0jz.pdf) · [Lecture video](https://youtu.be/2wxxvwRGANQ)

## Factoring and GCD notebook

The IBM-023 replay executes the six original code cells in order under Python 3.12.10 with SymPy 1.14.0 and mpmath 1.3.0. For the five result-producing cells it also exercises the corresponding calculator operations. The RSA-1024 cell prints an integer. The RSA-250 cell verifies a supplied factor pair by multiplication. Only the two calls to SymPy’s `factorint` ask for factor discovery. [Pinned notebook](https://github.com/Qiskit/documentation/blob/f842259423a7adc9adeafd54153cdb5d3c5b680b/learning/courses/fundamentals-of-quantum-algorithms/quantum-algorithmic-foundations/factoring-and-gcd.ipynb)

To reproduce, use the installation’s worker with its DLLs and definitions available and pass a downloaded copy of that notebook. The replay exits with a failure status when an expected calculator result is missing. The JSON captures the exact input, mode, expected value and observed result for each case.

```text
python docs/learning-evidence/aud01/replay-ibm023.py factoring-and-gcd.ipynb path/to/quantum-worker.exe
```

At `2965fa7ab`, all six Python cells reproduced their outputs outside the application. The Windows GUI returned exact results for the 23 source math occurrences and four numerical adaptations. For each of these 27 inputs it restored the session and re-evaluated the copied result exactly. The separate GUI and worker timeouts for cell `53f998fc` are recorded under DEV-18. [Per-input evidence](ibm023-factoring-baseline.json)
