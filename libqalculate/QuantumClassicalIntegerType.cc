// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalIntegerType.h"
namespace QuantumClassical {
IntegerType IntegerType::sized(Integer::Signedness sign,unsigned width) {
 Integer::fromBits(sign,width,0);return IntegerType(sign,width,true);
}
IntegerType IntegerType::machine(Integer::Signedness sign) {
 Integer::fromBits(sign,64,0);return IntegerType(sign,64,false);
}
IntegerType IntegerType::promoted() const {
 // A signed machine integer represents every supported narrower type. Only
 // unsigned 64-bit values need the unsigned machine type after promotion.
 return machine(sign_==Integer::Signedness::Unsigned && width_==64 ? Integer::Signedness::Unsigned : Integer::Signedness::Signed);
}
IntegerType IntegerType::common(const IntegerType &left,const IntegerType &right) {
 auto l=left.promoted(),r=right.promoted();
 return machine(l.sign_==Integer::Signedness::Unsigned || r.sign_==Integer::Signedness::Unsigned ? Integer::Signedness::Unsigned : Integer::Signedness::Signed);
}
TypedInteger TypedInteger::fromBits(IntegerType type,std::uint64_t bits) {
 return TypedInteger(type,Integer::fromBits(type.signedness(),type.width(),bits));
}
TypedInteger TypedInteger::cast(IntegerType target) const {
 return TypedInteger(target,value_.cast(target.signedness(),target.width()));
}
TypedInteger TypedInteger::binary(Integer::Operation operation,const TypedInteger &right) const {
 auto resultType=IntegerType::common(type_,right.type_);
 auto leftValue=cast(resultType),rightValue=right.cast(resultType);
 return TypedInteger(resultType,leftValue.value_.binary(operation,rightValue.value_));
}
int TypedInteger::compare(const TypedInteger &right) const {
 auto resultType=IntegerType::common(type_,right.type_);
 return cast(resultType).value_.compare(right.cast(resultType).value_);
}
}
