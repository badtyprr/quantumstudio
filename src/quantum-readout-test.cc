#include "../libqalculate/QuantumReadout.h"
#include <cmath>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <utility>
using QuantumNumerics::ReadoutAssignment;
static unsigned checks=0;
static void check(bool ok) {if(!ok)throw std::runtime_error("Readout check failed: "+std::to_string(checks+1));++checks;}
template<class F> static void rejects(F f) {bool rejected=false;try{f();}catch(const std::exception &){rejected=true;}check(rejected);}
int main(){try {
 ReadoutAssignment identity({0},{{1,0},{0,1}}),flip({0},{{0,1},{1,0}});
 for(std::uint64_t memory=0;memory<16;++memory) {
  check(identity.apply(memory,0)==memory);
  check(flip.apply(memory,std::nextafter(1.,0.))==(memory^1));
 }
 ReadoutAssignment asymmetric({2},{{.75,.25},{.5,.5}});
 check(asymmetric.apply(0,.749)==0);check(asymmetric.apply(0,.75)==4);
 check(asymmetric.apply(4,.499)==0);check(asymmetric.apply(4,.5)==4);
 unsigned ones0=0,ones1=0;
 for(unsigned k=0;k<1000;++k) {ones0+=asymmetric.apply(0,(k+.5)/1000)==4;ones1+=asymmetric.apply(4,(k+.5)/1000)==4;}
 check(ones0==250 && ones1==500);
 // Correlated assignment cannot be represented by two independent flips.
 ReadoutAssignment correlated({3,1},{{.5,0,0,.5},{0,1,0,0},{0,0,1,0},{1,0,0,0}});
 check(correlated.apply(5,0)==5);check(correlated.apply(5,.5)==15);
 check(correlated.apply(7,.9)==7);check(correlated.apply(13,.9)==13);
 check(correlated.apply(15,.9)==5);
 const std::uint64_t high=std::uint64_t(1)<<63;
 ReadoutAssignment highFlip({63},{{0,1},{1,0}});
 check(highFlip.apply(7,0)==(high|7));check(highFlip.apply(high|7,0)==7);
 ReadoutAssignment tiny({0},{{1e-300,1},{0,1}});
 check(tiny.apply(1,0)==1);check(tiny.apply(0,0)==0);check(tiny.apply(0,1e-299)==1);
 std::vector<std::vector<double>> maximum(256,std::vector<double>(256));
 for(unsigned i=0;i<256;++i)maximum[i][255-i]=1;
 ReadoutAssignment eight({7,6,5,4,3,2,1,0},maximum);
 for(unsigned i=0;i<256;++i)check(eight.apply(256+i,.5)==(256+(255-i)));
 rejects([&]{ReadoutAssignment a({},{{1}});});
 rejects([&]{ReadoutAssignment a({0,1,2,3,4,5,6,7,8},{});});
 rejects([&]{ReadoutAssignment a({64},{{1,0},{0,1}});});
 rejects([&]{ReadoutAssignment a({0,0},{});});
 rejects([&]{ReadoutAssignment a({0},{{1,0}});});
 rejects([&]{ReadoutAssignment a({0},{{1},{0,1}});});
 for(double bad:{-1.,2.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()})
  rejects([&]{ReadoutAssignment a({0},{{bad,0},{0,1}});});
 rejects([&]{ReadoutAssignment a({0},{{.2,.2},{0,1}});});
 rejects([&]{ReadoutAssignment a({0},{{1,0},{0,0}});});
 for(double bad:{-1.,1.,std::numeric_limits<double>::infinity(),std::numeric_limits<double>::quiet_NaN()})
  rejects([&]{identity.apply(0,bad);});
 ReadoutAssignment moved(std::move(flip));
 check(moved.apply(0,0)==1);
 rejects([&]{flip.apply(0,0);});
 std::cout<<"PASS: "<<checks<<" classical readout assignment checks\n";
 }catch(const std::exception &e){std::cerr<<e.what()<<'\n';return 1;}}
