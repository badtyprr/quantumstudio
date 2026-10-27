// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_REAL_EXPRESSION_H
#define QUANTUM_CLASSICAL_REAL_EXPRESSION_H
#include "QuantumClassicalIntegerExpression.h"
#include "QuantumClassicalNumeric.h"
namespace QuantumClassical {
// Immutable finite float32/64 and modular angle expressions. Integer leaves
// retain their own typing, overflow and initialization checks.
class RealExpression {
 friend class IntegerExpression;
 friend class Bits;
 unsigned depth() const;
 unsigned count() const;
 std::uint64_t references() const;
 struct Node;
 std::shared_ptr<const Node> node_;
 explicit RealExpression(std::shared_ptr<const Node> node):node_(node) {}
public:
 using Operation=NumericValue::Operation;
 static RealExpression constant(double value);
 static RealExpression constant(const NumericValue &value);
 static RealExpression fromInteger(const IntegerExpression &value,unsigned floatWidth=64);
 static RealExpression variable(NumericType type,std::size_t slot);
 static RealExpression cast(NumericType type,const RealExpression &value);
 static RealExpression fromBits(unsigned angleWidth,const Bits &value);
 static RealExpression function(NumericValue::Function function,const RealExpression &value);
 static RealExpression scale(NumericValue::Scaling operation,const RealExpression &angle,const IntegerExpression &value);
 static RealExpression binary(Operation operation,const RealExpression &left,const RealExpression &right);
 NumericType type() const;
 // Bounds include embedded integer expressions: 32 levels, 512 expanded nodes.
 // Validation checks declarations without reading undefined runtime variables.
 void validate(unsigned registerBits,const IntegerStorage &storage) const;
 double evaluate(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const;
 NumericValue evaluateTyped(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const;
};
}
#endif
