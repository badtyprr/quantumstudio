// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_TRAJECTORY_H
#define QUANTUM_TRAJECTORY_H
#include "QuantumNumericalState.h"
#include "QuantumReadout.h"
#include <memory>

namespace QuantumNumerics {
class TrajectoryStep {
public:
 enum class Kind { Gate, Measure, Reset, Conditional, Channel, Readout, Branch };
 const Kind kind;
 const std::vector<Complex> matrix;
 const std::vector<std::vector<Complex>> kraus;
 const std::vector<unsigned> wires;
 const unsigned classicalBit;
 const std::uint64_t mask,value;
 const std::shared_ptr<const ReadoutAssignment> assignment;
 const std::shared_ptr<const std::vector<TrajectoryStep>> whenTrue,whenFalse;
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
private:
 TrajectoryStep(Kind k,const std::vector<Complex> &m,const std::vector<unsigned> &w,unsigned b,std::uint64_t mask_,std::uint64_t value_,const std::vector<std::vector<Complex>> &operators={},std::shared_ptr<const ReadoutAssignment> readout={},std::shared_ptr<const std::vector<TrajectoryStep>> yes={},std::shared_ptr<const std::vector<TrajectoryStep>> no={}):kind(k),matrix(m),kraus(operators),wires(w),classicalBit(b),mask(mask_),value(value_),assignment(readout),whenTrue(yes),whenFalse(no) {}
};
// Each shot starts in |0...0> with zero classical memory. Conditions read saved
// measurement bits, not the current quantum wires. Limits: 25 qubits, 64
// classical bits, 4096 total steps (including both branch bodies), 32 nested
// branches and 1000000 shots. byteBudget limits one state;
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
}
#endif
