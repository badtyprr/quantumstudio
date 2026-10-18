# Classical expression text

The circuit-editing parser accepts declared register names, individual bits such
as `c[0]`, inclusive ascending slices such as `c[1:2]`, and `read(2,0,2)` for
global bit indices in any order. The first selected bit is least significant.
`read(...)` also provides access to registers whose names contain characters
outside the expression identifier syntax.

Decimal integers take their width from the assignment or other operand. Quoted
bit strings such as `"001"` declare an explicit width. `true` and `false` are
one-bit constants. All values are unsigned and must fit in 1–64 bits.

Operators from lowest to highest precedence are `||`, `&&`, `|`, `^`, `&`,
equality (`==`, `!=`), ordering (`<`, `<=`, `>`, `>=`), shifts (`<<`, `>>`), and
unary negation (`~`, `!`). Parentheses override precedence. Logical operators
require one-bit operands; bitwise operators retain their width. Comparisons
produce one bit. Shift counts have their own width.

Examples include `c[0] ^ c[1]`, `c == 1 || c == 2`, `~c`, and `c << 1`.
Formatting uses explicit bit strings, `read(...)`, and parentheses so saved
expressions retain their widths and meaning when edited again. Limits are 512
nodes and 32 expression levels. The parser validates its output using the same
circuit model as imported files.

In the classical circuit editor, choose **Assign bits**, enter target bit indices
in least-significant-first order, and type an expression. Choose **If expression**
for a one-bit condition, then add operations to its Then and Else bodies.
Replacing either kind of condition preserves both bodies. Invalid expressions
leave the circuit and undo history unchanged. Saving uses the expression-aware
circuit format automatically.
These register names are not added to the general calculator namespace.

`popcount(value)` counts set bits and returns a 64-bit unsigned value; it can be
compared directly, for example `popcount(c) == 2`. `rotl(value, distance)` and
`rotr(value, distance)` preserve the value width and wrap the distance modulo
that width. Negative decimal distances reverse direction, including -2^63.
Positive distances and register expressions are unsigned by default.
`rotl_signed` and `rotr_signed` explicitly interpret distance bits as two's
complement. Their decimal arguments default to 64 bits; quoted bit strings and
registers retain their declared width. Formatting uses these explicit forms to
preserve imported signed distances through editing. These names belong to the
classical circuit editor, not the main mathematical calculator.

Signed integer constants display as signed decimal values, for example
`int(-1)` and `int[8](-128)`. Formatting and reparsing preserve the declared
width, signedness and stored bits, including the minimum signed 64-bit value.
Unsigned constants keep their nonnegative decimal representation.
