"""Prepare lexical subroutine scopes for the pinned compile-time evaluator."""
from dataclasses import fields, is_dataclass
import openqasm3.ast as ast
from qasm_source_diagnostics import error_at


def prepare_subroutine_scope(program):
    mutable = {node.identifier.name for node in program.statements
               if isinstance(node, ast.ClassicalDeclaration)}

    def expression(value, bound):
        if isinstance(value, ast.Identifier):
            if value.name in mutable and value.name not in bound:
                raise error_at(value, "Subroutines cannot capture mutable global variables: " + value.name)
        elif isinstance(value, (list, tuple)):
            for child in value:
                expression(child, bound)
        elif is_dataclass(value):
            for field in fields(value):
                if field.name in ("span", "annotations"):
                    continue
                if field.name == "name" and isinstance(value, (ast.FunctionCall, ast.QuantumGate)):
                    continue
                expression(getattr(value, field.name), bound)

    def block(body, parent):
        bound = set(parent)
        for node in body:
            if isinstance(node, (ast.ClassicalDeclaration, ast.ConstantDeclaration)):
                expression(node.type, bound)
                bound.add(node.identifier.name)
                expression(node.init_expression, bound)
            elif isinstance(node, ast.AliasStatement):
                expression(node.value, bound)
                bound.add(node.target.name)
            elif isinstance(node, ast.ForInLoop):
                expression(node.type, bound)
                expression(node.set_declaration, bound)
                block(node.block, bound | {node.identifier.name})
            elif isinstance(node, ast.WhileLoop):
                expression(node.while_condition, bound)
                block(node.block, bound)
            elif isinstance(node, ast.BranchingStatement):
                expression(node.condition, bound)
                block(node.if_block, bound)
                block(node.else_block, bound)
            elif isinstance(node, ast.CompoundStatement):
                block(node.statements, bound)
            elif isinstance(node, ast.SwitchStatement):
                expression(node.target, bound)
                for labels, case in node.cases:
                    expression(labels, bound)
                    block(case.statements, bound)
                if node.default is not None:
                    block(node.default.statements, bound)
            else:
                expression(node, bound)

    for node in program.statements:
        if isinstance(node, ast.SubroutineDefinition):
            block(node.body, {argument.name.name for argument in node.arguments})
            # PyQASM defaults integer declarations to 32 bits, but leaves an
            # omitted formal-argument width as None. Its assignment validator
            # then rejects even n += 1. Make that same compiler default explicit
            # for scalar integer arguments; preserve all specified widths.
            for argument in node.arguments:
                if (isinstance(argument, ast.ClassicalArgument)
                        and isinstance(argument.type, (ast.IntType, ast.UintType))
                        and argument.type.size is None):
                    argument.type.size = ast.IntegerLiteral(32)
