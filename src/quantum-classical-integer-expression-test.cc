// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassicalIntegerExpression.h"
#include <iostream>
#include <stdexcept>
using namespace QuantumClassical;
using Sign=Integer::Signedness;using Op=Integer::Operation;using Expr=IntegerExpression;
unsigned checks=0;void check(bool ok){++checks;if(!ok)throw std::runtime_error("Integer expression check failed: "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
int main(){try {
 auto machine=IntegerType::machine(Sign::Signed),s8=IntegerType::sized(Sign::Signed,8),u8=IntegerType::sized(Sign::Unsigned,8);
 auto constant=[&](std::uint64_t value){return Expr::constant(TypedInteger::fromBits(machine,value));};
 auto byte=Expr::read(s8,{0,1,2,3,4,5,6,7});
 check(byte.evaluate(255,8).value().negative());check(byte.type()==s8);
 auto widened=Expr::cast(machine,byte);check(widened.evaluate(255,8).value().bits()==~std::uint64_t(0));
 auto unsignedByte=Expr::cast(u8,byte);check(unsignedByte.evaluate(255,8).value().bits()==255);
 auto divide=Expr::binary(Op::Divide,constant(6),byte);
 divide.validate(8);check(true); // No fabricated zero divisor during validation.
 check(divide.type()==machine && divide.evaluate(2,8).value().bits()==3);
 check(divide.evaluate(254,8).value().bits()==~std::uint64_t(2));
 reject<std::domain_error>([&]{divide.evaluate(0,8);});
 reject<std::out_of_range>([&]{divide.validate(7);});
 reject<std::out_of_range>([&]{byte.evaluate(256,8);});
 reject<std::out_of_range>([&]{constant(0).validate(65);});
 constant(6).validate(0);check(constant(6).evaluate(0,0).value().bits()==6);
 for(unsigned width=1;width<=64;++width) {
  std::vector<unsigned> indices;for(unsigned k=0;k<width;++k)indices.push_back(63-k);
  auto type=IntegerType::sized(Sign::Unsigned,width);auto value=Expr::read(type,indices).evaluate(std::uint64_t(1)<<63,64);
  check(value.type()==type && value.value().bits()==1);
 }
 auto sum=Expr::binary(Op::Add,byte,constant(1));
 check(sum.evaluate(127,8).value().bits()==128);
 check(Expr::cast(s8,sum).evaluate(127,8).value().negative());
 check(byte.evaluate(127,8).value().bits()==127); // Building wrappers never mutates inputs.
 reject<std::invalid_argument>([&]{Expr::read(s8,{0});});
 reject<std::out_of_range>([&]{Expr::read(IntegerType::sized(Sign::Unsigned,1),{64});});
 reject<std::invalid_argument>([&]{Expr::binary(static_cast<Op>(99),byte,byte);});
 check(Expr::binary(Op::Subtract,constant(9),byte).evaluate(2,8).value().bits()==7);
 check(Expr::binary(Op::Multiply,constant(9),byte).evaluate(2,8).value().bits()==18);
 check(Expr::binary(Op::Remainder,constant(9),byte).evaluate(2,8).value().bits()==1);
 auto maximum=constant(~std::uint64_t(0)>>1);
 auto overflow=Expr::binary(Op::Add,maximum,constant(1));overflow.validate(0);
 reject<std::overflow_error>([&]{overflow.evaluate(0,0);});
 auto nested=Expr::cast(machine,Expr::binary(Op::Multiply,constant(2),byte));
 reject<std::out_of_range>([&]{nested.validate(7);});
 auto deep=constant(0);for(unsigned i=1;i<32;++i)deep=Expr::cast(machine,deep);
 check(deep.evaluate(0,0).value().bits()==0);
 reject<std::length_error>([&]{Expr::cast(machine,deep);});
 auto shared=constant(0);for(unsigned i=0;i<8;++i)shared=Expr::binary(Op::Add,shared,shared); // 511 expanded nodes.
 check(shared.evaluate(0,0).value().bits()==0);
 auto full=Expr::cast(machine,shared);check(full.evaluate(0,0).value().bits()==0); // 512 nodes.
 reject<std::length_error>([&]{Expr::cast(machine,full);});
 reject<std::length_error>([&]{Expr::binary(Op::Add,shared,shared);});
 std::cout<<"PASS: "<<checks<<" runtime integer expression checks.\n";return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
