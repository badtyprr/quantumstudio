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
