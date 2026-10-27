// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_EXACT_CIRCUIT_H
#define QUANTUM_EXACT_CIRCUIT_H
#include "QuantumExactRecords.h"
#include "QuantumExactOperation.h"
#include "QuantumExactReadout.h"
#include "QuantumClassical.h"
#include "QuantumClassicalIntegerExpression.h"
#include "QuantumClassicalRangeExpression.h"
#include "QuantumRuntimeRotation.h"
#include "QuantumRuntimeGate.h"
#include "QuantumWireSelection.h"
#include <memory>

namespace QuantumExact {
class CircuitStep {
public:
 enum class Kind { Map, Measure, Reset, Branch, Readout, Assign, StoreInteger, ClearInteger, While, Break, Continue, End, ForRange, Rotation, ParameterGate, StoreNumeric, ClearNumeric };
 const Kind kind;
 const std::shared_ptr<const QuantumNumerics::RuntimeRotation> rotation;
 const std::shared_ptr<const QuantumNumerics::RuntimeGate> parameterGate;
 const std::shared_ptr<const QuantumClassical::RealExpression> numericExpression;
 static CircuitStep storeNumeric(std::size_t slot,const QuantumClassical::RealExpression &value) {
  return {Kind::StoreNumeric,{},0,0,0,{},{},{},{},{},slot,{},{},{},{},std::make_shared<const QuantumClassical::RealExpression>(value)};
 }
 static CircuitStep clearNumeric(std::size_t slot){return {Kind::ClearNumeric,{},0,0,0,{},{},{},{},{},slot};}
 static CircuitStep parameterized(const QuantumNumerics::RuntimeGate &operation,const std::vector<unsigned> &wires) {
  if(wires.size()!=operation.wireCount())throw std::invalid_argument("Runtime gate wire count does not match controls and target");
  return {Kind::ParameterGate,wires,0,0,0,{},{},{},{},{},0,{},{},{},std::make_shared<const QuantumNumerics::RuntimeGate>(operation)};
 }
 static CircuitStep rotate(const QuantumNumerics::RuntimeRotation &operation,unsigned wire) {
  return {Kind::Rotation,{wire},0,0,0,{},{},{},{},{},0,{},{},std::make_shared<const QuantumNumerics::RuntimeRotation>(operation)};
 }
 const std::shared_ptr<const QuantumClassical::WireSelection> wireSelection;
 // Replace fixed targets with a validated runtime selection of the same arity.
 CircuitStep selectWires(const QuantumClassical::WireSelection &selection) const {
  if(!(kind==Kind::Map || kind==Kind::Measure || kind==Kind::Reset || kind==Kind::Rotation || kind==Kind::ParameterGate))throw std::invalid_argument("Only quantum operations accept runtime wire selectors");
  if(wireSelection)throw std::invalid_argument("Nested wire selections are not supported");
  for(unsigned k=0;k<wires.size();++k)if(wires[k]!=k)throw std::invalid_argument("Runtime wire operation must use local ordinal targets");
  if(selection.size()!=wires.size())throw std::invalid_argument("Wire selector count differs from operation arity");
  return CircuitStep(*this,std::make_shared<const QuantumClassical::WireSelection>(selection));
 }
 const std::vector<unsigned> wires;
 const unsigned classicalBit;
 const std::uint64_t mask,value;
 const std::shared_ptr<const TracePreservingMap> operation;
 const std::shared_ptr<const ReadoutAssignment> assignment;
 const std::shared_ptr<const std::vector<CircuitStep>> whenTrue,whenFalse;
 const std::shared_ptr<const QuantumClassical::Bits> expression;
 const std::size_t variableSlot;
 const std::shared_ptr<const QuantumClassical::IntegerExpression> integerExpression;
 const std::shared_ptr<const QuantumClassical::RangeExpression> rangeExpression;
 static CircuitStep map(const TracePreservingMap &op,const std::vector<unsigned> &wires) {
  return {Kind::Map,wires,0,0,0,std::make_shared<const TracePreservingMap>(op)};
 }
 static CircuitStep measure(unsigned wire,unsigned bit) {return {Kind::Measure,{wire},bit,0,0};}
 static CircuitStep reset(unsigned wire) {return {Kind::Reset,{wire},0,0,0};}
 static CircuitStep readout(const ReadoutAssignment &a) {
  return {Kind::Readout,{},0,0,0,{},std::make_shared<const ReadoutAssignment>(a)};
 }
 static CircuitStep branch(std::uint64_t mask,std::uint64_t value,
  const std::vector<CircuitStep> &yes,const std::vector<CircuitStep> &no={}) {
  return {Kind::Branch,{},0,mask,value,{},{},
   std::make_shared<const std::vector<CircuitStep>>(yes),std::make_shared<const std::vector<CircuitStep>>(no)};
 }
 // Assignment wires are classical targets, ordered least-significant first.
 static CircuitStep assign(const std::vector<unsigned> &targets,const QuantumClassical::Bits &value) {
  return {Kind::Assign,targets,0,0,0,{},{},{},{},std::make_shared<const QuantumClassical::Bits>(value)};
 }
 static CircuitStep branch(const QuantumClassical::Bits &condition,
  const std::vector<CircuitStep> &yes,const std::vector<CircuitStep> &no={}) {
  return {Kind::Branch,{},0,0,0,{},{},std::make_shared<const std::vector<CircuitStep>>(yes),
   std::make_shared<const std::vector<CircuitStep>>(no),std::make_shared<const QuantumClassical::Bits>(condition)};
 }
 // Each active measurement history rechecks the condition before each iteration.
 static CircuitStep whileLoop(const QuantumClassical::Bits &condition,const std::vector<CircuitStep> &body) {
  return {Kind::While,{},0,0,0,{},{},std::make_shared<const std::vector<CircuitStep>>(body),{},std::make_shared<const QuantumClassical::Bits>(condition)};
 }
 // Only valid inside a loop; branches preserve the nearest-loop target.
 static CircuitStep breakLoop() {return {Kind::Break,{},0,0,0};}
 // Bounds are captured per incoming history. The caller reserves a scoped
 // binding slot; normal, empty, break and end exits clear it.
 static CircuitStep forRange(std::size_t slot,const QuantumClassical::RangeExpression &range,const std::vector<CircuitStep> &body) {
  return {Kind::ForRange,{},0,0,0,{},{},std::make_shared<const std::vector<CircuitStep>>(body),{},{},slot,{},std::make_shared<const QuantumClassical::RangeExpression>(range)};
 }
 static CircuitStep continueLoop() {return {Kind::Continue,{},0,0,0};}
 // Terminate this history at any depth without discarding its probability mass.
 static CircuitStep endProgram() {return {Kind::End,{},0,0,0};}
 static CircuitStep storeInteger(std::size_t slot,const QuantumClassical::IntegerExpression &value) {
  return {Kind::StoreInteger,{},0,0,0,{},{},{},{},{},slot,std::make_shared<const QuantumClassical::IntegerExpression>(value)};
 }
 static CircuitStep clearInteger(std::size_t slot) {
  return {Kind::ClearInteger,{},0,0,0,{},{},{},{},{},slot};
 }
private:
 CircuitStep(const CircuitStep &other,std::shared_ptr<const QuantumClassical::WireSelection> selection):
  CircuitStep(other.kind,other.wires,other.classicalBit,other.mask,other.value,other.operation,other.assignment,other.whenTrue,other.whenFalse,other.expression,other.variableSlot,other.integerExpression,other.rangeExpression,other.rotation,other.parameterGate,other.numericExpression,selection) {}
 CircuitStep(Kind k,const std::vector<unsigned> &w,unsigned bit,std::uint64_t m,std::uint64_t v,
  std::shared_ptr<const TracePreservingMap> op={},std::shared_ptr<const ReadoutAssignment> a={},
  std::shared_ptr<const std::vector<CircuitStep>> yes={},std::shared_ptr<const std::vector<CircuitStep>> no={},
  std::shared_ptr<const QuantumClassical::Bits> expr={},std::size_t slot=0,
  std::shared_ptr<const QuantumClassical::IntegerExpression> integer={},
  std::shared_ptr<const QuantumClassical::RangeExpression> range={},
  std::shared_ptr<const QuantumNumerics::RuntimeRotation> rotation_={},std::shared_ptr<const QuantumNumerics::RuntimeGate> parameterGate_={},std::shared_ptr<const QuantumClassical::RealExpression> numeric_={},std::shared_ptr<const QuantumClassical::WireSelection> selection={}):
  kind(k),wireSelection(selection),rotation(rotation_),parameterGate(parameterGate_),numericExpression(numeric_),wires(w),classicalBit(bit),mask(m),value(v),operation(op),assignment(a),whenTrue(yes),whenFalse(no),expression(expr),variableSlot(slot),integerExpression(integer),rangeExpression(range) {}
};
// Starts in |0...0><0...0| with zero classical memory. No implicit final
// measurement. Validates every body before execution, including untaken ones.
// Limits: 10 qubits, 64 classical bits, 512 total steps, 32 nested branches/loops.
// maxCells bounds each record map; temporary matrices and symbolic expression
// storage are additional. Cancellation/failure never returns partial records.
// Certificates and expressions belong to the current Calculator context:
// keep its definitions and symbolic assumptions unchanged from operation/
// readout certification through evaluation (the Calculator is not thread-safe).
Records evaluateCircuit(unsigned qubits,unsigned classicalBits,
 const std::vector<CircuitStep> &steps,std::size_t maxCells,const EvaluationOptions &options);
// Variables start undefined. Intermediate branches merge only when all variable
// values and initialization states match. Final records marginalize variables.
// maxCells also bounds the total variable slots across intermediate histories.
Records evaluateCircuit(unsigned qubits,unsigned classicalBits,
 const std::vector<CircuitStep> &steps,const std::vector<QuantumClassical::IntegerType> &variableTypes,
 std::size_t maxCells,const EvaluationOptions &options);
// Loop work is bounded across the entire evaluation, including all measurement
// histories and nested loops. Every condition or range-cursor check consumes
// one unit, including exhausted ranges.
// Existing overloads use 1,000,000 units. Exhaustion throws; no partial probability
// distribution is returned or renormalized. An infinite-support loop may exceed
// this budget even when a sampled trajectory would terminate almost surely.
Records evaluateCircuit(unsigned qubits,unsigned classicalBits,
 const std::vector<CircuitStep> &steps,const std::vector<QuantumClassical::IntegerType> &variableTypes,
 std::size_t maxCells,const EvaluationOptions &options,std::size_t maxLoopConditions,
 const std::vector<QuantumClassical::NumericType> &numericTypes={});
}
#endif
