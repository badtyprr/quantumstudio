// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_INTEGER_EXPRESSION_H
#define QUANTUM_CLASSICAL_INTEGER_EXPRESSION_H
#include "QuantumClassicalIntegerType.h"
#include <memory>
#include <vector>
#include <cstddef>
namespace QuantumClassical {
class RuntimeStorage;
using IntegerStorage=RuntimeStorage;
class Bits;
class RealExpression;
class ArraySelection;
class ArrayView;
// Immutable expressions over a packed record and optional typed variable slots.
// Register declarations/initialization and protocol decoding belong to callers.
class IntegerExpression {
 friend class Bits;
 friend class RealExpression;
 friend class ArraySelection;
 friend class ArrayView;
 unsigned depth() const;
 unsigned count() const;
 std::uint64_t references() const;
 void validateContext(unsigned registerBits,const IntegerStorage *storage) const;
 struct Node;
 std::shared_ptr<const Node> node_;
 explicit IntegerExpression(std::shared_ptr<const Node> node):node_(node) {}
public:
 static IntegerExpression constant(const TypedInteger &value);
 // indices[k] supplies bit k of the declared integer, in little-endian order.
 static IntegerExpression read(IntegerType type,const std::vector<unsigned> &indices);
 // Reinterpret a complete bit expression with matching width, preserving lazy
 // evaluation and undefined-variable errors. Boolean values use unsigned width 1.
 static IntegerExpression fromBits(IntegerType type,const Bits &operand);
 static IntegerExpression variable(IntegerType type,std::size_t index);
 static IntegerExpression viewExtent(const ArrayView &view,unsigned axis);
 static IntegerExpression arrayExtent(const ArraySelection &selection);
 static IntegerExpression arrayElement(IntegerType type,const ArraySelection &selection);
 static IntegerExpression cast(IntegerType type,const IntegerExpression &operand);
 static IntegerExpression binary(Integer::Operation operation,const IntegerExpression &left,const IntegerExpression &right);
 static IntegerExpression fromNumeric(IntegerType type,const RealExpression &value);
 static IntegerExpression angleRatio(const RealExpression &left,const RealExpression &right);
 static IntegerExpression angleBits(const RealExpression &value);
 // Internal ordered comparison result (-1,0,1); Boolean conditions compare it
 // with zero through the existing short-circuit bit-expression machinery.
 static IntegerExpression numericCompare(const RealExpression &left,const RealExpression &right);
 const IntegerType &type() const;
 // Bounds are 32 levels and 512 expanded nodes, including shared subtrees.
 // Validation checks references only: it never evaluates a fabricated record.
 void validate(unsigned registerBits) const;
 void validate(unsigned registerBits,const IntegerStorage &storage) const;
 TypedInteger evaluate(std::uint64_t record,unsigned registerBits) const;
 TypedInteger evaluate(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const;
};
}
#endif
