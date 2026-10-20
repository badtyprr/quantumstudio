// GPL-2.0-or-later; see COPYING.
#include "QuantumRuntimeRotation.h"
#include <cmath>
namespace QuantumNumerics {
RuntimeRotation::RuntimeRotation(Axis axis,const QuantumClassical::RealExpression &angle):axis_(axis),angle_(angle) {
 switch(axis) {case Axis::X:case Axis::Y:case Axis::Z:return;}
 throw std::invalid_argument("Unknown runtime rotation axis");
}
void RuntimeRotation::validate(unsigned bits,const QuantumClassical::IntegerStorage &storage) const {
 angle_.validate(bits,storage);
}
std::vector<Complex> RuntimeRotation::matrix(std::uint64_t record,unsigned bits,const QuantumClassical::IntegerStorage &storage) const {
 const double half=angle(record,bits,storage)/2;
 const double c=std::cos(half),s=std::sin(half);
 switch(axis_) {
  case Axis::X:return {c,Complex(0,-s),Complex(0,-s),c};
  case Axis::Y:return {c,-s,s,c};
  case Axis::Z:return {Complex(c,-s),0,0,Complex(c,s)};
 }
 throw std::invalid_argument("Unknown runtime rotation axis");
}
}
