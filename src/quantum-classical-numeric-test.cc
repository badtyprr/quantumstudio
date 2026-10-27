// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassicalNumeric.h"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
using namespace QuantumClassical;
using V=NumericValue;using T=NumericType;using O=V::Operation;using F=V::Function;using S=V::Scaling;
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("Numeric check "+std::to_string(checks));}
template<class E,class Fn>void rejects(Fn fn){bool caught=false;try{fn();}catch(const E&){caught=true;}check(caught);}
TypedInteger integer(std::uint64_t bits,unsigned width=64,bool sign=false){return TypedInteger::fromBits(IntegerType::sized(sign ? Integer::Signedness::Signed : Integer::Signedness::Unsigned,width),bits);}
int main(){try {
 rejects<std::invalid_argument>([]{T::floating(16);});rejects<std::invalid_argument>([]{T::angle(0);});rejects<std::invalid_argument>([]{T::angle(65);});
 for(unsigned width:{32,64}) {
  const auto zero=V::floating(-0.0,width);check(std::signbit(zero.floatingValue()));check(!zero.truth());
  check(zero.cast(T::floating(width==32 ? 64 : 32)).floatingValue()==0);
  rejects<std::domain_error>([&]{V::floating(std::numeric_limits<double>::infinity(),width);});
  rejects<std::domain_error>([&]{V::floating(std::numeric_limits<double>::quiet_NaN(),width);});
  auto one=V::floating(1,width),two=V::floating(2,width);
  check(one.binary(O::Add,two).floatingValue()==3);check(one.binary(O::Subtract,two).floatingValue()==-1);
  check(two.binary(O::Multiply,two).floatingValue()==4);check(one.binary(O::Divide,two).floatingValue()==.5);
  check(two.binary(O::Power,V::floating(3,width)).floatingValue()==8);
  check(V::floating(-5.5,width).binary(O::Mod,two).floatingValue()==-1.5);
  rejects<std::domain_error>([&]{one.binary(O::Divide,zero);});rejects<std::domain_error>([&]{one.binary(O::Mod,zero);});
  rejects<std::domain_error>([&]{V::floating(-1,width).binary(O::Power,V::floating(.5,width));});
  rejects<std::domain_error>([&]{V::floating(-1,width).function(F::Sqrt);});rejects<std::domain_error>([&]{zero.function(F::Log);});
  rejects<std::domain_error>([&]{two.function(F::Arcsin);});rejects<std::domain_error>([&]{two.function(F::Arccos);});
  check(V::floating(-1.5,width).function(F::Floor).floatingValue()==-2);check(V::floating(-1.5,width).function(F::Ceiling).floatingValue()==-1);
  check(one.function(F::Log).floatingValue()==0);check(zero.function(F::Exp).floatingValue()==1);
  check(zero.function(F::Sin).floatingValue()==0);check(zero.function(F::Cos).floatingValue()==1);check(zero.function(F::Tan).floatingValue()==0);
  check(zero.function(F::Arcsin).floatingValue()==0);check(one.function(F::Arccos).floatingValue()==0);check(zero.function(F::Arctan).floatingValue()==0);
  check(V::floating(9,width).function(F::Sqrt).floatingValue()==3);
  check(V::floating(-3.9,width).integerCast(IntegerType::sized(Integer::Signedness::Signed,8)).value().bits()==253);
  rejects<std::out_of_range>([&]{V::floating(128,width).integerCast(IntegerType::sized(Integer::Signedness::Signed,8));});
  rejects<std::out_of_range>([&]{V::floating(-1,width).integerCast(IntegerType::sized(Integer::Signedness::Unsigned,8));});
 }
 // Single-precision operations round before subsequent operations, rather than
 // retaining a hidden double-precision intermediate.
 auto big=V::floating(16777216,32);check(big.binary(O::Add,V::floating(1,32)).binary(O::Subtract,big).floatingValue()==0);
 check(big.binary(O::Add,V::floating(1,64)).binary(O::Subtract,big).floatingValue()==1);
 check(V::fromBits(T::floating(32),1).floatingValue()==std::ldexp(1.0,-149));
 check(V::fromBits(T::floating(32),1).binary(O::Divide,V::floating(2,32)).bits()==0);
 check(V::fromBits(T::floating(32),3).binary(O::Divide,V::floating(2,32)).bits()==2);
 rejects<std::domain_error>([]{V::floating(std::numeric_limits<float>::max(),32).binary(O::Multiply,V::floating(2,32));});
 rejects<std::domain_error>([]{V::floating(std::numeric_limits<double>::max()).binary(O::Multiply,V::floating(2));});
 rejects<std::domain_error>([]{V::fromBits(T::floating(32),0x7f800000);});
 rejects<std::out_of_range>([]{V::fromBits(T::floating(32),std::uint64_t(1)<<32);});
 const auto midpoint=(std::uint64_t(1)<<63)+(std::uint64_t(1)<<39)+1;
 check(V::fromInteger(integer(midpoint),32).bits()==0x5f000001);
 check(V::fromInteger(integer(midpoint),64).cast(T::floating(32)).bits()==0x5f000000);
 check(V::fromInteger(integer(std::uint64_t(1)<<63,64,true),32).floatingValue()==-std::ldexp(1.0,63));
 const double tau=2*std::acos(-1.0);
 for(unsigned width=1;width<=64;++width) {
  auto type=T::angle(width);const auto half=std::uint64_t(1)<<(width-1);
  check(V::floating(tau/2).cast(type).bits()==half);
  check(V::floating(-tau/2).cast(type).bits()==half);
  check(V::floating(tau).cast(type).bits()==0);
  auto a=V::fromBits(type,half);check(a.binary(O::Add,a).bits()==0);check(a.function(F::Negate).bits()==half);
  check(a.scale(S::ShiftLeft,integer(width)).bits()==0);check(a.scale(S::ShiftRight,integer(width)).bits()==0);
 }
 check(V::floating(tau/512).cast(T::angle(8)).bits()==0); // exact halfway, even zero
 check(V::floating(tau*(127.0/512)).cast(T::angle(8)).bits()==64);
 check(V::fromBits(T::angle(8),254).cast(T::angle(4)).bits()==15); // explicit truncation
 check(V::fromBits(T::angle(4),15).cast(T::angle(8)).bits()==240);
 const auto seven=V::fromBits(T::angle(4),7),one=V::fromBits(T::angle(4),1),ten=V::fromBits(T::angle(4),10);
 check(seven.binary(O::Add,one).bits()==8);check(one.binary(O::Subtract,seven).bits()==10);
 check(seven.scale(S::Divide,integer(2,4)).bits()==3);check(ten.scale(S::Multiply,integer(2,4)).bits()==4);
 check(ten.ratio(one).value().bits()==10);check(V::fromBits(T::angle(4),2).function(F::Negate).bits()==14);
 check(ten.binary(O::And,seven).bits()==2);check(ten.binary(O::Or,seven).bits()==15);check(ten.binary(O::Xor,seven).bits()==13);
 check(ten.function(F::Complement).bits()==5);check(seven.compare(ten)<0);
 check(V::fromBits(T::angle(4),4).function(F::Sin).floatingValue()==1);
 rejects<std::invalid_argument>([&]{seven.cast(T::floating());});rejects<std::invalid_argument>([&]{seven.integerCast(IntegerType::machine(Integer::Signedness::Unsigned));});
 rejects<std::invalid_argument>([&]{seven.scale(S::Multiply,integer(2,8));});rejects<std::invalid_argument>([&]{seven.binary(O::Add,V::fromBits(T::angle(8),1));});
 rejects<std::domain_error>([&]{seven.scale(S::Divide,integer(0,4));});
 NumericStorage storage({T::floating(32),T::angle(4)});check(!storage.initialized(0));rejects<std::domain_error>([&]{storage.read(0);});
 storage.write(0,V::floating(16777217));check(storage.read(0).floatingValue()==16777216);
 storage.write(1,seven);auto copy=storage;copy.write(1,ten);check(storage.read(1).bits()==7);check(copy.read(1).bits()==10);
 rejects<std::invalid_argument>([&]{storage.write(0,seven);});check(storage.read(0).floatingValue()==16777216);
 copy.clear(1);rejects<std::domain_error>([&]{copy.read(1);});check(storage.read(1).bits()==7);
 std::cout<<"PASS: "<<checks<<" typed numeric checks.\n";return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
