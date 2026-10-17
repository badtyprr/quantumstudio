// GPL-2.0-or-later; see COPYING.
#include "libqalculate/QuantumClassicalIntegerStorage.h"
#include <iostream>
#include <stdexcept>
using namespace QuantumClassical;
using Sign=Integer::Signedness;
unsigned checks=0;
void check(bool ok){++checks;if(!ok)throw std::runtime_error("Integer storage check failed: "+std::to_string(checks));}
template<class E,class F>void reject(F f){bool caught=false;try{f();}catch(const E&){caught=true;}check(caught);}
int main(){try {
 auto machine=IntegerType::machine(Sign::Signed);
 IntegerStorage empty({});check(empty.size()==0);
 reject<std::out_of_range>([&]{empty.read(0);});
 IntegerStorage many(std::vector<IntegerType>(129,machine));
 auto one=TypedInteger::fromBits(machine,1),zero=TypedInteger::fromBits(machine,0);
 many.write(128,one);check(many.read(128).value().bits()==1 && !many.initialized(0));
 reject<std::domain_error>([&]{many.write(128,one.binary(Integer::Operation::Divide,zero));});
 check(many.read(128).value().bits()==1);
 auto snapshot=many;many.clear(128);check(snapshot.read(128).value().bits()==1 && !many.initialized(128));
 for(unsigned width=1;width<=64;++width)for(auto sign:{Sign::Signed,Sign::Unsigned}) {
  auto type=IntegerType::sized(sign,width);IntegerStorage store({type,machine});
  check(store.size()==2 && store.type(0)==type && store.type(1)==machine);
  check(!store.initialized(0));reject<std::domain_error>([&]{store.read(0);});
  auto all=TypedInteger::fromBits(machine,~std::uint64_t(0));store.write(0,all);
  const auto mask=~std::uint64_t(0)>>(64-width);
  check(store.initialized(0) && store.read(0).type()==type && store.read(0).value().bits()==mask);
  check(!store.initialized(1));reject<std::domain_error>([&]{store.read(1);});
  auto fork=store;fork.write(0,TypedInteger::fromBits(machine,0));
  check(store.read(0).value().bits()==mask && fork.read(0).value().bits()==0);
  store.clear(0);check(!store.initialized(0) && fork.initialized(0));
  reject<std::domain_error>([&]{store.read(0);});
  store.write(0,TypedInteger::fromBits(machine,0));check(store.read(0).value().bits()==0);
  reject<std::out_of_range>([&]{store.write(2,all);});
  reject<std::out_of_range>([&]{store.clear(2);});
  reject<std::out_of_range>([&]{store.type(2);});
  reject<std::out_of_range>([&]{store.initialized(2);});
  check(store.read(0).value().bits()==0 && !store.initialized(1));
 }
 std::cout<<"PASS: "<<checks<<" integer storage checks.\n";return 0;
}catch(const std::exception &error){std::cerr<<error.what()<<'\n';return 1;}}
