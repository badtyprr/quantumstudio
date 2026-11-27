# IBM-030 Grover search lecture

The 30-page slide deck has SHA-256 `02be18ffcd56ac5b9d4bd43a69180ac1330f285fc8dfc30ed5559142d04091c1`. The public player reports a duration of 54 minutes 56 seconds. All 154 segments of the English (US) generated caption track were available, containing 1,344 distinct cues from 1.480 to 3291.319 seconds. These captions identify the spoken discussion. The slides supply the mathematical notation. [Slides](https://ibm.box.com/public/static/03clwlnuz7ygbrctbrm7xofngf5f0urs.pdf) · [Lecture](https://video.ibm.com/embed/recorded/134056243)

| Pages | Topic | Verification |
| --- | --- | --- |
| 1–7 | Search, queries and the phase oracle | For the page 4 exercise, conjugating the controlled phase oracle by Hadamards on its control reproduces the XOR query. The replay compares all eight basis outputs for each of the 16 Boolean functions on two input bits. |
| 8–16 | Grover iteration and the two reflections | The oracle flips marked amplitudes. Diffusion reflects about the uniform state. The [reflection checks](replay-ibm033-reflections.py) exercise the operators on individual states. |
| 17–19 | Rotation in the plane of the marked and unmarked states | The [rotation replay](replay-ibm033-rotations.py) compares the iterated operator with the angle formula on every nonempty proper subset of four words. |
| 20–28 | Choosing the iteration count when the number of solutions is known | The slide replay checks all 11 plotted iterates on pages 24 and 26. It also compares the 12 printed unique-search probabilities on page 25 with an independent rational recurrence, at each displayed precision. |
| 29 | Choosing the iteration count when the number of solutions is unknown | The printed range and the spoken discussion around 46–48 minutes give a lower endpoint of one. The claimed 40% lower bound has the counterexample below. |
| 30 | Query complexity and applications | The closing discussion distinguishes unstructured oracle access from applications that must implement their own oracle. The finite replays cover the worked examples. |

## Counterexample to the randomized iteration claim

Take four words with 01, 10 and 11 marked. The printed upper endpoint is floor(π√4/4) = 1, so the only possible iteration count is one. After the oracle, the amplitudes in binary order are (1, −1, −1, −1)/2. Reflecting about their mean of −1/4 gives (−1, 0, 0, 0). Measurement therefore returns 00 with certainty, giving success probability zero. Independently, θ = arcsin(√3/2) = π/3 gives sin²(3θ) = 0. Repeating this particular schedule still gives zero success.

Run the [slide replay](replay-ibm030-slides.py) with the pinned PDF and a candidate worker executable as its two arguments. It checks the range endpoint, the probability and the resulting state separately. The [published Windows results](ibm030-published.json) include the exercise replay and saved-session checks.
