# DEV-11 complete finite comparison tables

These are finite adapted tests, not whole-source audits. Syndrome bit 1 means anticommutation; generator order is the source order. Logical recovery compares every physical amplitude of BOTH encoded basis columns; only one common global phase is allowed. Exact worker evaluation is compared numerically after safe parsing, tolerance 1e-12.

## Repetition: III and three X errors

| Error | Expected syndrome | Actual canonical syndrome | Recovery |
|---|---|---|---|
| III | 00 | `vector(0,0)` | already-supported-adaptation |
| XII | 10 | `vector(1,0)` | already-supported-adaptation |
| IXI | 11 | `vector(1,1)` | already-supported-adaptation |
| IIX | 01 | `vector(0,1)` | already-supported-adaptation |

## Five-qubit: all 16 weight-zero/one Paulis

| Error | Expected syndrome | Actual canonical syndrome | Recovery |
|---|---|---|---|
| IIIII | 0000 | `vector(0,0,0,0)` | already-supported-adaptation |
| XIIII | 0001 | `vector(0,0,0,1)` | already-supported-adaptation |
| IXIII | 1000 | `vector(1,0,0,0)` | already-supported-adaptation |
| IIXII | 1100 | `vector(1,1,0,0)` | already-supported-adaptation |
| IIIXI | 0110 | `vector(0,1,1,0)` | already-supported-adaptation |
| IIIIX | 0011 | `vector(0,0,1,1)` | already-supported-adaptation |
| YIIII | 1011 | `vector(1,0,1,1)` | already-supported-adaptation |
| IYIII | 1101 | `vector(1,1,0,1)` | already-supported-adaptation |
| IIYII | 1110 | `vector(1,1,1,0)` | already-supported-adaptation |
| IIIYI | 1111 | `vector(1,1,1,1)` | already-supported-adaptation |
| IIIIY | 0111 | `vector(0,1,1,1)` | already-supported-adaptation |
| ZIIII | 1010 | `vector(1,0,1,0)` | already-supported-adaptation |
| IZIII | 0101 | `vector(0,1,0,1)` | already-supported-adaptation |
| IIZII | 0010 | `vector(0,0,1,0)` | already-supported-adaptation |
| IIIZI | 1001 | `vector(1,0,0,1)` | already-supported-adaptation |
| IIIIZ | 0100 | `vector(0,1,0,0)` | already-supported-adaptation |

## Steane: all 22 weight-zero/one Paulis

| Error | Expected syndrome | Actual canonical syndrome | Recovery |
|---|---|---|---|
| IIIIIII | 000000 | `vector(0,0,0,0,0,0)` | already-supported-adaptation |
| XIIIIII | 111000 | `vector(1,1,1,0,0,0)` | already-supported-adaptation |
| IXIIIII | 110000 | `vector(1,1,0,0,0,0)` | already-supported-adaptation |
| IIXIIII | 101000 | `vector(1,0,1,0,0,0)` | already-supported-adaptation |
| IIIXIII | 100000 | `vector(1,0,0,0,0,0)` | already-supported-adaptation |
| IIIIXII | 011000 | `vector(0,1,1,0,0,0)` | already-supported-adaptation |
| IIIIIXI | 010000 | `vector(0,1,0,0,0,0)` | already-supported-adaptation |
| IIIIIIX | 001000 | `vector(0,0,1,0,0,0)` | already-supported-adaptation |
| YIIIIII | 111111 | `vector(1,1,1,1,1,1)` | already-supported-adaptation |
| IYIIIII | 110110 | `vector(1,1,0,1,1,0)` | already-supported-adaptation |
| IIYIIII | 101101 | `vector(1,0,1,1,0,1)` | already-supported-adaptation |
| IIIYIII | 100100 | `vector(1,0,0,1,0,0)` | already-supported-adaptation |
| IIIIYII | 011011 | `vector(0,1,1,0,1,1)` | already-supported-adaptation |
| IIIIIYI | 010010 | `vector(0,1,0,0,1,0)` | already-supported-adaptation |
| IIIIIIY | 001001 | `vector(0,0,1,0,0,1)` | already-supported-adaptation |
| ZIIIIII | 000111 | `vector(0,0,0,1,1,1)` | already-supported-adaptation |
| IZIIIII | 000110 | `vector(0,0,0,1,1,0)` | already-supported-adaptation |
| IIZIIII | 000101 | `vector(0,0,0,1,0,1)` | already-supported-adaptation |
| IIIZIII | 000100 | `vector(0,0,0,1,0,0)` | already-supported-adaptation |
| IIIIZII | 000011 | `vector(0,0,0,0,1,1)` | already-supported-adaptation |
| IIIIIZI | 000010 | `vector(0,0,0,0,1,0)` | already-supported-adaptation |
| IIIIIIZ | 000001 | `vector(0,0,0,0,0,1)` | already-supported-adaptation |

## Shor: all 28 weight-zero/one Paulis

| Error | Expected syndrome | Actual canonical syndrome | Recovery |
|---|---|---|---|
| IIIIIIIII | 00000000 | `vector(0,0,0,0,0,0,0,0)` | already-supported-adaptation |
| XIIIIIIII | 10000000 | `vector(1,0,0,0,0,0,0,0)` | already-supported-adaptation |
| IXIIIIIII | 11000000 | `vector(1,1,0,0,0,0,0,0)` | already-supported-adaptation |
| IIXIIIIII | 01000000 | `vector(0,1,0,0,0,0,0,0)` | already-supported-adaptation |
| IIIXIIIII | 00100000 | `vector(0,0,1,0,0,0,0,0)` | already-supported-adaptation |
| IIIIXIIII | 00110000 | `vector(0,0,1,1,0,0,0,0)` | already-supported-adaptation |
| IIIIIXIII | 00010000 | `vector(0,0,0,1,0,0,0,0)` | already-supported-adaptation |
| IIIIIIXII | 00001000 | `vector(0,0,0,0,1,0,0,0)` | already-supported-adaptation |
| IIIIIIIXI | 00001100 | `vector(0,0,0,0,1,1,0,0)` | already-supported-adaptation |
| IIIIIIIIX | 00000100 | `vector(0,0,0,0,0,1,0,0)` | already-supported-adaptation |
| YIIIIIIII | 10000010 | `vector(1,0,0,0,0,0,1,0)` | already-supported-adaptation |
| IYIIIIIII | 11000010 | `vector(1,1,0,0,0,0,1,0)` | already-supported-adaptation |
| IIYIIIIII | 01000010 | `vector(0,1,0,0,0,0,1,0)` | already-supported-adaptation |
| IIIYIIIII | 00100011 | `vector(0,0,1,0,0,0,1,1)` | already-supported-adaptation |
| IIIIYIIII | 00110011 | `vector(0,0,1,1,0,0,1,1)` | already-supported-adaptation |
| IIIIIYIII | 00010011 | `vector(0,0,0,1,0,0,1,1)` | already-supported-adaptation |
| IIIIIIYII | 00001001 | `vector(0,0,0,0,1,0,0,1)` | execution-timeout; right-associated already-supported-adaptation |
| IIIIIIIYI | 00001101 | `vector(0,0,0,0,1,1,0,1)` | execution-timeout; right-associated already-supported-adaptation |
| IIIIIIIIY | 00000101 | `vector(0,0,0,0,0,1,0,1)` | execution-timeout; right-associated already-supported-adaptation |
| ZIIIIIIII | 00000010 | `vector(0,0,0,0,0,0,1,0)` | execution-timeout; right-associated already-supported-adaptation |
| IZIIIIIII | 00000010 | `vector(0,0,0,0,0,0,1,0)` | execution-timeout; right-associated already-supported-adaptation |
| IIZIIIIII | 00000010 | `vector(0,0,0,0,0,0,1,0)` | execution-timeout; right-associated already-supported-adaptation |
| IIIZIIIII | 00000011 | `vector(0,0,0,0,0,0,1,1)` | execution-timeout; right-associated already-supported-adaptation |
| IIIIZIIII | 00000011 | `vector(0,0,0,0,0,0,1,1)` | execution-timeout; right-associated already-supported-adaptation |
| IIIIIZIII | 00000011 | `vector(0,0,0,0,0,0,1,1)` | execution-timeout; right-associated already-supported-adaptation |
| IIIIIIZII | 00000001 | `vector(0,0,0,0,0,0,0,1)` | execution-timeout; right-associated already-supported-adaptation |
| IIIIIIIZI | 00000001 | `vector(0,0,0,0,0,0,0,1)` | execution-timeout; right-associated already-supported-adaptation |
| IIIIIIIIZ | 00000001 | `vector(0,0,0,0,0,0,0,1)` | execution-timeout; right-associated already-supported-adaptation |

## Logical actions and encoders

| Fixture | Full output | Maximum residual |
|---|---|---|
| 062-css-encoder | already-supported-adaptation | 0.0 |
| 062-css-state-0 | already-supported-adaptation | 0.0 |
| 062-css-state-1 | already-supported-adaptation | 0.0 |
| 067-logical-shor-ZIIZIIZII | already-supported-adaptation | 0.0 |
| 067-logical-shor-XXXIIIIII | already-supported-adaptation | 0.0 |
| 067-logical-steane-XXXXXXX | already-supported-adaptation | 0.0 |
| 067-logical-steane-ZZZZZZZ | already-supported-adaptation | 0.0 |
| 067-steane-H | already-supported-adaptation | 5.551115123125783e-17 |
| 067-steane-Sdg | already-supported-adaptation | 5.551115123125783e-17 |
| 054-encoding | already-supported-adaptation | 0.0 |
| 054-phase-encoding | already-supported-adaptation | 0.0 |

## Complete repetition-code Pauli partition

All 64 Paulis, in source generator order ZZI, IZZ; all four classes have 16 elements. Only the four weight-zero/one X cases above are claimed correctable here.

| Pauli | Expected | Actual |
|---|---|---|
| III | 00 | `vector(0,0)` |
| IIX | 01 | `vector(0,1)` |
| IIY | 01 | `vector(0,1)` |
| IIZ | 00 | `vector(0,0)` |
| IXI | 11 | `vector(1,1)` |
| IXX | 10 | `vector(1,0)` |
| IXY | 10 | `vector(1,0)` |
| IXZ | 11 | `vector(1,1)` |
| IYI | 11 | `vector(1,1)` |
| IYX | 10 | `vector(1,0)` |
| IYY | 10 | `vector(1,0)` |
| IYZ | 11 | `vector(1,1)` |
| IZI | 00 | `vector(0,0)` |
| IZX | 01 | `vector(0,1)` |
| IZY | 01 | `vector(0,1)` |
| IZZ | 00 | `vector(0,0)` |
| XII | 10 | `vector(1,0)` |
| XIX | 11 | `vector(1,1)` |
| XIY | 11 | `vector(1,1)` |
| XIZ | 10 | `vector(1,0)` |
| XXI | 01 | `vector(0,1)` |
| XXX | 00 | `vector(0,0)` |
| XXY | 00 | `vector(0,0)` |
| XXZ | 01 | `vector(0,1)` |
| XYI | 01 | `vector(0,1)` |
| XYX | 00 | `vector(0,0)` |
| XYY | 00 | `vector(0,0)` |
| XYZ | 01 | `vector(0,1)` |
| XZI | 10 | `vector(1,0)` |
| XZX | 11 | `vector(1,1)` |
| XZY | 11 | `vector(1,1)` |
| XZZ | 10 | `vector(1,0)` |
| YII | 10 | `vector(1,0)` |
| YIX | 11 | `vector(1,1)` |
| YIY | 11 | `vector(1,1)` |
| YIZ | 10 | `vector(1,0)` |
| YXI | 01 | `vector(0,1)` |
| YXX | 00 | `vector(0,0)` |
| YXY | 00 | `vector(0,0)` |
| YXZ | 01 | `vector(0,1)` |
| YYI | 01 | `vector(0,1)` |
| YYX | 00 | `vector(0,0)` |
| YYY | 00 | `vector(0,0)` |
| YYZ | 01 | `vector(0,1)` |
| YZI | 10 | `vector(1,0)` |
| YZX | 11 | `vector(1,1)` |
| YZY | 11 | `vector(1,1)` |
| YZZ | 10 | `vector(1,0)` |
| ZII | 00 | `vector(0,0)` |
| ZIX | 01 | `vector(0,1)` |
| ZIY | 01 | `vector(0,1)` |
| ZIZ | 00 | `vector(0,0)` |
| ZXI | 11 | `vector(1,1)` |
| ZXX | 10 | `vector(1,0)` |
| ZXY | 10 | `vector(1,0)` |
| ZXZ | 11 | `vector(1,1)` |
| ZYI | 11 | `vector(1,1)` |
| ZYX | 10 | `vector(1,0)` |
| ZYY | 10 | `vector(1,0)` |
| ZYZ | 11 | `vector(1,1)` |
| ZZI | 00 | `vector(0,0)` |
| ZZX | 01 | `vector(0,1)` |
| ZZY | 01 | `vector(0,1)` |
| ZZZ | 00 | `vector(0,0)` |

Repetition logical XXX and ZII full 8-by-2 actions also pass (X and Z respectively).
