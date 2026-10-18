// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassicalRange.h"
#include <cstdint>
#include <iostream>
#include <stdexcept>
#include <vector>
using QuantumClassical::Integer;
using QuantumClassical::IntegerRange;
using Sign=Integer::Signedness;
unsigned checks=0;
void check(bool ok) {++checks;if(!ok)throw std::runtime_error("Range check failed: "+std::to_string(checks));}
template<class E,class F>void reject(F action) {bool caught=false;try{action();}catch(const E&){caught=true;}check(caught);}
Integer small(Sign sign,unsigned width,int value) {
 return Integer::fromBits(sign,width,static_cast<std::uint64_t>(value)&((std::uint64_t(1)<<width)-1));
}
void sequence(Integer first,Integer last,Integer step,std::vector<std::uint64_t> expected) {
 IntegerRange range(first,last,step);
 for(auto bits:expected) {check(range.hasValue());check(range.value().bits()==bits);range.advance();}
 check(!range.hasValue());
 reject<std::out_of_range>([&]{range.value();});
 reject<std::out_of_range>([&]{range.advance();});
}
int main() {try {
 // Independent mathematical oracle: all arithmetic fits host int; no bit-rank
 // or modular-successor implementation is used to predict the sequence.
 for(unsigned width=1;width<=5;++width)for(auto sign:{Sign::Signed,Sign::Unsigned}) {
  const int low=sign==Sign::Signed ? -(1<<(width-1)) : 0;
  const int high=sign==Sign::Signed ? (1<<(width-1))-1 : (1<<width)-1;
  for(int start=low;start<=high;++start)for(int stop=low;stop<=high;++stop)for(int step=-8;step<=8;++step) {
   if(!step)continue;
   IntegerRange range(small(sign,width,start),small(sign,width,stop),small(Sign::Signed,8,step));
   for(int expected=start;step>0 ? expected<=stop : expected>=stop;expected+=step) {
    check(range.hasValue());check(range.value().bits()==small(sign,width,expected).bits());
    check(range.value().width()==width && range.value().signedness()==sign);range.advance();
   }
   check(!range.hasValue());
  }
 }
 const auto all=~std::uint64_t(0),high=std::uint64_t(1)<<63;
 auto u=[](std::uint64_t n){return Integer::fromBits(Sign::Unsigned,64,n);};
 auto s=[](std::uint64_t n){return Integer::fromBits(Sign::Signed,64,n);};
 sequence(u(all-1),u(all),u(1),{all-1,all});
 sequence(u(1),u(0),s(all),{1,0});
 sequence(s(high-2),s(high-1),u(1),{high-2,high-1});
 sequence(s(high+1),s(high),s(all),{high+1,high});
 sequence(s(high),s(high-1),u(all),{high,high-1});
 sequence(u(0),u(all),u(all),{0,all});
 sequence(s(high-1),s(high),s(high),{high-1,all});
 sequence(u(all),u(0),s(high),{all,high-1});
 sequence(u(3),u(0),u(1),{});
 sequence(u(0),u(3),s(all),{});
 sequence(u(0),u(0),s(high),{0});
 reject<std::invalid_argument>([&]{IntegerRange(u(0),u(1),u(0));});
 reject<std::invalid_argument>([&]{IntegerRange(s(0),u(1),u(1));});
 reject<std::invalid_argument>([&]{IntegerRange(small(Sign::Unsigned,8,0),u(1),u(1));});
 IntegerRange original(u(0),u(2),u(1));auto fork=original;
 auto binding=original.value();binding=u(99);(void)binding;
 original.advance();check(original.value().bits()==1);check(fork.value().bits()==0);
 std::cout<<"PASS: "<<checks<<" integer range checks.\n";
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
