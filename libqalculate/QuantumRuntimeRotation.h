// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_RUNTIME_ROTATION_H
#define QUANTUM_RUNTIME_ROTATION_H
#include "QuantumClassicalRealExpression.h"
#include "QuantumNumericalState.h"
namespace QuantumNumerics {
// A rotation's angle is read at execution time, never during validation.
class RuntimeRotation {
public:
 enum class Axis { X, Y, Z };
 RuntimeRotation(Axis axis,const QuantumClassical::RealExpression &angle);
 Axis axis() const {return axis_;}
 double angle(std::uint64_t record,unsigned bits,const QuantumClassical::IntegerStorage &storage) const {
  return angle_.evaluate(record,bits,storage);
 }
 void validate(unsigned bits,const QuantumClassical::IntegerStorage &storage) const;
 std::vector<Complex> matrix(std::uint64_t record,unsigned bits,const QuantumClassical::IntegerStorage &storage) const;
private:
 Axis axis_;
 QuantumClassical::RealExpression angle_;
};
}
#endif
