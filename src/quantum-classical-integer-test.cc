// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassicalInteger.h"
#include <iostream>
#include <limits>
#include <stdexcept>
using QuantumClassical::Integer;using Sign=Integer::Signedness;using Op=Integer::Operation;
unsigned checks=0;
void check(bool value){++checks;if(!value)throw std::runtime_error("Integer check failed: "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
int main(){try {
 for(unsigned w=1;w<=8;++w) {
  const std::int64_t size=std::int64_t(1)<<w,mask=size-1,minimum=-size/2,maximum=size/2-1;
  for(std::int64_t raw=0;raw<size;++raw)for(auto sign:{Sign::Signed,Sign::Unsigned}) {
   const auto value=sign==Sign::Signed && raw>=size/2 ? raw-size : raw;
   auto left=Integer::fromBits(sign,w,raw);
   for(unsigned target=1;target<=10;++target)for(auto targetSign:{Sign::Signed,Sign::Unsigned})
    check(left.cast(targetSign,target).bits()==(static_cast<std::uint64_t>(value)&((std::uint64_t(1)<<target)-1)));
   for(unsigned exponent=0;exponent<=8;++exponent) {
    std::int64_t expected=1;
    for(unsigned k=0;k<exponent;++k)expected=sign==Sign::Unsigned ? (expected*value)&mask : expected*value;
    if(sign==Sign::Signed && (expected<minimum || expected>maximum))reject<std::overflow_error>([&]{left.power(exponent);});
    else check(left.power(exponent).bits()==(static_cast<std::uint64_t>(expected)&mask));
   }
   for(std::int64_t other=0;other<size;++other) {
    const auto b=sign==Sign::Signed && other>=size/2 ? other-size : other;
    auto right=Integer::fromBits(sign,w,other);
    check(left.compare(right)==(value<b ? -1 : value>b ? 1 : 0));
    for(auto op:{Op::Add,Op::Subtract,Op::Multiply,Op::Divide,Op::Remainder}) {
     auto run=[&]{return left.binary(op,right);};
     if((op==Op::Divide || op==Op::Remainder) && !b){reject<std::domain_error>(run);continue;}
     if(sign==Sign::Signed && (op==Op::Divide || op==Op::Remainder) && value==minimum && b==-1){reject<std::overflow_error>(run);continue;}
     std::int64_t expected=op==Op::Add ? value+b : op==Op::Subtract ? value-b : op==Op::Multiply ? value*b : op==Op::Divide ? value/b : value%b;
     if(sign==Sign::Signed && (expected<minimum || expected>maximum))reject<std::overflow_error>(run);
     else check(run().bits()==(static_cast<std::uint64_t>(expected)&mask));
    }
   }
  }
 }
 const auto high=std::uint64_t(1)<<63,all=~std::uint64_t(0);
 auto minimum=Integer::fromBits(Sign::Signed,64,high),maximum=Integer::fromBits(Sign::Signed,64,high-1);
 auto minusOne=Integer::fromBits(Sign::Signed,64,all),one=Integer::fromBits(Sign::Signed,64,1);
 reject<std::overflow_error>([&]{minimum.binary(Op::Divide,minusOne);});
 reject<std::overflow_error>([&]{minimum.binary(Op::Remainder,minusOne);});
 reject<std::overflow_error>([&]{minimum.binary(Op::Multiply,minusOne);});
 reject<std::overflow_error>([&]{minimum.binary(Op::Subtract,one);});
 reject<std::overflow_error>([&]{maximum.binary(Op::Add,one);});
 check(minimum.binary(Op::Divide,one).bits()==high);
 check(minimum.binary(Op::Add,maximum).bits()==all);
 check(Integer::fromBits(Sign::Unsigned,64,all).binary(Op::Add,Integer::fromBits(Sign::Unsigned,64,1)).bits()==0);
 check(Integer::fromBits(Sign::Signed,64,all-1).power(63).bits()==high);
 auto tiny=Integer::fromBits(Sign::Signed,1,1);check(tiny.power(3).bits()==1);
 reject<std::overflow_error>([&]{tiny.power(2);});reject<std::overflow_error>([&]{tiny.power(0);});
 reject<std::invalid_argument>([&]{one.binary(Op::Add,Integer::fromBits(Sign::Unsigned,64,1));});
 reject<std::invalid_argument>([&]{one.compare(Integer::fromBits(Sign::Signed,32,1));});
 reject<std::out_of_range>([]{Integer::fromBits(Sign::Signed,0,0);});
 reject<std::out_of_range>([]{Integer::fromBits(Sign::Signed,65,0);});
 reject<std::out_of_range>([]{Integer::fromBits(Sign::Signed,3,8);});
 reject<std::invalid_argument>([]{Integer::fromBits(static_cast<Sign>(9),3,0);});
 std::cout<<"PASS: "<<checks<<" integer value checks.\n";return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
