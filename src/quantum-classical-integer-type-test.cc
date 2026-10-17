// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassicalIntegerType.h"
#include <iostream>
#include <stdexcept>
using QuantumClassical::Integer;using QuantumClassical::IntegerType;using QuantumClassical::TypedInteger;
using Sign=Integer::Signedness;using Op=Integer::Operation;
unsigned checks=0;void check(bool ok){++checks;if(!ok)throw std::runtime_error("Integer type check failed: "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
int main(){try {
 auto machine=IntegerType::machine(Sign::Signed),umachine=IntegerType::machine(Sign::Unsigned);
 check(machine!=IntegerType::sized(Sign::Signed,64));check(umachine!=IntegerType::sized(Sign::Unsigned,64));
 for(unsigned a=1;a<=64;++a)for(unsigned b=1;b<=64;++b)for(auto sa:{Sign::Signed,Sign::Unsigned})for(auto sb:{Sign::Signed,Sign::Unsigned}) {
  auto left=IntegerType::sized(sa,a),right=IntegerType::sized(sb,b),result=IntegerType::common(left,right);
  // Independent range model: choose signed machine storage only when both
  // input type ranges fit its positive limit.
  auto leftMaximum=~std::uint64_t(0)>>(64-a),rightMaximum=~std::uint64_t(0)>>(64-b);
  if(sa==Sign::Signed)leftMaximum>>=1;
  if(sb==Sign::Signed)rightMaximum>>=1;
  const auto signedMaximum=~std::uint64_t(0)>>1;
  bool unsignedResult=leftMaximum>signedMaximum || rightMaximum>signedMaximum;
  check(result.width()==64 && !result.explicitWidth());check(result.signedness()==(unsignedResult ? Sign::Unsigned : Sign::Signed));
  check(result==IntegerType::common(right,left));
 }
 auto s8=IntegerType::sized(Sign::Signed,8),u8=IntegerType::sized(Sign::Unsigned,8);
 auto negative=TypedInteger::fromBits(s8,255),positive=TypedInteger::fromBits(u8,255);
 check(negative.compare(positive)<0);
 auto sum=TypedInteger::fromBits(s8,127).binary(Op::Add,TypedInteger::fromBits(s8,1));
 check(sum.type()==machine && sum.value().bits()==128);check(sum.cast(s8).value().negative());
 check(negative.cast(machine).value().bits()==~std::uint64_t(0));
 check(negative.cast(IntegerType::sized(Sign::Signed,64)).type()!=negative.cast(machine).type());
 auto all=TypedInteger::fromBits(umachine,~std::uint64_t(0));check(negative.compare(all)==0);
 auto wrap=all.binary(Op::Add,TypedInteger::fromBits(machine,1));check(wrap.type()==umachine && wrap.value().bits()==0);
 auto quotient=TypedInteger::fromBits(s8,249).binary(Op::Divide,TypedInteger::fromBits(u8,2));
 check(quotient.type()==machine && quotient.value().bits()==~std::uint64_t(2));
 // Powers use the same promotion boundary as the other binary arithmetic.
 auto power=TypedInteger::fromBits(s8,2).binary(Op::Power,TypedInteger::fromBits(u8,8));
 check(power.type()==machine && power.value().bits()==256);
 check(negative.binary(Op::Power,TypedInteger::fromBits(u8,3)).value().bits()==~std::uint64_t(0));
 reject<std::domain_error>([&]{positive.binary(Op::Power,negative);});
 check(TypedInteger::fromBits(machine,0).binary(Op::Power,TypedInteger::fromBits(machine,0)).value().bits()==1);
 reject<std::overflow_error>([&]{TypedInteger::fromBits(machine,2).binary(Op::Power,TypedInteger::fromBits(machine,63));});
 auto wrapped=TypedInteger::fromBits(umachine,2).binary(Op::Power,TypedInteger::fromBits(u8,64));
 check(wrapped.type()==umachine && wrapped.value().bits()==0);
 // Usual conversions happen before the operation, including the exponent.
 check(all.binary(Op::Power,negative).value().bits()==~std::uint64_t(0));
 reject<std::out_of_range>([]{IntegerType::sized(Sign::Signed,0);});
 reject<std::out_of_range>([]{IntegerType::sized(Sign::Unsigned,65);});
 reject<std::invalid_argument>([]{IntegerType::machine(static_cast<Sign>(9));});
 reject<std::out_of_range>([&]{TypedInteger::fromBits(s8,256);});
 std::cout<<"PASS: "<<checks<<" integer type checks.\n";return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
