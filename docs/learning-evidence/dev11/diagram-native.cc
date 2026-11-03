// GPL-2.0-or-later; see COPYING.
// Audit-only adapter: execute transcribed gates through the existing product core.
#include "QuantumNumericalState.h"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>
using QuantumNumerics::Complex;
int main() {
 try {
  unsigned n, count;
  while(std::cin >> n >> count) {
   QuantumNumerics::StateVector state(n, 64*1024*1024);
   unsigned record=0;
   for(unsigned k=0;k<count;++k) {
    std::string gate; unsigned a; std::cin >> gate >> a;
    if(gate=="M") {
     unsigned bit; double draw; std::cin >> bit >> draw;
     if(state.measure(a,draw)) record |= 1u<<bit;
     else record &= ~(1u<<bit);
     continue;
    }
    if(gate=="F") {
     unsigned mask,value; std::cin >> mask >> value >> gate;
     if((record&mask)!=value) continue;
    }
    std::vector<Complex> matrix; std::vector<unsigned> wires{a};
    if(gate=="H") {double h=1/std::sqrt(2.0);matrix={h,h,h,-h};}
    else if(gate=="X") matrix={0,1,1,0};
    else if(gate=="Z") matrix={1,0,0,-1};
    else if(gate=="S") matrix={1,0,0,Complex(0,1)};
    else if(gate=="CNOT") {unsigned b;std::cin>>b;wires.push_back(b);matrix={1,0,0,0,0,1,0,0,0,0,0,1,0,0,1,0};}
    else throw std::runtime_error("Unknown audit gate");
    if(!std::cin) throw std::runtime_error("Truncated audit input");
    state.apply(matrix,wires);
   }
   std::cout<<std::setprecision(17)<<"{\"record\":"<<record<<",\"norm\":"<<state.normSquared()<<",\"amplitudes\":[";
   bool comma=false;
   for(std::size_t i=0;i<state.size();++i) {
    auto z=state.amplitude(i);
    if(z!=Complex(0)) {if(comma)std::cout<<',';comma=true;std::cout<<'['<<i<<','<<z.real()<<','<<z.imag()<<']';}
   }
   std::cout<<"]}\n";
  }
 } catch(const std::exception &e) {std::cerr<<e.what();return 1;}
}
