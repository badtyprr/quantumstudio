// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_INTEGER_EXPRESSION_H
#define QUANTUM_CLASSICAL_INTEGER_EXPRESSION_H
#include "QuantumClassicalIntegerType.h"
#include <memory>
#include <vector>
namespace QuantumClassical {
// Immutable runtime expressions over an already initialized packed record.
// Register declarations/initialization and protocol decoding belong to callers.
class IntegerExpression {
 struct Node;
 std::shared_ptr<const Node> node_;
 explicit IntegerExpression(std::shared_ptr<const Node> node):node_(node) {}
public:
 static IntegerExpression constant(const TypedInteger &value);
 // indices[k] supplies bit k of the declared integer, in little-endian order.
 static IntegerExpression read(IntegerType type,const std::vector<unsigned> &indices);
 static IntegerExpression cast(IntegerType type,const IntegerExpression &operand);
 static IntegerExpression binary(Integer::Operation operation,const IntegerExpression &left,const IntegerExpression &right);
 const IntegerType &type() const;
 // Bounds are 32 levels and 512 expanded nodes, including shared subtrees.
 // Validation checks references only: it never evaluates a fabricated record.
 void validate(unsigned registerBits) const;
 TypedInteger evaluate(std::uint64_t record,unsigned registerBits) const;
};
}
#endif
