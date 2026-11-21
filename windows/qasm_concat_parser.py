"""Compatibility parsing for concatenated call arguments and gate timing.

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
from qasm_source_diagnostics import error_at


class _Errors(ErrorListener):
    def syntaxError(self, recognizer, offendingSymbol, line, column, msg, exc):
        raise QASM3ParsingError(f'L{line}:C{column}: {msg}')


class _Visitor(QASMNodeVisitor):
    def visitGateCallStatement(self, ctx):
        node = super().visitGateCallStatement(ctx)
        # The pinned reference AST omits duration on QuantumPhase. Reject it
        # while the grammar still exposes the original duration designator.
        if ctx.GPHASE() and ctx.designator() is not None:
            raise error_at(node, 'Timed gates are not supported.')
        return node

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
    """Use compatibility parsing for concatenation or global-phase tokens."""
    if '++' not in source and 'gphase' not in source:
        return None
    lexer = qasm3Lexer(InputStream(source)); lexer.removeErrorListeners()
    lexer.addErrorListener(_Errors())
    stream = CommonTokenStream(lexer); stream.fill()
    operators = [token for token in stream.tokens if token.type == qasm3Lexer.DOUBLE_PLUS]
    if not operators and not any(token.type == qasm3Lexer.GPHASE for token in stream.tokens):
        return None
    for token in operators:
        token.type = qasm3Lexer.DOUBLE_PIPE
    stream.seek(0)
    parser = qasm3Parser(stream); parser.removeErrorListeners()
    parser.addErrorListener(_Errors()); parser._errHandler = BailErrorStrategy()
    return _Visitor().visitProgram(parser.program())
