// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalRangeExpression.h"
namespace QuantumClassical {
RangeExpression::RangeExpression(const IntegerExpression &start,const IntegerExpression &stop,const IntegerExpression &step):
 start_(start),stop_(stop),step_(step),type_(IntegerType::common(start.type(),stop.type())) {}
void RangeExpression::validate(unsigned registerBits,const IntegerStorage &storage) const {
 start_.validate(registerBits,storage);stop_.validate(registerBits,storage);step_.validate(registerBits,storage);
}
IntegerRange RangeExpression::evaluate(std::uint64_t record,unsigned registerBits,const IntegerStorage &storage) const {
 const auto start=start_.evaluate(record,registerBits,storage).cast(type_);
 const auto stop=stop_.evaluate(record,registerBits,storage).cast(type_);
 const auto step=step_.evaluate(record,registerBits,storage);
 return IntegerRange(start.value(),stop.value(),step.value());
}
}
