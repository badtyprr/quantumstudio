// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassicalIntegerExpression.h"
#include "libqalculate/QuantumClassicalIntegerStorage.h"
#include "libqalculate/QuantumClassical.h"
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
 auto invert=Expr::fromBits(s8,Bits::complement(Bits::read({0,1,2,3,4,5,6,7})));
 for(unsigned value=0;value<256;++value) {
  check(invert.evaluate(value,8).value().bits()==(255^value));
  check(invert.evaluate(value,8).value().negative()==(value<128));
 }
 reject<std::invalid_argument>([&]{Expr::fromBits(s8,Bits::constant(1,1));});
 reject<std::out_of_range>([&]{invert.validate(7);});
 reject<std::out_of_range>([&]{invert.evaluate(256,8);});
 auto u1=IntegerType::sized(Sign::Unsigned,1);
 auto flag=Expr::fromBits(u1,Bits::constant(1,1));
 check(Expr::cast(machine,flag).evaluate(0,0).value().bits()==1);
 auto high=Expr::fromBits(IntegerType::sized(Sign::Unsigned,64),Bits::read({63,62,61,60,59,58,57,56,55,54,53,52,51,50,49,48,47,46,45,44,43,42,41,40,39,38,37,36,35,34,33,32,31,30,29,28,27,26,25,24,23,22,21,20,19,18,17,16,15,14,13,12,11,10,9,8,7,6,5,4,3,2,1,0}));
 check(high.evaluate(1,64).value().bits()==(std::uint64_t(1)<<63));
 auto guarded=Bits::logical(Bits::Binary::And,Bits::constant(1,0),
  Bits::integerCompare(Bits::Binary::Equal,Expr::variable(s8,0),constant(0)));
 IntegerStorage undefined({s8});
 auto lazy=Expr::fromBits(u1,guarded);
 lazy.validate(0,undefined);check(lazy.evaluate(0,0,undefined).value().bits()==0);
 reject<std::invalid_argument>([&]{lazy.validate(0);});
 IntegerStorage wrongType({u8});reject<std::invalid_argument>([&]{lazy.validate(0,wrongType);});
 auto strict=Expr::fromBits(u1,Bits::integerCompare(Bits::Binary::Equal,Expr::variable(s8,0),constant(0)));
 reject<std::domain_error>([&]{strict.evaluate(0,0,undefined);});
 undefined.write(0,TypedInteger::fromBits(s8,0));check(strict.evaluate(0,0,undefined).value().bits()==1);
 auto depthBits=Bits::constant(1,0);
 for(unsigned n=0;n<15;++n)depthBits=Bits::fromInteger(Expr::fromBits(u1,depthBits));
 auto depthLimit=Expr::fromBits(u1,depthBits);check(depthLimit.evaluate(0,0).value().bits()==0);
 reject<std::length_error>([&]{Bits::fromInteger(depthLimit);});
 auto broad=Bits::constant(1,0);
 for(unsigned n=0;n<8;++n)broad=Bits::binary(Bits::Binary::Or,broad,broad);
 auto countLimit=Expr::fromBits(u1,broad);check(countLimit.evaluate(0,0).value().bits()==0);
 reject<std::length_error>([&]{Bits::fromInteger(countLimit);});
 IntegerStorage storage({s8,machine});auto variable=Expr::variable(s8,0);
 variable.validate(0,storage);check(true); // An uninitialized slot is structurally valid.
 reject<std::domain_error>([&]{variable.evaluate(0,0,storage);});
 reject<std::invalid_argument>([&]{variable.validate(0);});
 reject<std::invalid_argument>([&]{variable.evaluate(0,0);});
 reject<std::invalid_argument>([&]{Expr::variable(machine,0).validate(0,storage);});
 reject<std::out_of_range>([&]{Expr::variable(s8,2).validate(0,storage);});
 storage.write(0,TypedInteger::fromBits(s8,3));
 auto mixed=Expr::binary(Op::Add,variable,byte);
 check(mixed.evaluate(2,8,storage).value().bits()==5);
 reject<std::out_of_range>([&]{mixed.validate(7,storage);});
 reject<std::out_of_range>([&]{mixed.evaluate(256,8,storage);});
 auto fork=storage;fork.write(0,TypedInteger::fromBits(s8,7));
 check(mixed.evaluate(2,8,fork).value().bits()==9 && mixed.evaluate(2,8,storage).value().bits()==5);
 auto powerVariable=Expr::binary(Op::Power,constant(2),variable);
 check(powerVariable.evaluate(0,0,storage).value().bits()==8);
 storage.clear(0);reject<std::domain_error>([&]{powerVariable.evaluate(0,0,storage);});
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
 auto exponent=Expr::read(IntegerType::sized(Sign::Unsigned,3),{8,9,10});
 auto power=Expr::binary(Op::Power,byte,exponent);
 check(power.type()==machine);
 // Independent repeated-multiplication oracle across every signed-byte base
 // and three-bit exponent, both read from the actual measurement record.
 for(unsigned raw=0;raw<256;++raw)for(unsigned e=0;e<8;++e) {
  std::int64_t base=raw<128 ? raw : static_cast<std::int64_t>(raw)-256,expected=1;
  for(unsigned n=0;n<e;++n)expected*=base;
  check(power.evaluate(raw|(e<<8),11).value().bits()==static_cast<std::uint64_t>(expected));
 }
 reject<std::out_of_range>([&]{power.validate(10);});
 reject<std::out_of_range>([&]{power.evaluate(2048,11);});
 auto negativePower=Expr::binary(Op::Power,constant(2),byte);
 negativePower.validate(8);check(true); // Validation must not evaluate operands.
 reject<std::domain_error>([&]{negativePower.evaluate(255,8);});
 check(negativePower.evaluate(3,8).value().bits()==8);
 reject<std::overflow_error>([&]{negativePower.evaluate(63,8);});
 auto rightAssociated=Expr::binary(Op::Power,constant(2),Expr::binary(Op::Power,constant(3),constant(2)));
 check(rightAssociated.evaluate(0,0).value().bits()==512);
 check(Expr::binary(Op::Subtract,constant(0),Expr::binary(Op::Power,constant(2),constant(2))).evaluate(0,0).value().bits()==~std::uint64_t(3));
 auto deepPower=constant(1);for(unsigned n=1;n<32;++n)deepPower=Expr::binary(Op::Power,deepPower,constant(1));
 check(deepPower.evaluate(0,0).value().bits()==1);
 reject<std::length_error>([&]{Expr::binary(Op::Power,deepPower,constant(1));});
 auto widePower=constant(1);for(unsigned n=0;n<8;++n)widePower=Expr::binary(Op::Power,widePower,widePower);
 check(widePower.evaluate(0,0).value().bits()==1); // 511 expanded nodes.
 reject<std::length_error>([&]{Expr::binary(Op::Power,widePower,widePower);});
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
