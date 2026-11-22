# IBM-026 phase-estimation lecture slides

The lesson introduction links to John Watrous's 41-page slide deck. The public PDF has SHA-256 `a79cc94cc28ebf9efd214364ffb616796fab520abe7a22a9f920659b40ff95ab`. Each page was rendered for inspection. The accompanying replay performs 241 exact calculations using the calculator worker. [Original slides](https://ibm.box.com/public/static/jxase3mly99ui1n1fg8pvp6bzymbdgrh.pdf) · [Runnable examples](replay-ibm026-slides.py)

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

## Spoken lecture

The public IBM player supplied the complete generated English caption track for the 75-minute, 14-second lecture. Its playlist contained 210 segments and 1,860 distinct cues. The first cue begins at 0.24 seconds and the last ends at 4,509.88 seconds. The longest gap between adjacent cues was 1.78 seconds. The player delivered 178 zero-duration cues, which were retained during the review. The SHA-256 of the concatenated lowercase hexadecimal segment digests in playlist order is `83f3ff8860c687aec86264c2c36a4c517dc88f4d531c035abae40a67284dc8e9`. [IBM lecture player](https://video.ibm.com/embed/recorded/134056217)

| Elapsed time | Spoken material and checks |
|---|---|
| 00:00–12:00 | Spectral theorem, eigenvalue promise and the circular meaning of phase. The target is specified by a circuit and the approximation is measured modulo one. |
| 12:00–23:00 | One control qubit produces cosine-squared and sine-squared probabilities. Repeating the controlled operation doubles the phase. The replay checks both outcomes. |
| 23:00–40:00 | Two control qubits motivate orthogonal Fourier columns, the inverse transform and the recursive QFT circuit. The replay applies the inverse transform to each of the four promised phase states and checks the resulting basis vector. |
| 40:00–49:00 | General controlled powers, nearest estimates and confidence through repeated measurement. The lecturer identifies the mode of the outcomes and explains why the eigenvector can be reused. [Procedure and probability-curve audit](../IBM-028.md) |
| 49:00–62:00 | Modular units, orders, orbit eigenvectors and precision for reciprocal reconstruction. The examples modulo 21 and modulo 15 are covered by the slide replay. |
| 62:00–66:00 | Random eigenvectors produce fractions in lowest terms. With order six and eleven control bits, the replay recovers 1/6, 1/3, 1/2, 2/3 and 5/6 from rounded measurement outcomes. The denominators three and two together recover order six. |
| 66:00–75:14 | The circuit uses modular repeated squaring, prepares the basis state one, and extracts factors by a GCD. The replay checks 60 basis actions for four controlled powers and the finite factor-finding examples on slide 41. |

This review follows the generated captions and rendered slides. The captions contain transcription errors in mathematical names and symbols, so the equations in the replay follow the slides and are checked numerically. Published-package verification remains open.
