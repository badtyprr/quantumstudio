// Audit-only adapter to the existing numerical state API. No SDK execution.
#include "QuantumNumericalState.h"
#include <cmath>
#include <iomanip>
#include <iostream>
#include <string>

int main() {
 try {
  unsigned n, count;
  std::cout << std::setprecision(17);
  while(std::cin >> n >> count) {
   if(n > 8 || count > 1000) throw std::runtime_error("Audit input exceeds bounds");
   QuantumNumerics::StateVector state(n, 4096);
   for(unsigned k = 0; k < count; ++k) {
    std::string name; unsigned a, b; double angle;
    if(!(std::cin >> name >> a >> b >> angle)) throw std::runtime_error("Incomplete operation");
    using C = QuantumNumerics::Complex;
    std::vector<C> gate;
    std::vector<unsigned> wires = {a};
    double c = std::cos(angle / 2), s = std::sin(angle / 2);
    if(name == "Rx") gate = {c, C(0,-s), C(0,-s), c};
    else if(name == "Ry") gate = {c,-s,s,c};
    else if(name == "Rz") gate = {std::polar(1.0,-angle/2),0,0,std::polar(1.0,angle/2)};
    else if(name == "P") gate = {1,0,0,std::polar(1.0,angle)};
    else if(name == "H") {double h = std::sqrt(.5); gate = {h,h,h,-h};}
    else if(name == "X") gate = {0,1,1,0};
    else if(name == "CZ" || name == "CP") {gate = {1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,name == "CZ" ? C(-1) : std::polar(1.0,angle)}; wires.push_back(b);}
    else if(name == "CNOT") {gate = {1,0,0,0,0,1,0,0,0,0,0,1,0,0,1,0}; wires.push_back(b);}
    else throw std::runtime_error("Unknown audit gate");
    state.apply(gate,wires);
   }
   for(std::size_t i = 0; i < state.size(); ++i) std::cout << state.amplitude(i).real() << ' ' << state.amplitude(i).imag() << ' ';
   std::cout << '\n';
  }
 } catch(const std::exception &error) {std::cerr << error.what(); return 1;}
}
