// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalInteger.h"
#include <stdexcept>
namespace QuantumClassical {
namespace {
std::uint64_t mask(unsigned width) {
 if(!width || width>64)throw std::out_of_range("Integer width must be 1..64");
 return width==64 ? ~std::uint64_t(0) : (std::uint64_t(1)<<width)-1;
}
}
Integer Integer::fromBits(Signedness sign,unsigned width,std::uint64_t bits) {
 if(sign!=Signedness::Signed && sign!=Signedness::Unsigned)throw std::invalid_argument("Unknown integer signedness");
 if(bits&~mask(width))throw std::out_of_range("Integer bit pattern exceeds its width");
 return Integer(sign,width,bits);
}
bool Integer::negative() const {return sign_==Signedness::Signed && (bits_&(std::uint64_t(1)<<(width_-1)));}
std::int64_t Integer::signedValue() const {
 // The complement fits INT64_MAX even for the signed minimum. Avoid an
 // implementation-defined unsigned-to-signed conversion and negating INT64_MIN.
 return negative() ? -1-static_cast<std::int64_t>((~bits_)&mask(width_)) : static_cast<std::int64_t>(bits_);
}
std::uint64_t Integer::magnitude() const {return negative() ? (~bits_+1)&mask(width_) : bits_;}
Integer Integer::cast(Signedness sign,unsigned width) const {
 auto value=bits_;
 if(width>width_ && negative())value|=~mask(width_);
 return fromBits(sign,width,value&mask(width));
}
void Integer::sameType(const Integer &right) const {
 if(sign_!=right.sign_ || width_!=right.width_)throw std::invalid_argument("Promote integer operands to the same type before evaluation");
}
Integer Integer::signedMagnitude(bool neg,std::uint64_t value) const {
 const auto limit=std::uint64_t(1)<<(width_-1);
 if(value>(neg ? limit : limit-1))throw std::overflow_error("Signed integer arithmetic overflow");
 return fromBits(sign_,width_,(neg ? ~value+1 : value)&mask(width_));
}
Integer Integer::binary(Operation operation,const Integer &right) const {
 sameType(right);
 if(operation==Operation::Power) {
  if(right.negative())throw std::domain_error("Integer power requires a nonnegative exponent");
  return power(right.bits_);
 }
 if(operation==Operation::Divide || operation==Operation::Remainder) {
  if(!right.bits_)throw std::domain_error("Integer division by zero");
 }
 if(sign_==Signedness::Unsigned) {
  std::uint64_t value;
  switch(operation) {
   case Operation::Add:value=bits_+right.bits_;break;
   case Operation::Subtract:value=bits_-right.bits_;break;
   case Operation::Multiply:value=bits_*right.bits_;break;
   case Operation::Divide:value=bits_/right.bits_;break;
   case Operation::Remainder:value=bits_%right.bits_;break;
   default:throw std::invalid_argument("Unknown integer operation");
  }
  return fromBits(sign_,width_,value&mask(width_));
 }
 const auto a=signedValue(),b=right.signedValue();
 const auto maximum=static_cast<std::int64_t>(mask(width_)>>1),minimum=-maximum-1;
 if(operation==Operation::Add) {
  if((b>0 && a>maximum-b) || (b<0 && a<minimum-b))throw std::overflow_error("Signed integer arithmetic overflow");
  return fromBits(sign_,width_,static_cast<std::uint64_t>(a+b)&mask(width_));
 }
 if(operation==Operation::Subtract) {
  if((b>0 && a<minimum+b) || (b<0 && a>maximum+b))throw std::overflow_error("Signed integer arithmetic overflow");
  return fromBits(sign_,width_,static_cast<std::uint64_t>(a-b)&mask(width_));
 }
 const auto am=magnitude(),bm=right.magnitude();const bool neg=negative()!=right.negative();
 if(operation==Operation::Multiply) {
  const auto limit=(std::uint64_t(1)<<(width_-1))-(neg ? 0 : 1);
  if(bm && am>limit/bm)throw std::overflow_error("Signed integer arithmetic overflow");
  return signedMagnitude(neg,am*bm);
 }
 if(operation==Operation::Divide || operation==Operation::Remainder) {
  if(a==minimum && b==-1)throw std::overflow_error("Signed integer quotient overflow");
  return operation==Operation::Divide ? signedMagnitude(neg,am/bm) : signedMagnitude(negative(),am%bm);
 }
 throw std::invalid_argument("Unknown integer operation");
}
Integer Integer::power(std::uint64_t exponent) const {
 // Delay creating the multiplicative identity: signed one-bit values cannot
 // represent +1, but (-1)^odd is still a valid result.
 if(!exponent)return sign_==Signedness::Signed ? signedMagnitude(false,1) : fromBits(sign_,width_,1);
 if(negative() && bits_==mask(width_))return exponent&1 ? *this : signedMagnitude(false,1);
 Integer result=*this,base=*this;--exponent;
 while(exponent) {
  if(exponent&1)result=result.binary(Operation::Multiply,base);
  exponent>>=1;
  if(exponent)base=base.binary(Operation::Multiply,base);
 }
 return result;
}
int Integer::compare(const Integer &right) const {
 sameType(right);
 if(negative()!=right.negative())return negative() ? -1 : 1;
 return bits_<right.bits_ ? -1 : bits_>right.bits_ ? 1 : 0;
}
}
