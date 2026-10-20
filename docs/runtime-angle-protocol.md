# Runtime rotation requests

`QEXACT10` extends `QEXACT9`; `QSAMPLE11` extends `QSAMPLE10`. All earlier fields,
variable declarations, loop budgets, operation codes and limits remain unchanged.
Earlier versions reject the new operation. The associated version-11 circuit
model preserves rotation axes and real expression trees through save/load.
The importer supports unmodified `rx`, `ry`, and `rz` outside subroutines; export
uses explicit `float[64]` conversion where integer values become real operands.
See DEV-06 in `learning-coverage-checklist.md` for integration/release status and
the remaining editor, gate and type coverage. This protocol alone does not
establish that those user-facing paths have shipped.

Operation `16` is a runtime rotation. Its fields are the target quantum wire,
axis (`0` = Rx, `1` = Ry, `2` = Rz), and one real-expression tree. All scalar
fields use the existing unsigned-decimal integer followed by LF encoding.

Real-expression node codes:

| Code | Following fields | Meaning |
|---|---|---|
| 0 | One uint64 | IEEE-754 binary64 bit pattern of a finite constant |
| 1 | One existing typed integer-expression tree | Convert the evaluated integer to binary64 |
| 2 | Operation, left real tree, right real tree | Arithmetic: 0 add, 1 subtract, 2 multiply, 3 divide |

For example, positive `1.0` has constant encoding `0\n4607182418800017408\n`.
Negative constants use their binary64 sign bit, not a signed protocol integer.
Integer leaves support existing variable and bit expressions. Integer arithmetic
finishes with its existing type and overflow rules before conversion; dividing
two converted real operands instead uses binary64 division.

The decoder bounds each complete real tree, including embedded integer and bit
trees, to 32 levels and 512 expanded nodes before recursion. Declaration/wire
validation includes unreachable bodies but never reads an undefined variable.
NaN, infinities, invalid codes, unavailable references and malformed fields fail.
Division by zero, overflow to a nonfinite result and reads of undefined variables
fail when reached, without partial output.

Each execution evaluates the angle from the current measurement record and
variable storage. Sampling builds the numerical rotation matrix. Exact execution
preserves the binary64 angle as its exact rational value, then constructs and
certifies the symbolic gate. It does not snap approximate pi to mathematical pi.
Both modes interpret these angles in radians independently of calculator entry
preferences. This finite-real arithmetic is not OpenQASM's modular angle type.

Regression coverage: `src/quantum-runtime-angle-request-test.py`, included in
native tests and Windows package validation.
