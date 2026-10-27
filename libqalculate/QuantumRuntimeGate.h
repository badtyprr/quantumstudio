// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_RUNTIME_GATE_H
#define QUANTUM_RUNTIME_GATE_H
#include "QuantumClassicalRealExpression.h"
#include "QuantumNumericalState.h"
#include <string>
namespace QuantumNumerics {
// Parameters are read once, in source order, before modifiers are applied.
// Controls occupy the leading (most-significant) wires; their state is explicit
// so negative controls never discard a phase or require temporary mutations.
class RuntimeGate {
public:
 enum class Kind { X, Y, Z, Phase, GlobalPhase, U3, PublishedU };
 class Value {
  friend class RuntimeGate;
  Kind kind_;std::vector<QuantumClassical::NumericValue> parameters_;
  unsigned controls_;std::uint64_t controlState_;int power_;
  Value(Kind kind,const std::vector<QuantumClassical::NumericValue> &parameters,unsigned controls,std::uint64_t state,int power);
 public:
  unsigned targetCount() const;
  unsigned wireCount() const {return controls_+targetCount();}
  std::size_t activeOffset() const {return controlState_<<targetCount();}
  int power() const {return power_;}
  Value singleApplication() const {return Value(kind_,parameters_,controls_,controlState_,power_<0 ? -1 : 1);}
  // Base matrix includes the integer power, before controls are attached.
  std::vector<Complex> baseMatrix() const;
  std::vector<Complex> matrix() const;
  // Exact backend uses dyadic rationals for the same evaluated binary64 values.
  // This expression contains only internal gate names and generated integers.
  std::string exactBaseExpression() const;
 };
 RuntimeGate(Kind kind,const std::vector<QuantumClassical::RealExpression> &parameters,
             unsigned controls=0,std::uint64_t controlState=0,int power=1);
 RuntimeGate(Kind kind,const std::vector<QuantumClassical::RealExpression> &parameters,
             unsigned controls,std::uint64_t controlState,const QuantumClassical::IntegerExpression &power);
 unsigned targetCount() const;
 unsigned wireCount() const {return controls_+targetCount();}
 void validate(unsigned bits,const QuantumClassical::IntegerStorage &storage) const;
 Value evaluate(std::uint64_t record,unsigned bits,const QuantumClassical::IntegerStorage &storage) const;
private:
 Kind kind_;std::vector<QuantumClassical::RealExpression> parameters_;
 unsigned controls_;std::uint64_t controlState_;int power_;
 std::shared_ptr<const QuantumClassical::IntegerExpression> powerExpression_;
};
}
#endif
