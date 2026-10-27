# Runtime numeric core (DEV-06e implementation increment)

This increment supplies native typed values, expressions, per-history storage and
worker decoding. Application model/editor/import/export integration and DEV-06f
source-example evidence remain required before DEV-06 is complete.

## Finite value contract

`NumericType` supports IEEE float32/float64 and angle widths 1–64. Float constants,
operations, conversions and stores reject nonfinite values. Binary32 arithmetic
rounds at each operation; mixed floats use the wider type. Signed zero and
subnormals retain their bits. Integer conversion goes directly to the requested
precision; float-to-integer conversion truncates toward zero and checks the
destination range. Transcendentals use host math functions and round to the input
float width; cross-platform correctly rounded transcendental results are not
promised.

Functions are negate, sin, cos, tan, arcsin, arccos, arctan, exp, log, sqrt,
floor, ceiling and angle complement. Floating binary operations are +, -, *, /,
power and fmod. Division or mod by zero, non-real powers and invalid function
domains fail when evaluated. Existing lazy branches retain their behavior.

Angles store unsigned modular bits. Same-width addition, subtraction, bitwise
and/or/xor, negation and complement operate modulo 2^width. Multiplication and
division require an unsigned integer of the same width. Unsigned shift distances
at least the angle width yield zero. Angle/angle yields a same-width unsigned
integer. Narrowing truncates low bits; widening shifts left. Float-to-angle
quantization uses the source precision's 2π, exact rational division and nearest
ties-to-even rounding before modulo reduction. Bits-to-angle reinterprets equal
widths. Angle-to-float/integer casts are rejected; trig and gate consumption are
separate operations. Exact gates consume angles as rational multiples of π.

`RuntimeStorage` combines integer and numeric slots; `IntegerStorage` remains a
source-compatible alias. Numeric values are undefined until written. Stores
convert before mutation; clear returns the slot to undefined. Each measurement
history owns its storage. Exact record keys include initialization and raw numeric
bits so histories do not merge while stored values differ. Sampling resets the
frame for each shot. All consumers must be rebuilt after the frame/step layout
change; object-file ABI compatibility is not promised.

## Protocol

QEXACT12 and QSAMPLE13 extend the previous headers. After the integer declaration
list, write a numeric declaration count and `(kind,width)` pairs (kind 0 float,
1 angle), then the existing loop budget. Integer and numeric slots together are
limited to 4096. Slot indices address their own typed list. Operation 18 is numeric
store: slot then real tree. Operation 19 is numeric clear: slot.

Real-tree nodes 0–2 retain their encoding; binary operation codes now extend to
0 add, 1 subtract, 2 multiply, 3 divide, 4 power, 5 mod, 6 and, 7 or, 8 xor.

| Code | Payload |
| --- | --- |
| 3 | numeric type, unsigned raw bits |
| 4 | numeric type, slot |
| 5 | numeric destination type, real operand |
| 6 | function code, real operand |
| 7 | scale code, angle operand, integer operand |
| 8 | angle width, bit-expression operand |
| 9 | float width, integer operand (direct conversion) |

Function codes 0–12 follow the function order above. Scale codes 0–3 are multiply,
divide, left shift, right shift. Integer-tree extensions are 6 (integer target
type then real operand), 7 (two angles, ratio), 8 (angle, raw unsigned bits), and
9 (two numeric operands, signed machine comparison result -1/0/1). Numeric
comparisons can feed existing integer comparison/Boolean nodes. Construction
checks types; evaluation preserves left-to-right order and undefined-read errors.

All cross-domain edges contribute to the existing 32-depth/512-node limits.
Older headers reject these extensions. Existing headers and payloads remain
supported. Native value, integration and worker protocol regressions are in
`src/quantum-classical-numeric-test.cc`, `src/quantum-runtime-numeric-test.cc`
and `src/quantum-runtime-numeric-request-test.py`.
