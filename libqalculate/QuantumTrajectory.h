// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_TRAJECTORY_H
#define QUANTUM_TRAJECTORY_H
#include "QuantumNumericalState.h"
#include "QuantumReadout.h"
#include "QuantumClassical.h"
#include "QuantumClassicalIntegerExpression.h"
#include "QuantumClassicalRangeExpression.h"
#include "QuantumRuntimeRotation.h"
#include "QuantumRuntimeGate.h"
#include <memory>

namespace QuantumNumerics {
class TrajectoryStep {
public:
 enum class Kind { Gate, Measure, Reset, Conditional, Channel, Readout, Branch, Assign, StoreInteger, ClearInteger, While, Break, Continue, End, ForRange, Rotation, ParameterGate, StoreNumeric, ClearNumeric };
 const Kind kind;
 const std::shared_ptr<const QuantumClassical::RealExpression> numericExpression;
 static TrajectoryStep storeNumeric(std::size_t slot,const QuantumClassical::RealExpression &value) {
  return {Kind::StoreNumeric,{},{},0,0,0,{},{},{},{},{},slot,{},{},{},{},std::make_shared<const QuantumClassical::RealExpression>(value)};
 }
 static TrajectoryStep clearNumeric(std::size_t slot){return {Kind::ClearNumeric,{},{},0,0,0,{},{},{},{},{},slot};}
 const std::vector<Complex> matrix;
 const std::vector<std::vector<Complex>> kraus;
 const std::vector<unsigned> wires;
 const unsigned classicalBit;
 const std::uint64_t mask,value;
 const std::shared_ptr<const ReadoutAssignment> assignment;
 const std::shared_ptr<const std::vector<TrajectoryStep>> whenTrue,whenFalse;
 const std::shared_ptr<const QuantumClassical::Bits> expression;
 const std::size_t variableSlot;
 const std::shared_ptr<const QuantumClassical::IntegerExpression> integerExpression;
 const std::shared_ptr<const QuantumClassical::RangeExpression> rangeExpression;
 const std::shared_ptr<const RuntimeRotation> rotation;
 const std::shared_ptr<const RuntimeGate> parameterGate;
 static TrajectoryStep parameterized(const RuntimeGate &operation,const std::vector<unsigned> &wires) {
  if(wires.size()!=operation.wireCount())throw std::invalid_argument("Runtime gate wire count does not match controls and target");
  return {Kind::ParameterGate,{},wires,0,0,0,{},{},{},{},{},0,{},{},{},std::make_shared<const RuntimeGate>(operation)};
 }
 static TrajectoryStep rotate(const RuntimeRotation &operation,unsigned wire) {
  return {Kind::Rotation,{}, {wire},0,0,0,{},{},{},{},{},0,{},{},std::make_shared<const RuntimeRotation>(operation)};
 }
 static TrajectoryStep gate(const std::vector<Complex> &m,const std::vector<unsigned> &w) {return {Kind::Gate,m,w,0,0,0};}
 static TrajectoryStep measure(unsigned wire,unsigned bit) {return {Kind::Measure,{}, {wire},bit,0,0};}
 static TrajectoryStep reset(unsigned wire) {return {Kind::Reset,{}, {wire},0,0,0};}
 static TrajectoryStep conditional(const std::vector<Complex> &m,const std::vector<unsigned> &w,std::uint64_t mask,std::uint64_t value) {return {Kind::Conditional,m,w,0,mask,value};}
 static TrajectoryStep channel(const std::vector<std::vector<Complex>> &operators,const std::vector<unsigned> &w) {return {Kind::Channel,{},w,0,0,0,operators};}
 // Readout targets are classical bits, unlike the quantum wires of other steps.
 static TrajectoryStep readout(const std::vector<std::vector<double>> &probabilities,const std::vector<unsigned> &bits) {return {Kind::Readout,{},bits,0,0,0,{},std::make_shared<ReadoutAssignment>(bits,probabilities)};}
 // A block chooses one body once, even if that body rewrites condition bits.
 static TrajectoryStep branch(std::uint64_t mask,std::uint64_t value,const std::vector<TrajectoryStep> &yes,const std::vector<TrajectoryStep> &no={}) {
  return {Kind::Branch,{}, {},0,mask,value,{}, {},std::make_shared<const std::vector<TrajectoryStep>>(yes),std::make_shared<const std::vector<TrajectoryStep>>(no)};
 }
 // Assignment targets are classical indices ordered least-significant first.
 static TrajectoryStep assign(const std::vector<unsigned> &targets,const QuantumClassical::Bits &value) {
  return {Kind::Assign,{},targets,0,0,0,{},{},{},{},std::make_shared<const QuantumClassical::Bits>(value)};
 }
 static TrajectoryStep branch(const QuantumClassical::Bits &condition,const std::vector<TrajectoryStep> &yes,const std::vector<TrajectoryStep> &no={}) {
  return {Kind::Branch,{},{},0,0,0,{},{},std::make_shared<const std::vector<TrajectoryStep>>(yes),std::make_shared<const std::vector<TrajectoryStep>>(no),std::make_shared<const QuantumClassical::Bits>(condition)};
 }
 // The condition is re-evaluated before every iteration, including the first.
 static TrajectoryStep whileLoop(const QuantumClassical::Bits &condition,const std::vector<TrajectoryStep> &body) {
  return {Kind::While,{},{},0,0,0,{},{},std::make_shared<const std::vector<TrajectoryStep>>(body),{},std::make_shared<const QuantumClassical::Bits>(condition)};
 }
 // Transfer to the nearest enclosing loop; rejected outside loops, even if unreachable.
 static TrajectoryStep breakLoop() {return {Kind::Break,{},{},0,0,0};}
 // The caller reserves a scoped slot for the binding. It is cleared on exit,
 // including empty ranges, break and program termination. Body writes to the
 // binding do not alter the independent cursor's next value.
 static TrajectoryStep forRange(std::size_t slot,const QuantumClassical::RangeExpression &range,const std::vector<TrajectoryStep> &body) {
  return {Kind::ForRange,{},{},0,0,0,{},{},std::make_shared<const std::vector<TrajectoryStep>>(body),{},{},slot,{},std::make_shared<const QuantumClassical::RangeExpression>(range)};
 }
 static TrajectoryStep continueLoop() {return {Kind::Continue,{},{},0,0,0};}
 // Stop this shot at any nesting depth, preserving its saved classical results.
 static TrajectoryStep endProgram() {return {Kind::End,{},{},0,0,0};}
 // Slot identities are resolved by the caller. Store evaluates before conversion/write.
 static TrajectoryStep storeInteger(std::size_t slot,const QuantumClassical::IntegerExpression &value) {
  return {Kind::StoreInteger,{},{},0,0,0,{},{},{},{},{},slot,std::make_shared<const QuantumClassical::IntegerExpression>(value)};
 }
 // Scope entry/re-entry can restore an explicitly undefined value.
 static TrajectoryStep clearInteger(std::size_t slot) {
  return {Kind::ClearInteger,{},{},0,0,0,{},{},{},{},{},slot};
 }
private:
 TrajectoryStep(Kind k,const std::vector<Complex> &m,const std::vector<unsigned> &w,unsigned b,std::uint64_t mask_,std::uint64_t value_,const std::vector<std::vector<Complex>> &operators={},std::shared_ptr<const ReadoutAssignment> readout={},std::shared_ptr<const std::vector<TrajectoryStep>> yes={},std::shared_ptr<const std::vector<TrajectoryStep>> no={},std::shared_ptr<const QuantumClassical::Bits> expr={},std::size_t slot=0,std::shared_ptr<const QuantumClassical::IntegerExpression> integer={},std::shared_ptr<const QuantumClassical::RangeExpression> range={},std::shared_ptr<const RuntimeRotation> rotation_={},std::shared_ptr<const RuntimeGate> parameterGate_={},std::shared_ptr<const QuantumClassical::RealExpression> numeric_={}):kind(k),numericExpression(numeric_),matrix(m),kraus(operators),wires(w),classicalBit(b),mask(mask_),value(value_),assignment(readout),whenTrue(yes),whenFalse(no),expression(expr),variableSlot(slot),integerExpression(integer),rangeExpression(range),rotation(rotation_),parameterGate(parameterGate_) {}
};
// Each shot starts in |0...0> with zero classical memory. Conditions read saved
// measurement bits, not the current quantum wires. Limits: 25 qubits, 64
// classical bits, 4096 total steps (including both branch bodies), 32 nested
// branches/loops and 1000000 shots. byteBudget limits one state;
// caller-owned steps and returned counts require additional storage.
// Channels sample Kraus branches without changing classical memory.
// Readout assignments change recorded classical bits without measuring or
// changing the quantum state. Conditions see these possibly noisy records.
// Output bits follow the
// supplied classical-bit order, first bit most significant. Quantum wire 0 is
// most significant as in StateVector. Cancellation never returns partial counts.
std::map<std::uint64_t,unsigned> sampleTrajectories(unsigned qubits,unsigned classicalBits,
 unsigned shots,std::uint64_t seed,const std::vector<unsigned> &outputBits,
 const std::vector<TrajectoryStep> &steps,std::size_t byteBudget,
 const Cancellation &cancelled=Cancellation());
// Typed slots start undefined independently for every shot. Definitions are fixed
// for the run; assignment converts to the declared type. The caller resolves scopes.
std::map<std::uint64_t,unsigned> sampleTrajectories(unsigned qubits,unsigned classicalBits,
 unsigned shots,std::uint64_t seed,const std::vector<unsigned> &outputBits,
 const std::vector<TrajectoryStep> &steps,const std::vector<QuantumClassical::IntegerType> &variableTypes,
 std::size_t byteBudget,const Cancellation &cancelled=Cancellation());
// A shared per-shot budget counts every while-condition or range-cursor check, including
// false conditions, exhausted ranges and nested loops. Exhaustion throws without partial counts.
// Existing overloads allow 1,000,000 evaluations per shot. Zero permits only
// paths that never reach a loop check. The body remains immutable.
std::map<std::uint64_t,unsigned> sampleTrajectories(unsigned qubits,unsigned classicalBits,
 unsigned shots,std::uint64_t seed,const std::vector<unsigned> &outputBits,
 const std::vector<TrajectoryStep> &steps,const std::vector<QuantumClassical::IntegerType> &variableTypes,
 std::size_t byteBudget,const Cancellation &cancelled,std::size_t maxLoopConditions,
 const std::vector<QuantumClassical::NumericType> &numericTypes={});
}
#endif
