// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_INTEGER_TYPE_H
#define QUANTUM_CLASSICAL_INTEGER_TYPE_H
#include "QuantumClassicalInteger.h"
namespace QuantumClassical {
// Target policy: unspecified integers have 64-bit precision. Explicit-width
// integers are extended types ranked below the machine type of equal width.
class IntegerType {
 Integer::Signedness sign_;unsigned width_;bool explicit_;
 IntegerType(Integer::Signedness sign,unsigned width,bool sized):sign_(sign),width_(width),explicit_(sized) {}
public:
 static IntegerType sized(Integer::Signedness sign,unsigned width);
 static IntegerType machine(Integer::Signedness sign);
 Integer::Signedness signedness() const {return sign_;}
 unsigned width() const {return width_;}
 bool explicitWidth() const {return explicit_;}
 bool operator==(const IntegerType &right) const {return sign_==right.sign_ && width_==right.width_ && explicit_==right.explicit_;}
 bool operator!=(const IntegerType &right) const {return !(*this==right);}
 IntegerType promoted() const;
 static IntegerType common(const IntegerType &left,const IntegerType &right);
};
// Keep the type identity attached to the value across casts and operations.
class TypedInteger {
 IntegerType type_;Integer value_;
 TypedInteger(IntegerType type,Integer value):type_(type),value_(value) {}
public:
 static TypedInteger fromBits(IntegerType type,std::uint64_t bits);
 const IntegerType &type() const {return type_;}
 const Integer &value() const {return value_;}
 TypedInteger cast(IntegerType target) const;
 TypedInteger binary(Integer::Operation operation,const TypedInteger &right) const;
 int compare(const TypedInteger &right) const;
};
}
#endif
