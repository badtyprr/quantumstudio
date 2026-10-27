// GPL-2.0-or-later; see COPYING.
#include "QuantumRuntimeGate.h"
#include <cmath>
#include <gmp.h>
#include <stdexcept>
namespace QuantumNumerics {
namespace {
unsigned parameterCount(RuntimeGate::Kind kind) {
 using K=RuntimeGate::Kind;
 switch(kind) {
  case K::X:case K::Y:case K::Z:case K::Phase:case K::GlobalPhase:return 1;
  case K::U3:case K::PublishedU:return 3;
 }
 throw std::invalid_argument("Unknown runtime gate");
}
std::string rational(double value) {
 mpq_t number;mpq_init(number);mpq_set_d(number,value);
 try {
  std::vector<char> text(mpz_sizeinbase(mpq_numref(number),10)+mpz_sizeinbase(mpq_denref(number),10)+4);
  mpq_get_str(text.data(),10,number);std::string result(text.data());mpq_clear(number);return "("+result+")";
 } catch(...) {mpq_clear(number);throw;}
}
std::vector<Complex> multiply(const std::vector<Complex> &a,const std::vector<Complex> &b,unsigned n) {
 std::vector<Complex> result(n*n);
 for(unsigned r=0;r<n;++r)for(unsigned c=0;c<n;++c)for(unsigned k=0;k<n;++k)
  result[r*n+c]+=a[r*n+k]*b[k*n+c];
 return result;
}
}
RuntimeGate::RuntimeGate(Kind kind,const std::vector<QuantumClassical::RealExpression> &parameters,
 unsigned controls,std::uint64_t state,int power):kind_(kind),parameters_(parameters),controls_(controls),controlState_(state),power_(power) {
 if(parameters.size()!=parameterCount(kind))throw std::invalid_argument("Incorrect runtime gate parameter count");
 if(controls>3-targetCount())throw std::length_error("Runtime gates support at most three wires including controls");
 if(state>=(std::uint64_t(1)<<controls))throw std::out_of_range("Runtime gate control state exceeds its controls");
 if(power < -64 || power > 64)throw std::out_of_range("Runtime gate powers must be integers between -64 and 64");
}
unsigned RuntimeGate::targetCount() const {return kind_==Kind::GlobalPhase ? 0 : 1;}
RuntimeGate::RuntimeGate(Kind kind,const std::vector<QuantumClassical::RealExpression> &parameters,
 unsigned controls,std::uint64_t state,const QuantumClassical::IntegerExpression &power):RuntimeGate(kind,parameters,controls,state,1) {
 powerExpression_=std::make_shared<const QuantumClassical::IntegerExpression>(power);
}
void RuntimeGate::validate(unsigned bits,const QuantumClassical::IntegerStorage &storage) const {
 for(const auto &parameter:parameters_)parameter.validate(bits,storage);
 if(powerExpression_)powerExpression_->validate(bits,storage);
}
RuntimeGate::Value RuntimeGate::evaluate(std::uint64_t record,unsigned bits,const QuantumClassical::IntegerStorage &storage) const {
 std::vector<double> values;values.reserve(parameters_.size());
 for(const auto &parameter:parameters_)values.push_back(parameter.evaluate(record,bits,storage));
 int power=power_;
 if(powerExpression_) {
  const auto value=powerExpression_->evaluate(record,bits,storage).value();
  const auto mask=value.width()==64 ? ~std::uint64_t(0) : (std::uint64_t(1)<<value.width())-1;
  const auto magnitude=value.negative() ? ((~value.bits())&mask)+1 : value.bits();
  if(magnitude>64)throw std::out_of_range("Runtime gate power exceeds -64 through 64");
  power=value.negative() ? -static_cast<int>(magnitude) : static_cast<int>(magnitude);
 }
 return Value(kind_,values,controls_,controlState_,power);
}
RuntimeGate::Value::Value(Kind kind,const std::vector<double> &parameters,unsigned controls,std::uint64_t state,int power):
 kind_(kind),parameters_(parameters),controls_(controls),controlState_(state),power_(power) {}
unsigned RuntimeGate::Value::targetCount() const {return kind_==Kind::GlobalPhase ? 0 : 1;}
std::vector<Complex> RuntimeGate::Value::baseMatrix() const {
 const double theta=parameters_[0],c=std::cos(theta/2),s=std::sin(theta/2);
 auto phase=[](double x){return Complex(std::cos(x),std::sin(x));};
 std::vector<Complex> base;
 switch(kind_) {
  case Kind::X:base={c,Complex(0,-s),Complex(0,-s),c};break;
  case Kind::Y:base={c,-s,s,c};break;
  case Kind::Z:base={phase(-theta/2),0,0,phase(theta/2)};break;
  case Kind::Phase:base={1,0,0,phase(theta)};break;
  case Kind::GlobalPhase:base={phase(theta)};break;
  case Kind::U3:case Kind::PublishedU:
   // Multiply phases separately: adding two finite parameters can overflow.
   base={c,-phase(parameters_[2])*s,phase(parameters_[1])*s,phase(parameters_[1])*phase(parameters_[2])*c};
   if(kind_==Kind::PublishedU)for(auto &entry:base)entry*=phase(theta/2);
   break;
 }
 const unsigned n=1U<<targetCount();
 if(power_<0) {
  auto original=base;
  for(unsigned r=0;r<n;++r)for(unsigned col=0;col<n;++col)base[r*n+col]=std::conj(original[col*n+r]);
 }
 std::vector<Complex> result(n*n);for(unsigned k=0;k<n;++k)result[k*n+k]=1;
 for(int k=0;k<std::abs(power_);++k)result=multiply(result,base,n);
 return result;
}
std::vector<Complex> RuntimeGate::Value::matrix() const {
 const unsigned n=1U<<wireCount(),baseSize=1U<<targetCount();
 std::vector<Complex> result(n*n);for(unsigned k=0;k<n;++k)result[k*n+k]=1;
 const auto base=baseMatrix();const auto offset=activeOffset();
 for(unsigned r=0;r<baseSize;++r)for(unsigned c=0;c<baseSize;++c)result[(offset+r)*n+offset+c]=base[r*baseSize+c];
 return result;
}
std::string RuntimeGate::Value::exactBaseExpression() const {
 const std::string theta=rational(parameters_[0]);std::string base;
 switch(kind_) {
  case Kind::X:base="Rx("+theta+")";break;
  case Kind::Y:base="Ry("+theta+")";break;
  case Kind::Z:base="Rz("+theta+")";break;
  case Kind::Phase:base="P("+theta+")";break;
  case Kind::GlobalPhase:base="exp(i*"+theta+")";break;
  case Kind::U3:case Kind::PublishedU:
   base="U3("+theta+","+rational(parameters_[1])+","+rational(parameters_[2])+")";
   if(kind_==Kind::PublishedU)base="(exp(i*"+theta+"/2)*"+base+")";
   break;
 }
 return "("+base+")^("+std::to_string(power_)+")";
}
}
