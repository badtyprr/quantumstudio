// GPL-2.0-or-later; see COPYING.
#include "QuantumTrajectory.h"
#include <random>

namespace QuantumNumerics {
std::map<std::uint64_t,unsigned> sampleTrajectories(unsigned qubits,unsigned classicalBits,
 unsigned shots,std::uint64_t seed,const std::vector<unsigned> &outputBits,
 const std::vector<TrajectoryStep> &steps,std::size_t byteBudget,const Cancellation &cancelled) {
 if(qubits>25 || classicalBits>64 || shots>1000000 || steps.size()>4096)
  throw std::length_error("Trajectory sampling supports 25 qubits, 64 classical bits, 1000000 shots and 4096 steps");
 if((std::size_t(1)<<qubits)>byteBudget/sizeof(Complex))throw std::length_error("Trajectory state exceeds its memory budget");
 auto cancel=[&] {if(cancelled && cancelled())throw Cancelled();};cancel();
 std::uint64_t seen=0;
 for(unsigned bit:outputBits) {
  if(bit>=classicalBits)throw std::out_of_range("Output classical bit is outside the register");
  const std::uint64_t mask=std::uint64_t(1)<<bit;
  if(seen&mask)throw std::invalid_argument("Output classical bits must be distinct");
  seen|=mask;
 }
 const std::uint64_t allowed=classicalBits==64 ? ~std::uint64_t(0) : (std::uint64_t(1)<<classicalBits)-1;
 // Validate all operations, including conditional gates whose branch might
 // never run. A tiny state checks local matrices without allocating 2^n here.
 for(const auto &step:steps) {
  cancel();std::uint64_t wireMask=0;
  for(unsigned wire:step.wires) {
   if(wire>=qubits)throw std::out_of_range("Trajectory wire is outside the register");
   const std::uint64_t bit=std::uint64_t(1)<<wire;
   if(wireMask&bit)throw std::invalid_argument("Trajectory gate wires must be distinct");
   wireMask|=bit;
  }
  if(step.kind==TrajectoryStep::Kind::Gate || step.kind==TrajectoryStep::Kind::Conditional) {
   if(step.wires.empty() || step.wires.size()>3)throw std::invalid_argument("Trajectory gate needs one to three wires");
   StateVector probe(step.wires.size(),8*sizeof(Complex));std::vector<unsigned> local;
   for(unsigned k=0;k<step.wires.size();++k)local.push_back(k);
   probe.apply(step.matrix,local,cancelled);
   if((step.mask&~allowed) || (step.value&~step.mask))throw std::invalid_argument("Invalid classical condition mask or value");
  } else if(step.kind==TrajectoryStep::Kind::Measure && step.classicalBit>=classicalBits)
   throw std::out_of_range("Measurement destination is outside the classical register");
 }
 std::mt19937_64 random(seed);
 auto draw=[&] {return (random()>>11)*(1.0/9007199254740992.0);};
 const std::vector<Complex> X={0,1,1,0};std::map<std::uint64_t,unsigned> counts;
 for(unsigned shot=0;shot<shots;++shot) {
  cancel();StateVector state(qubits,byteBudget,cancelled);std::uint64_t bits=0;
  for(const auto &step:steps) {
   cancel();
   if(step.kind==TrajectoryStep::Kind::Gate)state.apply(step.matrix,step.wires,cancelled);
   else if(step.kind==TrajectoryStep::Kind::Conditional) {
    if((bits&step.mask)==step.value)state.apply(step.matrix,step.wires,cancelled);
   } else if(step.kind==TrajectoryStep::Kind::Measure) {
    const std::uint64_t bit=std::uint64_t(1)<<step.classicalBit;
    bits=(bits&~bit)|(state.measure(step.wires[0],draw(),cancelled) ? bit : 0);
   } else if(state.measure(step.wires[0],draw(),cancelled))state.apply(X,step.wires,cancelled);
  }
  std::uint64_t result=0;for(unsigned bit:outputBits)result=(result<<1)|((bits>>bit)&1);
  ++counts[result];
 }
 return counts;
}
}
