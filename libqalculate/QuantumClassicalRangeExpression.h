// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_RANGE_EXPRESSION_H
#define QUANTUM_CLASSICAL_RANGE_EXPRESSION_H
#include "QuantumClassicalRange.h"
#include "QuantumClassicalIntegerExpression.h"
namespace QuantumClassical {
// Immutable range inputs shared by execution backends. Evaluation snapshots
// bounds and step once; later writes in a loop body cannot change the sequence.
class RangeExpression {
 IntegerExpression start_,stop_,step_;
 IntegerType type_;
public:
 RangeExpression(const IntegerExpression &start,const IntegerExpression &stop,const IntegerExpression &step);
 const IntegerType &type() const {return type_;}
 void validate(unsigned registerBits,const IntegerStorage &storage) const;
 IntegerRange evaluate(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const;
};
}
#endif
