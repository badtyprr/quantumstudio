// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassical.h"
#include <iostream>
#include <stdexcept>
#include <utility>
using QuantumClassical::Bits;using QuantumClassical::assign;
using Op=Bits::Binary;
namespace {
unsigned checks=0;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Classical check failed: "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
}
int main(){try {
 for(unsigned width=1;width<=8;++width) {
  const unsigned size=1U<<width,mask=size-1;
  std::vector<unsigned> leftBits,rightBits;
  for(unsigned bit=0;bit<width;++bit){leftBits.push_back(bit);rightBits.push_back(bit+width);}
  auto a=Bits::read(leftBits),b=Bits::read(rightBits);
  const Op operations[]={Op::And,Op::Or,Op::Xor,Op::Equal,Op::NotEqual,Op::Less,Op::LessEqual,Op::Greater,Op::GreaterEqual};
  for(Op op:operations) {
   auto expression=Bits::binary(op,a,b);
   for(unsigned x=0;x<size;++x)for(unsigned y=0;y<size;++y) {
    unsigned expected=op==Op::And ? x&y : op==Op::Or ? x|y : op==Op::Xor ? x^y :
     op==Op::Equal ? x==y : op==Op::NotEqual ? x!=y : op==Op::Less ? x<y : op==Op::LessEqual ? x<=y : op==Op::Greater ? x>y : x>=y;
    check(expression.evaluate(x|(y<<width),width*2)==expected);
   }
  }
  auto negated=Bits::complement(a);
  for(unsigned x=0;x<size;++x)check(negated.evaluate(x,width)==(x^mask));
  for(unsigned shift=0;shift<=65;++shift) {
   auto amount=Bits::constant(7,shift),l=Bits::binary(Op::ShiftLeft,a,amount),r=Bits::binary(Op::ShiftRight,a,amount);
   for(unsigned x=0;x<size;++x) {
    check(l.evaluate(x,width)==(shift>=width ? 0 : (x<<shift)&mask));
    check(r.evaluate(x,width)==(shift>=width ? 0 : x>>shift));
   }
  }
 }
 check(assign(1,3,{1,2},Bits::read({0,1}))==3); // Overlap: 001 -> 011, never 111.
 check(assign(7,3,{0,2},Bits::constant(2,0))==2); // Untargeted bit retained.
 const std::uint64_t high=std::uint64_t(1)<<63,all=~std::uint64_t(0);
 std::vector<unsigned> every;for(unsigned k=0;k<64;++k)every.push_back(k);
 check(Bits::read(every).evaluate(all,64)==all);
 check(Bits::read({63}).evaluate(high,64)==1);
 check(Bits::complement(Bits::constant(64,0)).evaluate(0,0)==all);
 check(Bits::binary(Op::ShiftLeft,Bits::constant(64,1),Bits::constant(64,63)).evaluate(0,0)==high);
 check(Bits::binary(Op::ShiftLeft,Bits::constant(64,1),Bits::constant(64,64)).evaluate(0,0)==0);
 check(Bits::binary(Op::ShiftRight,Bits::constant(64,all),Bits::constant(64,all)).evaluate(0,0)==0);
 check(assign(0,64,{63},Bits::constant(1,1))==high);
 auto original=Bits::read({0});auto copied=std::move(original);
 check(original.evaluate(1,1)==1 && copied.evaluate(1,1)==1);
 reject<std::out_of_range>([]{Bits::constant(0,0);});
 reject<std::out_of_range>([]{Bits::constant(65,0);});
 reject<std::out_of_range>([]{Bits::constant(1,2);});
 reject<std::out_of_range>([]{Bits::read({});});
 reject<std::out_of_range>([]{Bits::read({64});});
 reject<std::out_of_range>([]{Bits::read(std::vector<unsigned>(65,0));});
 reject<std::out_of_range>([]{Bits::read({1}).evaluate(0,1);});
 reject<std::out_of_range>([]{Bits::constant(1,0).evaluate(2,1);});
 reject<std::out_of_range>([]{Bits::constant(1,0).evaluate(0,65);});
 reject<std::invalid_argument>([]{Bits::binary(Op::Xor,Bits::constant(1,0),Bits::constant(2,0));});
 reject<std::invalid_argument>([]{Bits::binary(static_cast<Op>(999),Bits::constant(1,0),Bits::constant(1,0));});
 reject<std::invalid_argument>([]{assign(0,2,{0,0},Bits::constant(2,0));});
 reject<std::invalid_argument>([]{assign(0,2,{0},Bits::constant(2,0));});
 reject<std::out_of_range>([]{assign(0,1,{1},Bits::constant(1,0));});
 reject<std::out_of_range>([]{assign(0,65,{64},Bits::constant(1,0));});
 auto deep=Bits::constant(1,0);for(unsigned k=1;k<32;++k)deep=Bits::complement(deep);
 check(deep.evaluate(0,0)==1);reject<std::length_error>([&]{Bits::complement(deep);});
 auto broad=Bits::constant(1,1);for(unsigned k=0;k<8;++k)broad=Bits::binary(Op::Or,broad,broad);
 check(broad.evaluate(0,0)==1);reject<std::length_error>([&]{Bits::binary(Op::Or,broad,broad);});
 std::cout<<"PASS: "<<checks<<" classical bit-expression checks.\n";return 0;
 }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
