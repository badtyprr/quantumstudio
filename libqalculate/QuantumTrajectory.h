// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_TRAJECTORY_H
#define QUANTUM_TRAJECTORY_H
#include "QuantumNumericalState.h"

namespace QuantumNumerics {
class TrajectoryStep {
public:
 enum class Kind { Gate, Measure, Reset, Conditional };
 const Kind kind;
 const std::vector<Complex> matrix;
 const std::vector<unsigned> wires;
 const unsigned classicalBit;
 const std::uint64_t mask,value;
 static TrajectoryStep gate(const std::vector<Complex> &m,const std::vector<unsigned> &w) {return {Kind::Gate,m,w,0,0,0};}
 static TrajectoryStep measure(unsigned wire,unsigned bit) {return {Kind::Measure,{}, {wire},bit,0,0};}
 static TrajectoryStep reset(unsigned wire) {return {Kind::Reset,{}, {wire},0,0,0};}
 static TrajectoryStep conditional(const std::vector<Complex> &m,const std::vector<unsigned> &w,std::uint64_t mask,std::uint64_t value) {return {Kind::Conditional,m,w,0,mask,value};}
private:
 TrajectoryStep(Kind k,const std::vector<Complex> &m,const std::vector<unsigned> &w,unsigned b,std::uint64_t mask_,std::uint64_t value_):kind(k),matrix(m),wires(w),classicalBit(b),mask(mask_),value(value_) {}
};
// Each shot starts in |0...0> with zero classical memory. Conditions read saved
// measurement bits, not the current quantum wires. Limits: 25 qubits, 64
// classical bits, 4096 steps and 1000000 shots. byteBudget limits one state;
// caller-owned steps and returned counts require additional storage.
// Output bits follow the
// supplied classical-bit order, first bit most significant. Quantum wire 0 is
// most significant as in StateVector. Cancellation never returns partial counts.
std::map<std::uint64_t,unsigned> sampleTrajectories(unsigned qubits,unsigned classicalBits,
 unsigned shots,std::uint64_t seed,const std::vector<unsigned> &outputBits,
 const std::vector<TrajectoryStep> &steps,std::size_t byteBudget,
 const Cancellation &cancelled=Cancellation());
}
#endif
