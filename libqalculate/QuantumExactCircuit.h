// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_EXACT_CIRCUIT_H
#define QUANTUM_EXACT_CIRCUIT_H
#include "QuantumExactRecords.h"
#include "QuantumExactOperation.h"
#include "QuantumExactReadout.h"
#include "QuantumClassical.h"
#include "QuantumClassicalIntegerExpression.h"
#include <memory>

namespace QuantumExact {
class CircuitStep {
public:
 enum class Kind { Map, Measure, Reset, Branch, Readout, Assign, StoreInteger, ClearInteger };
 const Kind kind;
 const std::vector<unsigned> wires;
 const unsigned classicalBit;
 const std::uint64_t mask,value;
 const std::shared_ptr<const TracePreservingMap> operation;
 const std::shared_ptr<const ReadoutAssignment> assignment;
 const std::shared_ptr<const std::vector<CircuitStep>> whenTrue,whenFalse;
 const std::shared_ptr<const QuantumClassical::Bits> expression;
 const std::size_t variableSlot;
 const std::shared_ptr<const QuantumClassical::IntegerExpression> integerExpression;
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
 static CircuitStep storeInteger(std::size_t slot,const QuantumClassical::IntegerExpression &value) {
  return {Kind::StoreInteger,{},0,0,0,{},{},{},{},{},slot,std::make_shared<const QuantumClassical::IntegerExpression>(value)};
 }
 static CircuitStep clearInteger(std::size_t slot) {
  return {Kind::ClearInteger,{},0,0,0,{},{},{},{},{},slot};
 }
private:
 CircuitStep(Kind k,const std::vector<unsigned> &w,unsigned bit,std::uint64_t m,std::uint64_t v,
  std::shared_ptr<const TracePreservingMap> op={},std::shared_ptr<const ReadoutAssignment> a={},
  std::shared_ptr<const std::vector<CircuitStep>> yes={},std::shared_ptr<const std::vector<CircuitStep>> no={},
  std::shared_ptr<const QuantumClassical::Bits> expr={},std::size_t slot=0,
  std::shared_ptr<const QuantumClassical::IntegerExpression> integer={}):
  kind(k),wires(w),classicalBit(bit),mask(m),value(v),operation(op),assignment(a),whenTrue(yes),whenFalse(no),expression(expr),variableSlot(slot),integerExpression(integer) {}
};
// Starts in |0...0><0...0| with zero classical memory. No implicit final
// measurement. Validates every body before execution, including untaken ones.
// Limits: 10 qubits, 64 classical bits, 512 total steps, 32 nested branches.
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
}
#endif
