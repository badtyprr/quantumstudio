// GPL-2.0-or-later; see COPYING.
#include "QuantumTrajectory.h"
#include "QuantumClassicalIntegerStorage.h"
#include <random>
#include <functional>

namespace QuantumNumerics {
std::map<std::uint64_t,unsigned> sampleTrajectories(unsigned qubits,unsigned classicalBits,
 unsigned shots,std::uint64_t seed,const std::vector<unsigned> &outputBits,
 const std::vector<TrajectoryStep> &steps,std::size_t byteBudget,const Cancellation &cancelled) {
 return sampleTrajectories(qubits,classicalBits,shots,seed,outputBits,steps,{},byteBudget,cancelled);
}
std::map<std::uint64_t,unsigned> sampleTrajectories(unsigned qubits,unsigned classicalBits,
 unsigned shots,std::uint64_t seed,const std::vector<unsigned> &outputBits,
 const std::vector<TrajectoryStep> &steps,const std::vector<QuantumClassical::IntegerType> &variableTypes,
 std::size_t byteBudget,const Cancellation &cancelled) {
 return sampleTrajectories(qubits,classicalBits,shots,seed,outputBits,steps,variableTypes,byteBudget,cancelled,1000000);
}
std::map<std::uint64_t,unsigned> sampleTrajectories(unsigned qubits,unsigned classicalBits,
 unsigned shots,std::uint64_t seed,const std::vector<unsigned> &outputBits,
 const std::vector<TrajectoryStep> &steps,const std::vector<QuantumClassical::IntegerType> &variableTypes,
 std::size_t byteBudget,const Cancellation &cancelled,std::size_t maxLoopConditions,const std::vector<QuantumClassical::NumericType> &numericTypes,
 const std::vector<QuantumClassical::ArrayDeclaration> &arrays) {
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
 const QuantumClassical::IntegerStorage declarations(variableTypes,numericTypes,arrays);
 unsigned totalSteps=0;
 std::function<void(const std::vector<TrajectoryStep>&,unsigned,unsigned)> validate;
 validate=[&](const std::vector<TrajectoryStep> &block,unsigned depth,unsigned loopDepth) {
 for(const auto &step:block) {
  cancel();
  if(++totalSteps>4096)throw std::length_error("Trajectory control flow exceeds 4096 total steps");
  if(step.kind==TrajectoryStep::Kind::End)continue;
  if(step.kind==TrajectoryStep::Kind::Break || step.kind==TrajectoryStep::Kind::Continue) {
   if(loopDepth==0)throw std::invalid_argument("Break and continue require an enclosing loop");
   continue;
  }
  if(step.kind==TrajectoryStep::Kind::StoreInteger || step.kind==TrajectoryStep::Kind::ClearInteger) {
   if(step.arraySelection) {step.arraySelection->validateWrite(classicalBits,declarations);declarations.array(step.arraySelection->array()).integerType();}
   else declarations.type(step.variableSlot); // Bounds-check targets even in untaken bodies.
   if(step.integerExpression)step.integerExpression->validate(classicalBits,declarations);
   continue;
  }
  if(step.kind==TrajectoryStep::Kind::StoreNumeric || step.kind==TrajectoryStep::Kind::ClearNumeric) {
   if(step.arraySelection)step.arraySelection->validateWrite(classicalBits,declarations);
   const auto target=step.arraySelection ? declarations.array(step.arraySelection->array()).numericType() : declarations.numeric().type(step.variableSlot);
   if(step.numericExpression) {
    step.numericExpression->validate(classicalBits,declarations);
    if(step.numericExpression->type().kind()==QuantumClassical::NumericType::Kind::Angle && target.kind()!=QuantumClassical::NumericType::Kind::Angle)throw std::invalid_argument("Angles cannot be stored in float variables");
   }
   continue;
  }
  if(step.kind==TrajectoryStep::Kind::Assign) {
   QuantumClassical::validateAssignment(classicalBits,step.wires,*step.expression,declarations);continue;
  }
  if(step.kind==TrajectoryStep::Kind::Branch || step.kind==TrajectoryStep::Kind::While || step.kind==TrajectoryStep::Kind::ForRange) {
   if(step.rangeExpression) {
    declarations.type(step.variableSlot);
    step.rangeExpression->validate(classicalBits,declarations);
   }
   if(step.expression) {
    if(step.expression->width()!=1)throw std::invalid_argument("Trajectory control-flow conditions must be one bit");
    step.expression->validate(classicalBits,declarations);
   }
   if(depth>=32)throw std::length_error("Trajectory control flow exceeds 32 nesting levels");
   if((step.mask&~allowed) || (step.value&~step.mask))throw std::invalid_argument("Invalid classical branch mask or value");
   validate(*step.whenTrue,depth+1,loopDepth+(step.kind==TrajectoryStep::Kind::While || step.kind==TrajectoryStep::Kind::ForRange));
   if(step.whenFalse)validate(*step.whenFalse,depth+1,loopDepth);
   continue;
  }
  if(step.wireSelection)step.wireSelection->validate(qubits,classicalBits,declarations);
  std::uint64_t wireMask=0;
  if(step.kind==TrajectoryStep::Kind::Readout) {
   for(unsigned bit:step.wires)if(bit>=classicalBits)
    throw std::out_of_range("Readout target is outside the classical register");
   continue; // The factory has already validated the immutable assignment table.
  }
  for(unsigned wire:step.wires) {
   if(wire>=qubits)throw std::out_of_range("Trajectory wire is outside the register");
   const std::uint64_t bit=std::uint64_t(1)<<wire;
   if(wireMask&bit)throw std::invalid_argument("Trajectory gate wires must be distinct");
   wireMask|=bit;
  }
  if(step.kind==TrajectoryStep::Kind::ParameterGate) {
   step.parameterGate->validate(classicalBits,declarations);
  } else if(step.kind==TrajectoryStep::Kind::Rotation) {
   step.rotation->validate(classicalBits,declarations);
  } else if(step.kind==TrajectoryStep::Kind::Gate || step.kind==TrajectoryStep::Kind::Conditional || step.kind==TrajectoryStep::Kind::Channel) {
   if(step.wires.empty() || step.wires.size()>3)throw std::invalid_argument("Trajectory gate needs one to three wires");
   StateVector probe(step.wires.size(),8*sizeof(Complex));std::vector<unsigned> local;
   for(unsigned k=0;k<step.wires.size();++k)local.push_back(k);
   if(step.kind==TrajectoryStep::Kind::Channel)probe.channel(step.kraus,local,0,cancelled);
   else probe.apply(step.matrix,local,cancelled);
   if((step.mask&~allowed) || (step.value&~step.mask))throw std::invalid_argument("Invalid classical condition mask or value");
  } else if(step.kind==TrajectoryStep::Kind::Measure && step.classicalBit>=classicalBits)
   throw std::out_of_range("Measurement destination is outside the classical register");
 }
 };
 validate(steps,0,0);
 std::mt19937_64 random(seed);
 auto draw=[&] {return (random()>>11)*(1.0/9007199254740992.0);};
 const std::vector<Complex> X={0,1,1,0};std::map<std::uint64_t,unsigned> counts;
 std::size_t loopConditionsLeft=0;
 enum class Flow { Normal, Break, Continue, End };
 std::function<Flow(const std::vector<TrajectoryStep>&,StateVector&,std::uint64_t&,QuantumClassical::IntegerStorage&)> execute;
 execute=[&](const std::vector<TrajectoryStep> &block,StateVector &state,std::uint64_t &bits,QuantumClassical::IntegerStorage &variables) -> Flow {
  for(const auto &step:block) {
   cancel();
   if(step.kind==TrajectoryStep::Kind::Break)return Flow::Break;
   if(step.kind==TrajectoryStep::Kind::Continue)return Flow::Continue;
   if(step.kind==TrajectoryStep::Kind::End)return Flow::End;
   if(step.kind==TrajectoryStep::Kind::ForRange) {
    auto cursor=step.rangeExpression->evaluate(bits,classicalBits,variables);
    variables.clear(step.variableSlot);
    for(;;) {
     cancel();
     if(loopConditionsLeft==0)throw std::length_error("Trajectory loop condition budget exceeded");
     --loopConditionsLeft;
     if(!cursor.hasValue())break;
     variables.write(step.variableSlot,QuantumClassical::TypedInteger::fromBits(step.rangeExpression->type(),cursor.value().bits()));
     const auto flow=execute(*step.whenTrue,state,bits,variables);
     if(flow==Flow::End) {variables.clear(step.variableSlot);return flow;}
     if(flow==Flow::Break)break;
     cursor.advance(); // Continue also advances, even if the body rewrote its binding.
    }
    variables.clear(step.variableSlot);
    continue;
   }
   if(step.kind==TrajectoryStep::Kind::While) {
    for(;;) {
     cancel(); // Empty loop bodies must remain interruptible.
     if(loopConditionsLeft==0)throw std::length_error("Trajectory loop condition budget exceeded");
     --loopConditionsLeft;
     if(!step.expression->evaluate(bits,classicalBits,variables))break;
     const auto flow=execute(*step.whenTrue,state,bits,variables);
     if(flow==Flow::End)return flow; // Program termination crosses every loop.
     if(flow==Flow::Break)break;
     // Normal completion and continue both re-evaluate this loop condition.
    }
    continue;
   }
   if(step.kind==TrajectoryStep::Kind::Branch) {
    const bool condition=step.expression ? step.expression->evaluate(bits,classicalBits,variables)!=0 : (bits&step.mask)==step.value;
    const auto &selected=condition ? *step.whenTrue : *step.whenFalse;
    const auto flow=execute(selected,state,bits,variables);
    if(flow!=Flow::Normal)return flow;
    continue;
   }
   const auto wires=step.wireSelection ? step.wireSelection->evaluate(bits,classicalBits,variables) : step.wires;
   if(step.kind==TrajectoryStep::Kind::StoreInteger) {
    const auto slot=step.arraySelection ? step.arraySelection->evaluate(bits,classicalBits,variables) : step.variableSlot;
    variables.write(slot,step.integerExpression->evaluate(bits,classicalBits,variables));
   }
   else if(step.kind==TrajectoryStep::Kind::ClearInteger)variables.clear(step.variableSlot);
   else if(step.kind==TrajectoryStep::Kind::StoreNumeric) {
    const auto slot=step.arraySelection ? step.arraySelection->evaluate(bits,classicalBits,variables) : step.variableSlot;
    variables.numeric().write(slot,step.numericExpression->evaluateTyped(bits,classicalBits,variables));
   }
   else if(step.kind==TrajectoryStep::Kind::ClearNumeric)variables.numeric().clear(step.variableSlot);
   else if(step.kind==TrajectoryStep::Kind::Assign)bits=QuantumClassical::assign(bits,classicalBits,wires,*step.expression,variables);
   else if(step.kind==TrajectoryStep::Kind::Gate)state.apply(step.matrix,wires,cancelled);
   else if(step.kind==TrajectoryStep::Kind::ParameterGate) {
    auto value=step.parameterGate->evaluate(bits,classicalBits,variables);
    if(value.wireCount())state.apply(value.matrix(),wires,cancelled);
   }
   else if(step.kind==TrajectoryStep::Kind::Rotation)state.apply(step.rotation->matrix(bits,classicalBits,variables),wires,cancelled);
   else if(step.kind==TrajectoryStep::Kind::Conditional) {
    if((bits&step.mask)==step.value)state.apply(step.matrix,wires,cancelled);
   } else if(step.kind==TrajectoryStep::Kind::Channel)state.channel(step.kraus,wires,draw(),cancelled);
   else if(step.kind==TrajectoryStep::Kind::Readout)bits=step.assignment->apply(bits,draw());
   else if(step.kind==TrajectoryStep::Kind::Measure) {
    const std::uint64_t bit=std::uint64_t(1)<<step.classicalBit;
    bits=(bits&~bit)|(state.measure(wires[0],draw(),cancelled) ? bit : 0);
   } else if(state.measure(wires[0],draw(),cancelled))state.apply(X,wires,cancelled);
  }
  return Flow::Normal;
 };
 for(unsigned shot=0;shot<shots;++shot) {
  cancel();StateVector state(qubits,byteBudget,cancelled);std::uint64_t bits=0;
  auto variables=declarations;loopConditionsLeft=maxLoopConditions;
  execute(steps,state,bits,variables);
  std::uint64_t result=0;for(unsigned bit:outputBits)result=(result<<1)|((bits>>bit)&1);
  ++counts[result];
 }
 return counts;
}
}
