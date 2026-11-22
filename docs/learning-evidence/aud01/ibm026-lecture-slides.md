# IBM-026 phase-estimation lecture slides

The lesson introduction links to John Watrous's 41-page slide deck. The public PDF has SHA-256 `a79cc94cc28ebf9efd214364ffb616796fab520abe7a22a9f920659b40ff95ab`. Each page was rendered for inspection. The accompanying replay performs 171 exact calculations using the calculator worker. [Original slides](https://ibm.box.com/public/static/jxase3mly99ui1n1fg8pvp6bzymbdgrh.pdf) · [Runnable examples](replay-ibm026-slides.py)

| Pages | Material | Verification |
|---|---|---|
| 1–5 | Spectral decomposition, the phase-estimation promise and phase modulo one | The related notebook audit records the source expressions and their readings. [Phase-estimation problem](ibm027-lesson-results.json) |
| 6–12 | Phase kickback, repetition and two controls | The replay checks both measurement probabilities for one and two applications at three phases. |
| 13–22 | Fourier columns, inverse transform circuit and recursive gate count | The replay checks each column in dimensions 2, 3, 4 and 8 and the recurrence for one through eight qubits. |
| 23–28 | Controlled powers, probability bounds, nearest phase estimates and repetition | The source notebook audit covers the circuits and probability curves. [Phase-estimation procedure](../IBM-028.md) |
| 29–35 | Orders of units, multiplication modulo N and orbit eigenvectors | The replay checks the powers of each unit modulo 21 and all 15 basis actions of multiplication by two modulo 15. |
| 36–37 | Random orbit eigenvector and rational reconstruction | The printed eigenvector index differs from the identity on page 34. The replay tests both forms across all four eigenphases for the order-four orbit. |
| 38–41 | Modular controlled powers, preparation of the input state and factoring | The equal superposition of the four orbit eigenvectors reproduces the starting ket. The factor-finding replay checks the probability bound for 15, 21 and 35. |

Pages 36 and 37 print the action on ψⱼ with ψ₁ on the right. The eigenvalue multiplies ψⱼ, as page 34 states. For multiplication by two modulo 15, the squared residual of the page 34 equation is zero for every j. For the equation printed on pages 36 and 37 it is two for j = 0, 2 and 3 and zero for j = 1.

```text
python replay-ibm026-slides.py WORKER slides.pdf
```

The linked video reports a duration of 1 hour, 15 minutes and 14 seconds. Its public player listed an English caption track, but the request for that track returned no caption text. Verification of the spoken lecture remains open. [Lecture video](https://www.youtube.com/watch?v=4nT0BTUxhJY)
