#include "libqalculate/QuantumNumericalState.h"
#include <cmath>
#include <iostream>
#include <random>
#include <limits>
using namespace QuantumNumerics;
namespace {
unsigned checks=0;
void check(bool v){++checks;if(!v)throw std::runtime_error("Numerical sampling regression failed");}
template<class E,class F>void rejects(F f){bool caught=false;try{f();}catch(const E &){caught=true;}check(caught);}
unsigned total(const std::map<std::uint64_t,unsigned> &counts){unsigned n=0;for(auto c:counts)n+=c.second;return n;}
}
int main(){try {
 const double h=std::sqrt(.5);const std::vector<Complex> H={h,h,h,-h},X={0,1,1,0};
 StateVector zero(1,32);check(!zero.measure(0,0));check(!zero.measure(0,.999));
 zero.apply(X,{0});check(zero.measure(0,0));check(zero.amplitude(1)==Complex(1));
 for(double draw:{.1,.9}) {
  StateVector entangled(2,64);entangled.apply(H,{0});entangled.apply({1,0,0,0,0,1,0,0,0,0,0,1,0,0,1,0},{0,1});
  bool outcome=entangled.measure(0,draw);check(outcome==(draw>.5));
  check(entangled.measure(1,1-draw)==outcome);
  check(std::abs(entangled.amplitude(outcome ? 3 : 0)-Complex(1))<1e-12);
  check(std::abs(entangled.normSquared()-1)<1e-12);
 }
 StateVector tiny(1,32);const double epsilon=1e-150;tiny.apply({epsilon,-1,1,epsilon},{0});
 check(!tiny.measure(0,0));check(std::abs(tiny.amplitude(0)-Complex(1))<1e-12);check(tiny.amplitude(1)==Complex(0));
 for(double draw:{.7,.8}) {
  StateVector biased(1,32);biased.apply({std::sqrt(.75),-.5,.5,std::sqrt(.75)},{0});
  check(biased.measure(0,draw)==(draw>.75));check(std::abs(biased.normSquared()-1)<1e-12);
 }
 StateVector coherent(2,64);coherent.apply(H,{0});coherent.apply(H,{1});coherent.apply({1,0,0,Complex(0,1)},{1});
 check(coherent.measure(0,.9));check(std::abs(coherent.amplitude(2)-h)<1e-12);check(std::abs(coherent.amplitude(3)-Complex(0,h))<1e-12);
 for(double draw:{-1.,1.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()})rejects<std::invalid_argument>([&]{coherent.measure(0,draw);});
 rejects<std::out_of_range>([&]{coherent.measure(2,.5);});check(coherent.valid() && std::abs(coherent.normSquared()-1)<1e-12);
 StateVector cancellable(14,262144);cancellable.apply(H,{0});unsigned measurementCalls=0;
 rejects<Cancelled>([&]{cancellable.measure(0,.9,[&]{return ++measurementCalls==3;});});check(cancellable.valid());
 measurementCalls=0;rejects<Cancelled>([&]{cancellable.measure(0,.9,[&]{return ++measurementCalls==8;});});check(!cancellable.valid());
 rejects<std::logic_error>([&]{cancellable.measure(0,.9);});
 StateVector basis(3,128);basis.apply(X,{0});basis.apply(X,{2});
 for(auto test:std::vector<std::pair<std::vector<unsigned>,std::uint64_t>>{{{0,1,2},5},{{2,0,1},6},{{1,0},1},{{1},0},{{},0}}) {
  auto c=basis.sampleCounts(100,test.first,7);check(c.size()==1 && c[test.second]==100);
 }
 check(basis.sampleCounts(0,{0},7).empty());
 rejects<std::length_error>([&]{basis.sampleCounts(1000001,{0},7);});
 rejects<std::out_of_range>([&]{basis.sampleCounts(0,{3},7);});
 rejects<std::invalid_argument>([&]{basis.sampleCounts(10,{0,0},7);});
 rejects<Cancelled>([&]{basis.sampleCounts(10,{0},7,[]{return true;});});
 check(basis.valid() && basis.amplitude(5)==Complex(1));
 StateVector bell(2,64);bell.apply(H,{0});bell.apply({1,0,0,0,0,1,0,0,0,0,0,1,0,0,1,0},{0,1});
 auto counts=bell.sampleCounts(20000,{0,1},1731);
 check(total(counts)==20000 && counts.size()==2 && counts.count(0) && counts.count(3));
 check(std::abs(int(counts[0])-10000)<500);
 check(counts==bell.sampleCounts(20000,{0,1},1731));
 check(counts!=bell.sampleCounts(20000,{0,1},1732));
 // A Bell draw is determined by the top bit of the specified PRNG output.
 std::mt19937_64 engine(1731);unsigned zeros=0;for(unsigned i=0;i<20000;++i)if((engine()>>63)==0)++zeros;
 check(counts[0]==zeros && counts[3]==20000-zeros);
 auto marginal=bell.sampleCounts(20000,{1},1731);check(marginal[0]==counts[0] && marginal[1]==counts[3]);
 check(std::abs(bell.amplitude(0)-h)<1e-12 && std::abs(bell.amplitude(3)-h)<1e-12 && bell.amplitude(1)==Complex(0));
 StateVector product(3,128);double c=std::sqrt(.75),s=.5;
 product.apply({c,Complex(0,-s),Complex(0,-s),c},{0});product.apply(H,{2});
 product.apply({1,0,0,Complex(0,1)},{2});
 auto probabilities=product.sampleCounts(40000,{2,0},91);
 check(total(probabilities)==40000 && probabilities.size()==4);
 for(unsigned i=0;i<4;++i)check(std::abs(probabilities[i]/40000.0-((i&1) ? .125 : .375))<.02);
 StateVector empty(0,16);check(empty.sampleCounts(100,{},1).at(0)==100);
 StateVector large(14,262144);large.apply(H,{0});unsigned calls=0;
 rejects<Cancelled>([&]{large.sampleCounts(100,{0},1,[&]{return ++calls==3;});});
 check(large.valid() && std::abs(large.normSquared()-1)<1e-12);
 calls=0;rejects<Cancelled>([&]{large.apply(X,{13},[&]{return ++calls==3;});});
 rejects<std::logic_error>([&]{large.sampleCounts(100,{0},1);});
 std::cout<<"PASS: "<<checks<<" numerical sampling checks\n";
 }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
