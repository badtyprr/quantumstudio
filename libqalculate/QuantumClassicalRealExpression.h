// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_REAL_EXPRESSION_H
#define QUANTUM_CLASSICAL_REAL_EXPRESSION_H
#include "QuantumClassicalIntegerExpression.h"
namespace QuantumClassical {
// Finite binary64 arithmetic for runtime gate parameters. This is not the
// modular OpenQASM angle type or the calculator's symbolic real arithmetic.
// Integer leaves retain their own typing, overflow and initialization checks.
class RealExpression {
 struct Node;
 std::shared_ptr<const Node> node_;
 explicit RealExpression(std::shared_ptr<const Node> node):node_(node) {}
public:
 enum class Operation { Add, Subtract, Multiply, Divide };
 static RealExpression constant(double value);
 static RealExpression fromInteger(const IntegerExpression &value);
 static RealExpression binary(Operation operation,const RealExpression &left,const RealExpression &right);
 // Bounds include embedded integer expressions: 32 levels, 512 expanded nodes.
 // Validation checks declarations without reading undefined runtime variables.
 void validate(unsigned registerBits,const IntegerStorage &storage) const;
 double evaluate(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const;
};
}
#endif
