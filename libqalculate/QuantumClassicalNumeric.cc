// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalNumeric.h"
#include <algorithm>
#include <cmath>
#include <cstring>
#include <gmp.h>
#include <limits>
#include <stdexcept>
namespace QuantumClassical {
namespace {
static_assert(std::numeric_limits<float>::is_iec559 && std::numeric_limits<float>::digits==24 && sizeof(float)==4,"Runtime float32 requires IEEE binary32");
static_assert(std::numeric_limits<double>::is_iec559 && std::numeric_limits<double>::digits==53 && sizeof(double)==8,"Runtime float64 requires IEEE binary64");
std::uint64_t mask(unsigned width){return width==64 ? ~std::uint64_t(0) : (std::uint64_t(1)<<width)-1;}
void finite(double value){if(!std::isfinite(value))throw std::domain_error("Runtime numeric value must be finite");}
struct Rational {mpq_t value;Rational(){mpq_init(value);}~Rational(){mpq_clear(value);}Rational(const Rational&)=delete;};
struct BigInteger {mpz_t value;BigInteger(){mpz_init(value);}~BigInteger(){mpz_clear(value);}BigInteger(const BigInteger&)=delete;};
std::uint64_t raw(const mpz_t value){std::uint64_t result=0;std::size_t count=0;mpz_export(&result,&count,-1,sizeof(result),0,0,value);return result;}
void sameAngles(NumericType a,NumericType b){if(a.kind()!=NumericType::Kind::Angle || a!=b)throw std::invalid_argument("Angle operands must have the same width");}
}
NumericType NumericType::floating(unsigned width){if(width!=32 && width!=64)throw std::invalid_argument("Runtime floats require width 32 or 64");return NumericType(Kind::Float,width);}
NumericType NumericType::angle(unsigned width){if(width<1 || width>64)throw std::invalid_argument("Runtime angles require width 1–64");return NumericType(Kind::Angle,width);}
NumericValue NumericValue::fromBits(NumericType type,std::uint64_t bits) {
 if(bits&~mask(type.width()))throw std::out_of_range("Numeric bit pattern exceeds its declared width");
 NumericValue value(type,bits);if(type.kind()==NumericType::Kind::Float)finite(value.floatingValue());return value;
}
NumericValue NumericValue::floating(double value,unsigned width) {
 const auto type=NumericType::floating(width);finite(value);
 if(width==32){const float rounded=static_cast<float>(value);finite(rounded);std::uint32_t bits;std::memcpy(&bits,&rounded,4);return NumericValue(type,bits);}
 std::uint64_t bits;std::memcpy(&bits,&value,8);return NumericValue(type,bits);
}
double NumericValue::floatingValue() const {
 if(type_.kind()!=NumericType::Kind::Float)throw std::invalid_argument("An angle is not a floating-point value");
 if(type_.width()==32){auto bits=static_cast<std::uint32_t>(bits_);float value;std::memcpy(&value,&bits,4);return value;}
 double value;std::memcpy(&value,&bits_,8);return value;
}
NumericValue NumericValue::fromInteger(const TypedInteger &value,unsigned width) {
 NumericType::floating(width);const auto &integer=value.value();const bool negative=integer.negative();
 const auto magnitude=negative ? ((~integer.bits())&mask(integer.width()))+1 : integer.bits();
 // Convert directly to the destination precision, avoiding uint64→double→float double rounding.
 if(width==32){const float number=static_cast<float>(magnitude);return floating(negative ? -number : number,32);}
 const double number=static_cast<double>(magnitude);return floating(negative ? -number : number,64);
}
bool NumericValue::truth() const {return type_.kind()==NumericType::Kind::Angle ? bits_!=0 : floatingValue()!=0;}
double NumericValue::radians() const {return type_.kind()==NumericType::Kind::Float ? floatingValue() : std::ldexp(static_cast<double>(bits_),-static_cast<int>(type_.width()))*(2*std::acos(-1.0));}
std::string NumericValue::exactRadians() const {
 if(type_.kind()==NumericType::Kind::Angle)return "(2*pi*"+std::to_string(bits_)+"/"+(type_.width()==64 ? "18446744073709551616" : std::to_string(std::uint64_t(1)<<type_.width()))+")";
 Rational value;mpq_set_d(value.value,floatingValue());
 std::vector<char> text(mpz_sizeinbase(mpq_numref(value.value),10)+mpz_sizeinbase(mpq_denref(value.value),10)+4);
 mpq_get_str(text.data(),10,value.value);return "("+std::string(text.data())+")";
}
NumericValue NumericValue::cast(NumericType target) const {
 if(type_==target)return *this;
 if(type_.kind()==NumericType::Kind::Angle) {
  if(target.kind()!=NumericType::Kind::Angle)throw std::invalid_argument("Angles cannot be cast to float");
  return fromBits(target,target.width()>type_.width() ? bits_<<(target.width()-type_.width()) : bits_>>(type_.width()-target.width()));
 }
 if(target.kind()==NumericType::Kind::Float)return floating(floatingValue(),target.width());
 // Quantize modulo the source precision's tau using exact rational arithmetic.
 // This retains low bits even for angle[64], huge inputs and negative values.
 const double tau=type_.width()==32 ? static_cast<double>(static_cast<float>(2*std::acos(-1.0))) : 2*std::acos(-1.0);
 Rational value,period;mpq_set_d(value.value,floatingValue());mpq_set_d(period.value,tau);
 mpq_div(value.value,value.value,period.value);mpq_mul_2exp(value.value,value.value,target.width());
 BigInteger quotient,remainder;mpz_fdiv_qr(quotient.value,remainder.value,mpq_numref(value.value),mpq_denref(value.value));
 mpz_mul_2exp(remainder.value,remainder.value,1);const int halfway=mpz_cmp(remainder.value,mpq_denref(value.value));
 if(halfway>0 || (halfway==0 && mpz_odd_p(quotient.value)))mpz_add_ui(quotient.value,quotient.value,1);
 mpz_fdiv_r_2exp(quotient.value,quotient.value,target.width());return fromBits(target,raw(quotient.value));
}
TypedInteger NumericValue::integerCast(IntegerType target) const {
 if(type_.kind()!=NumericType::Kind::Float)throw std::invalid_argument("Angles cannot be cast to integer");
 BigInteger integer,limit;mpz_set_d(integer.value,floatingValue());
 const bool signedTarget=target.signedness()==Integer::Signedness::Signed;
 mpz_set_ui(limit.value,1);mpz_mul_2exp(limit.value,limit.value,target.width()-(signedTarget ? 1 : 0));
 if(mpz_cmp(integer.value,limit.value)>=0)throw std::out_of_range("Float-to-integer cast exceeds the destination range");
 if(signedTarget)mpz_neg(limit.value,limit.value);else mpz_set_ui(limit.value,0);
 if(mpz_cmp(integer.value,limit.value)<0)throw std::out_of_range("Float-to-integer cast exceeds the destination range");
 mpz_fdiv_r_2exp(integer.value,integer.value,target.width());return TypedInteger::fromBits(target,raw(integer.value));
}
NumericValue NumericValue::binary(Operation operation,const NumericValue &right) const {
 if(type_.kind()==NumericType::Kind::Angle || right.type_.kind()==NumericType::Kind::Angle) {
  sameAngles(type_,right.type_);std::uint64_t result;
  switch(operation){case Operation::Add:result=bits_+right.bits_;break;case Operation::Subtract:result=bits_-right.bits_;break;
   case Operation::And:result=bits_&right.bits_;break;case Operation::Or:result=bits_|right.bits_;break;case Operation::Xor:result=bits_^right.bits_;break;
   default:throw std::invalid_argument("Unsupported operation between angles");}
  return fromBits(type_,result&mask(type_.width()));
 }
 const unsigned width=std::max(type_.width(),right.type_.width());const double a=floatingValue(),b=right.floatingValue();
 if((operation==Operation::Divide || operation==Operation::Mod) && b==0)throw std::domain_error("Runtime real division by zero");
 double result;
 if(width==32) {
  const float x=static_cast<float>(a),y=static_cast<float>(b);float rounded;
  switch(operation){case Operation::Add:rounded=x+y;break;case Operation::Subtract:rounded=x-y;break;case Operation::Multiply:rounded=x*y;break;case Operation::Divide:rounded=x/y;break;
   case Operation::Power:rounded=std::pow(x,y);break;case Operation::Mod:rounded=std::fmod(x,y);break;default:throw std::invalid_argument("Unsupported floating-point operation");}
  result=rounded;
 } else {
  switch(operation){case Operation::Add:result=a+b;break;case Operation::Subtract:result=a-b;break;case Operation::Multiply:result=a*b;break;case Operation::Divide:result=a/b;break;
   case Operation::Power:result=std::pow(a,b);break;case Operation::Mod:result=std::fmod(a,b);break;default:throw std::invalid_argument("Unsupported floating-point operation");}
 }
 return floating(result,width);
}
NumericValue NumericValue::function(Function function) const {
 if(type_.kind()==NumericType::Kind::Angle) {
  if(function==Function::Negate)return fromBits(type_,(0-bits_)&mask(type_.width()));
  if(function==Function::Complement)return fromBits(type_,(~bits_)&mask(type_.width()));
  if(function!=Function::Sin && function!=Function::Cos && function!=Function::Tan)throw std::invalid_argument("Only trigonometric functions accept angle values");
 }
 const double x=radians();double result;
 switch(function){case Function::Negate:result=-x;break;case Function::Sin:result=std::sin(x);break;case Function::Cos:result=std::cos(x);break;case Function::Tan:result=std::tan(x);break;
  case Function::Arcsin:result=std::asin(x);break;case Function::Arccos:result=std::acos(x);break;case Function::Arctan:result=std::atan(x);break;case Function::Exp:result=std::exp(x);break;
  case Function::Log:result=std::log(x);break;case Function::Sqrt:result=std::sqrt(x);break;case Function::Floor:result=std::floor(x);break;case Function::Ceiling:result=std::ceil(x);break;
  default:throw std::invalid_argument("Unsupported numeric function");}
 return floating(result,type_.kind()==NumericType::Kind::Angle ? 64 : type_.width());
}
NumericValue NumericValue::scale(Scaling operation,const TypedInteger &right) const {
 if(type_.kind()!=NumericType::Kind::Angle || right.type().signedness()!=Integer::Signedness::Unsigned)throw std::invalid_argument("Angle scaling requires an unsigned integer");
 const auto n=right.value().bits();std::uint64_t result;
 if(operation==Scaling::ShiftLeft || operation==Scaling::ShiftRight)result=n>=type_.width() ? 0 : operation==Scaling::ShiftLeft ? bits_<<n : bits_>>n;
 else {
  if(right.type().width()!=type_.width())throw std::invalid_argument("Angle scaling requires equal widths");
  if(operation==Scaling::Multiply)result=bits_*n;
  else if(operation==Scaling::Divide){if(!n)throw std::domain_error("Runtime angle division by zero");result=bits_/n;}
  else throw std::invalid_argument("Unsupported angle scaling operation");
 }
 return fromBits(type_,result&mask(type_.width()));
}
TypedInteger NumericValue::ratio(const NumericValue &right) const {
 sameAngles(type_,right.type_);if(!right.bits_)throw std::domain_error("Runtime angle division by zero");
 return TypedInteger::fromBits(IntegerType::sized(Integer::Signedness::Unsigned,type_.width()),bits_/right.bits_);
}
int NumericValue::compare(const NumericValue &right) const {
 if(type_.kind()==NumericType::Kind::Angle || right.type_.kind()==NumericType::Kind::Angle){sameAngles(type_,right.type_);return bits_<right.bits_ ? -1 : bits_>right.bits_ ? 1 : 0;}
 const double a=floatingValue(),b=right.floatingValue();return a<b ? -1 : a>b ? 1 : 0;
}
NumericStorage::NumericStorage(const std::vector<NumericType> &types){for(auto type:types)slots_.emplace_back(type);}
NumericType NumericStorage::type(std::size_t index) const{return slots_.at(index).type;}
bool NumericStorage::initialized(std::size_t index) const{return slots_.at(index).initialized;}
NumericValue NumericStorage::read(std::size_t index) const {const auto &slot=slots_.at(index);if(!slot.initialized)throw std::domain_error("Numeric variable read before initialization");return NumericValue::fromBits(slot.type,slot.bits);}
void NumericStorage::write(std::size_t index,const NumericValue &value){auto &slot=slots_.at(index);const auto converted=value.cast(slot.type);slot.bits=converted.bits();slot.initialized=true;}
void NumericStorage::clear(std::size_t index){auto &slot=slots_.at(index);slot.bits=0;slot.initialized=false;}
}
