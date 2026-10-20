// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassicalRealExpression.h"
#include "libqalculate/QuantumClassicalIntegerStorage.h"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace QuantumClassical;
using R=RealExpression;
using I=IntegerExpression;
using Op=R::Operation;
using Sign=Integer::Signedness;
unsigned checks=0;
void check(bool ok) {++checks;if(!ok)throw std::runtime_error("Real expression check "+std::to_string(checks));}
template<class E,class F>void reject(F f) {bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
int main() {try {
 IntegerStorage empty({});
 auto evaluate=[&](const R &r){return r.evaluate(0,0,empty);};
 for(int a=-8;a<=8;++a)for(int b=-8;b<=8;++b) {
  auto x=R::constant(a),y=R::constant(b);
  check(evaluate(R::binary(Op::Add,x,y))==a+b);
  check(evaluate(R::binary(Op::Subtract,x,y))==a-b);
  check(evaluate(R::binary(Op::Multiply,x,y))==a*b);
  if(b)check(evaluate(R::binary(Op::Divide,x,y))==double(a)/b);
 }
 // Independent small signed/unsigned conversion oracle.
 for(unsigned width=1;width<=8;++width)for(auto sign:{Sign::Signed,Sign::Unsigned}) {
  auto type=IntegerType::sized(sign,width);
  for(unsigned raw=0;raw<(1u<<width);++raw) {
   int expected=sign==Sign::Signed && raw>=(1u<<(width-1)) ? int(raw)-int(1u<<width) : int(raw);
   check(evaluate(R::fromInteger(I::constant(TypedInteger::fromBits(type,raw))))==expected);
  }
 }
 auto signed64=IntegerType::machine(Sign::Signed),unsigned64=IntegerType::machine(Sign::Unsigned);
 check(evaluate(R::fromInteger(I::constant(TypedInteger::fromBits(signed64,1ull<<63))))==-std::ldexp(1.0,63));
 check(evaluate(R::fromInteger(I::constant(TypedInteger::fromBits(signed64,~0ull))))==-1);
 check(evaluate(R::fromInteger(I::constant(TypedInteger::fromBits(unsigned64,~0ull))))==std::ldexp(1.0,64));
 auto bit=IntegerType::sized(Sign::Unsigned,1);
 auto feedback=R::binary(Op::Multiply,R::constant(std::acos(-1.0)),R::fromInteger(I::read(bit,{0})));
 check(feedback.evaluate(0,1,empty)==0);check(feedback.evaluate(1,1,empty)==std::acos(-1.0));
 reject<std::out_of_range>([&]{feedback.validate(0,empty);});
 IntegerStorage storage({signed64});
 auto variable=R::fromInteger(I::variable(signed64,0));
 variable.validate(0,storage); // Undefined is legal until the gate executes.
 reject<std::domain_error>([&]{variable.evaluate(0,0,storage);});
 storage.write(0,TypedInteger::fromBits(signed64,3));check(variable.evaluate(0,0,storage)==3);
 auto fork=storage;storage.write(0,TypedInteger::fromBits(signed64,5));
 check(variable.evaluate(0,0,storage)==5);check(variable.evaluate(0,0,fork)==3);
 reject<std::out_of_range>([&]{variable.validate(0,empty);});
 IntegerStorage wrong({unsigned64});
 reject<std::invalid_argument>([&]{variable.validate(0,wrong);});
 auto zero=R::constant(0),one=R::constant(1);
 // Integer operations must finish in their declared type before conversion.
 auto three=I::constant(TypedInteger::fromBits(signed64,3));
 auto two=I::constant(TypedInteger::fromBits(signed64,2));
 check(evaluate(R::fromInteger(I::binary(Integer::Operation::Divide,three,two)))==1);
 check(evaluate(R::binary(Op::Divide,R::fromInteger(three),R::fromInteger(two)))==1.5);
 auto maximum=I::constant(TypedInteger::fromBits(signed64,(1ull<<63)-1));
 reject<std::overflow_error>([&]{evaluate(R::fromInteger(I::binary(Integer::Operation::Add,maximum,two)));});
 // Validation cannot read or precompute even an invalid runtime division.
 auto divisor=R::binary(Op::Divide,one,variable);
 storage.clear(0);divisor.validate(0,storage);
 reject<std::domain_error>([&]{divisor.evaluate(0,0,storage);});
 storage.write(0,TypedInteger::fromBits(signed64,0));
 reject<std::domain_error>([&]{divisor.evaluate(0,0,storage);});
 storage.write(0,TypedInteger::fromBits(signed64,2));
 check(divisor.evaluate(0,0,storage)==0.5);
 reject<std::domain_error>([&]{R::constant(std::numeric_limits<double>::infinity());});
 reject<std::domain_error>([&]{R::constant(std::numeric_limits<double>::quiet_NaN());});
 reject<std::domain_error>([&]{evaluate(R::binary(Op::Divide,one,zero));});
 reject<std::domain_error>([&]{evaluate(R::binary(Op::Divide,one,R::constant(-0.0)));});
 reject<std::domain_error>([&]{evaluate(R::binary(Op::Multiply,R::constant(std::numeric_limits<double>::max()),R::constant(2)));});
 reject<std::invalid_argument>([&]{R::binary(static_cast<Op>(99),one,one);});
 reject<std::out_of_range>([&]{one.evaluate(1,0,empty);});
 reject<std::out_of_range>([&]{one.validate(65,empty);});
 check(one.evaluate(~0ull,64,empty)==1);
 auto deep=one;for(int i=1;i<32;++i)deep=R::binary(Op::Add,deep,zero);
 reject<std::length_error>([&]{R::binary(Op::Add,deep,zero);});
 auto wide=one;for(int i=0;i<8;++i)wide=R::binary(Op::Add,wide,wide);
 check(evaluate(wide)==256);
 reject<std::length_error>([&]{R::binary(Op::Add,wide,wide);});
 auto integer=I::constant(TypedInteger::fromBits(signed64,0));
 for(int i=1;i<32;++i)integer=I::cast(signed64,integer);
 reject<std::length_error>([&]{R::fromInteger(integer);});
 std::cout<<"PASS: "<<checks<<" runtime real expression checks.\n";
}catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
