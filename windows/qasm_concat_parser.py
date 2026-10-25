"""Compatibility parsing for the specification's concatenated call arguments.

The reference grammar only admits ++ in aliases, although its subroutine
example uses parity(c ++ c2). Keep tokens and source locations intact and give
this extension lower precedence than the ordinary expression operators.
"""
from antlr4 import CommonTokenStream, InputStream
from antlr4.error.ErrorListener import ErrorListener
from antlr4.error.ErrorStrategy import BailErrorStrategy
from openqasm3 import ast
from openqasm3.parser import QASMNodeVisitor, QASM3ParsingError, add_span, get_span
from openqasm3._antlr.qasm3Lexer import qasm3Lexer
from openqasm3._antlr.qasm3Parser import qasm3Parser


class _Errors(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, exc):
        raise QASM3ParsingError(f'L{line}:C{column}: {msg}')


class _Visitor(QASMNodeVisitor):
    def visitLogicalOrExpression(self, ctx):
        # Flatten only unparenthesized OR chains. Parenthesis contexts stay
        # opaque, so the caller's explicit grouping always takes precedence.
        operands = []; operators = []
        def collect(node):
            if isinstance(node, qasm3Parser.LogicalOrExpressionContext):
                collect(node.expression(0)); operators.append(node.op.text)
                collect(node.expression(1))
            else:
                operands.append(node)
        collect(ctx)
        if '++' not in operators:
            return super().visitLogicalOrExpression(ctx)
        operands = [self.visit(node) for node in operands]
        groups = []; current = operands[0]
        for operator, operand in zip(operators, operands[1:]):
            if operator == '++':
                groups.append(current); current = operand
            else:
                current = ast.BinaryExpression(op=ast.BinaryOperator['||'], lhs=current, rhs=operand)
        groups.append(current); result = groups[0]
        for operand in groups[1:]:
            result = ast.Concatenation(lhs=result, rhs=operand)
        return add_span(result, get_span(ctx))


def concatenation_program(source):
    """Return a reference AST when ++ tokens occur, otherwise use normal loading."""
    if '++' not in source:
        return None
    lexer = qasm3Lexer(InputStream(source)); lexer.removeErrorListeners()
    lexer.addErrorListener(_Errors())
    stream = CommonTokenStream(lexer); stream.fill()
    operators = [token for token in stream.tokens if token.type == qasm3Lexer.DOUBLE_PLUS]
    if not operators:
        return None
    for token in operators:
        token.type = qasm3Lexer.DOUBLE_PIPE
    stream.seek(0)
    parser = qasm3Parser(stream); parser.removeErrorListeners()
    parser.addErrorListener(_Errors()); parser._errHandler = BailErrorStrategy()
    return _Visitor().visitProgram(parser.program())
