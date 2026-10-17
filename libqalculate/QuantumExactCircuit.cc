// GPL-2.0-or-later; see COPYING.
#include "QuantumExactCircuit.h"
#include "Calculator.h"
#include "Function.h"
#include <stdexcept>

namespace QuantumExact {
namespace {
using Step=CircuitStep;
void checkpoint() {if(CALCULATOR->aborted())throw std::runtime_error("Exact circuit evaluation cancelled");}
void validate(const std::vector<Step> &steps,unsigned qubits,unsigned bits,unsigned depth,std::size_t &count) {
 for(const auto &step:steps) {
  checkpoint();if(++count>512)throw std::length_error("Exact circuits support at most 512 steps across all bodies");
  if(step.kind==Step::Kind::Assign) {
   QuantumClassical::assign(0,bits,step.wires,*step.expression);continue;
  }
  unsigned targets=0;
  for(unsigned wire:step.wires) {
   if(wire>=qubits)throw std::out_of_range("Exact circuit wire is outside the register");
   if(targets&(1U<<wire))throw std::invalid_argument("Exact circuit wires must be distinct");
   targets|=1U<<wire;
  }
  if(step.kind==Step::Kind::Map) {
   if(step.operation->dimension()!=(std::size_t(1)<<step.wires.size()))
    throw std::invalid_argument("Exact operation dimensions do not match its target wires");
  } else if(step.kind==Step::Kind::Measure) {
   if(step.classicalBit>=bits)throw std::out_of_range("Measurement destination is outside the classical register");
  } else if(step.kind==Step::Kind::Readout) {
   for(unsigned bit:step.assignment->bits())if(bit>=bits)throw std::out_of_range("Readout target is outside the classical register");
  } else if(step.kind==Step::Kind::Branch) {
   if(step.expression) {
    if(step.expression->width()!=1)throw std::invalid_argument("Exact branch expressions must be one bit");
    step.expression->evaluate(0,bits);
   }
   if(depth>=32)throw std::length_error("Exact circuits support at most 32 nested branches");
   if((bits<64 && (step.mask>>bits)) || (step.value&~step.mask))
    throw std::invalid_argument("Branch mask/value is outside the classical register or mask");
   validate(*step.whenTrue,qubits,bits,depth+1,count);validate(*step.whenFalse,qubits,bits,depth+1,count);
  }
 }
}
MathStructure apply(const MathStructure &rho,const Step &step,const EvaluationOptions &exact) {
 if(step.operation->dimension()==1)return rho; // A complete scalar channel is identity on the state.
 auto function=CALCULATOR->getFunction("qapply");if(!function)throw std::runtime_error("Exact gate application is unavailable");
 MathStructure wires;wires.clearVector();for(unsigned wire:step.wires)wires.addChild(MathStructure(static_cast<int>(wire)));
 const std::size_t n=rho.rows();MathStructure sum;sum.clearMatrix();sum.resizeMatrix(n,n,m_zero);
 for(const auto &op:step.operation->operators()) {
  checkpoint();MathStructure result;result.set(function,&op,&rho,&wires,NULL);result.eval(exact);checkpoint();
  if(!result.isMatrix() || result.rows()!=n || result.columns()!=n)throw std::runtime_error("Exact gate application did not produce a density matrix");
  for(std::size_t r=1;r<=n;++r) {
   checkpoint();for(std::size_t c=1;c<=n;++c)*sum.getElement(r,c)+=*result.getElement(r,c);
  }
 }
 sum.eval(exact);checkpoint();return sum;
}
Records execute(Records records,unsigned qubits,unsigned bits,const std::vector<Step> &steps,
 std::size_t maxCells,const EvaluationOptions &exact) {
 for(const auto &step:steps) {
  checkpoint();
  if(step.kind==Step::Kind::Measure) {
   records=measure(records,qubits,bits,step.wires[0],step.classicalBit,maxCells,exact);continue;
  }
  RecordAccumulator output(qubits,bits,maxCells,exact);
  for(const auto &record:records) {
   checkpoint();
   if(step.kind==Step::Kind::Branch) {
    // Select once for this incoming record; body writes cannot switch paths.
    const bool selected=step.expression ? step.expression->evaluate(record.first,bits)!=0 : (record.first&step.mask)==step.value;
    const auto &body=selected ? *step.whenTrue : *step.whenFalse;
    auto branch=execute({record},qubits,bits,body,maxCells,exact);
    for(const auto &result:branch)output.add(result.first,result.second);
   } else if(step.kind==Step::Kind::Assign) {
    output.add(QuantumClassical::assign(record.first,bits,step.wires,*step.expression),record.second);
   } else if(step.kind==Step::Kind::Readout) {
    for(const auto &outcome:step.assignment->outcomes(record.first)) {
     MathStructure rho=record.second;
     for(std::size_t r=1;r<=rho.rows();++r) {
      checkpoint();for(std::size_t c=1;c<=rho.columns();++c) {
       auto &cell=*rho.getElement(r,c);cell*=outcome.second;cell.eval(exact);
      }
     }
     output.add(outcome.first,rho);
    }
   } else if(step.kind==Step::Kind::Map) output.add(record.first,apply(record.second,step,exact));
   else {
    auto reset=CALCULATOR->getFunction("qreset");if(!reset)throw std::runtime_error("Exact reset is unavailable");
    MathStructure wire(static_cast<int>(step.wires[0])),result;
    result.set(reset,&record.second,&wire,NULL);result.eval(exact);checkpoint();
    output.add(record.first,result);
   }
  }
  records=output.take();
 }
 checkpoint();return records;
}
}
Records evaluateCircuit(unsigned qubits,unsigned classicalBits,const std::vector<Step> &steps,
 std::size_t maxCells,const EvaluationOptions &options) {
 checkpoint();RecordAccumulator initial(qubits,classicalBits,maxCells,options);
 std::size_t count=0;validate(steps,qubits,classicalBits,0,count);
 EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;
 const std::size_t n=std::size_t(1)<<qubits;
 MathStructure rho;rho.clearMatrix();rho.resizeMatrix(n,n,m_zero);*rho.getElement(1,1)=m_one;
 initial.add(0,rho);
 return execute(initial.take(),qubits,classicalBits,steps,maxCells,exact);
}
}
