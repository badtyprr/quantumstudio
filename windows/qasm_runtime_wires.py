"""Preserve scalar quantum indices while the pinned compiler lowers gates.

Only the private compilation proxy uses fixed wires. Every emitted operation
retains its real ordered candidates and runtime index for the circuit model.
"""
import copy
from dataclasses import dataclass
import openqasm3.ast as ast
from qasm_source_diagnostics import error_at


@dataclass
class WireReferenceCheck(ast.Statement):
    targets: list
    widths: object = None


@dataclass
class QuantumSelectorTypeCheck(ast.Statement):
    index: object


@dataclass
class SourceQuantumSelection(ast.Expression):
    register: object
    index: object


@dataclass
class SourceQuantumRegisterView(ast.Expression):
    register: object
    view: object
    selections: list


class RuntimeWires:
    def __init__(self, runtime, normalize):
        self.runtime = runtime
        self.normalize = normalize

    @staticmethod
    def parts(value):
        if isinstance(value, ast.IndexedIdentifier):
            return value.name, value.indices[0] if len(value.indices) == 1 else None
        if isinstance(value, ast.IndexExpression) and isinstance(value.collection, ast.Identifier):
            return value.collection, value.index
        return None, None

    def dynamic(self, visitor, operand):
        if isinstance(operand,(SourceQuantumSelection,SourceQuantumRegisterView)):return True
        _, indices = self.parts(operand)
        return indices is not None and self.runtime(visitor, indices)

    @staticmethod
    def key(value):
        return value.name.name, value.indices[0][0].value

    @staticmethod
    def fixed(visitor, operand):
        if isinstance(operand,ast.IndexExpression) and isinstance(operand.collection,ast.Identifier):operand=ast.IndexedIdentifier(name=operand.collection,indices=[operand.index])
        proxy = ast.QuantumGate(modifiers=[], name=ast.Identifier('id'), arguments=[], qubits=[operand])
        return visitor._get_op_bits(proxy, qubits=True)

    @staticmethod
    def require_integer_index(visitor,value):
        if (isinstance(value,ast.BooleanLiteral) or
            isinstance(value,ast.Identifier) and value.name in getattr(visitor,'_quantum_boolean_names',set()) or
            isinstance(value,ast.Cast) and isinstance(value.type,ast.BoolType) or
            isinstance(value,ast.UnaryExpression) and value.op.name=='!' or
            isinstance(value,ast.BinaryExpression) and value.op.name in ('==','!=','<','<=','>','>=','&&','||')):
            raise error_at(value,'Quantum indices require integers; cast Boolean values explicitly.')

    def group(self, visitor, operand, force=False):
        if isinstance(operand,SourceQuantumRegisterView):
            return [target for selected in operand.selections for target in self.group(visitor,selected)]
        if isinstance(operand,SourceQuantumSelection):
            return [{'Candidates':self.fixed(visitor,operand.register),'Index':self.normalize(visitor,operand.index,typed=True)}]
        if self.dynamic(visitor, operand) or force and self.parts(operand)[1] is not None:
            name, indices = self.parts(operand)
            if not isinstance(indices, list) or len(indices) != 1 or isinstance(indices[0], (ast.RangeDefinition, ast.DiscreteSet)):
                raise error_at(operand, 'Runtime quantum indices require one scalar integer; runtime slices/sets are unsupported.')
            value=indices[0]
            self.require_integer_index(visitor,value)
            index = self.normalize(visitor, value, typed=True)
            return [{'Candidates': self.fixed(visitor, name), 'Index': index}]
        return [{'Candidates': [wire], 'Index': ast.IntegerLiteral(0)} for wire in self.fixed(visitor, operand)]

    def compile(self, visitor, operation, callback, operands, replace):
        if not any(self.dynamic(visitor, operand) for operand in operands):
            return callback(operation)
        if getattr(operation, 'duration', None) is not None:
            raise error_at(operation, 'Timed gates are not supported.')
        if not 1 <= len(operands) <= 3:
            raise error_at(operation, 'Runtime quantum operations support one to three operands.')
        groups = [self.group(visitor, operand) for operand in operands]
        lanes = max(len(group) for group in groups)
        if any(len(group) not in (1, lanes) for group in groups):
            raise error_at(operation, 'Broadcast register sizes must agree.')
        measurement_targets=None
        if isinstance(operation,ast.QuantumMeasurementStatement) and operation.target is not None:
            measurement_targets=visitor._get_op_bits(operation,qubits=False)
            if len(measurement_targets)!=lanes:raise error_at(operation,'Measurement source and destination widths must agree.')
        proxies = []
        for name, size in visitor._global_qreg_size_map.items():
            for index in range(size):
                proxies.append(ast.IndexedIdentifier(name=ast.Identifier(name), indices=[[ast.IntegerLiteral(index)]]))
        if len(proxies) < len(operands):
            raise error_at(operation, 'Quantum operation requires more distinct wires than the circuit contains.')
        proxies = proxies[:len(operands)]
        guards, result = [], []
        for lane in range(lanes):
            targets = [group[0 if len(group) == 1 else lane] for group in groups]
            context = {self.key(proxy): target for proxy, target in zip(proxies, targets)}
            guard = ast.QuantumGate(modifiers=[], name=ast.Identifier('id'), arguments=[], qubits=copy.deepcopy(proxies))
            guard.span = operation.span
            guard._quantum_wire_preflight = True
            guard._quantum_wire_targets = copy.deepcopy(context)
            guards.append(guard)
            proxy = copy.deepcopy(operation)
            replace(proxy, copy.deepcopy(proxies))
            if measurement_targets is not None:proxy.target=copy.deepcopy(measurement_targets[lane])
            for item in callback(proxy):
                if not isinstance(item, (ast.QuantumGate, ast.QuantumPhase, ast.QuantumReset, ast.QuantumMeasurementStatement)):
                    raise error_at(operation, 'Runtime wire lowering produced an unsupported operation.')
                item.span = operation.span
                item._quantum_wire_targets = copy.deepcopy(context)
                result.append(item)
        # All lanes are checked before the first physical gate/reset/measurement.
        return guards + result

    def gate(self, visitor, operation, callback):
        return self.compile(visitor, operation, callback, operation.qubits or [], lambda op, wires: setattr(op, 'qubits', wires))

    def measurement(self, visitor, operation, callback):
        return self.compile(visitor, operation, callback, [operation.measure.qubit], lambda op, wires: setattr(op.measure, 'qubit', wires[0]))

    def reset(self, visitor, operation, callback):
        return self.compile(visitor, operation, callback, [operation.qubits], lambda op, wires: setattr(op, 'qubits', wires[0]))
