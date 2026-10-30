// GPL-2.0-or-later; see COPYING.
#include "QuantumExactCircuit.h"
#include "QuantumClassicalIntegerStorage.h"
#include "Calculator.h"
#include "Function.h"
#include <stdexcept>

namespace QuantumExact {
namespace {
using Step=CircuitStep;
void checkpoint() {if(CALCULATOR->aborted())throw std::runtime_error("Exact circuit evaluation cancelled");}
void validate(const std::vector<Step> &steps,unsigned qubits,unsigned bits,unsigned depth,unsigned loopDepth,std::size_t &count,const QuantumClassical::IntegerStorage &variables) {
 for(const auto &step:steps) {
  checkpoint();if(++count>512)throw std::length_error("Exact circuits support at most 512 steps across all bodies");
  if(step.kind==Step::Kind::End)continue;
  if(step.kind==Step::Kind::CopyArray){step.arrayCopy->validate(bits,variables);continue;}
  if(step.kind==Step::Kind::CheckArrayReferences){step.arrayReferences->validate(bits,variables);continue;}
  if(step.kind==Step::Kind::Break || step.kind==Step::Kind::Continue) {
   if(loopDepth==0)throw std::invalid_argument("Break and continue require an enclosing loop");
   continue;
  }
  if(step.kind==Step::Kind::StoreInteger || step.kind==Step::Kind::ClearInteger) {
   if(step.arraySelection) {step.arraySelection->validateWrite(bits,variables);variables.array(step.arraySelection->array()).integerType();}
   else variables.type(step.variableSlot);
   if(step.integerExpression)step.integerExpression->validate(bits,variables);
   continue;
  }
  if(step.kind==Step::Kind::StoreNumeric || step.kind==Step::Kind::ClearNumeric) {
   if(step.arraySelection)step.arraySelection->validateWrite(bits,variables);
   const auto target=step.arraySelection ? variables.array(step.arraySelection->array()).numericType() : variables.numeric().type(step.variableSlot);
   if(step.numericExpression) {
    step.numericExpression->validate(bits,variables);
    if(step.numericExpression->type().kind()==QuantumClassical::NumericType::Kind::Angle && target.kind()!=QuantumClassical::NumericType::Kind::Angle)throw std::invalid_argument("Angles cannot be stored in float variables");
   }
   continue;
  }
  if(step.kind==Step::Kind::Assign) {
   QuantumClassical::validateAssignment(bits,step.wires,*step.expression,variables);continue;
  }
  if(step.wireSelection)step.wireSelection->validate(qubits,bits,variables);
  unsigned targets=0;
  for(unsigned wire:step.wires) {
   if(wire>=qubits)throw std::out_of_range("Exact circuit wire is outside the register");
   if(targets&(1U<<wire))throw std::invalid_argument("Exact circuit wires must be distinct");
   targets|=1U<<wire;
  }
  if(step.kind==Step::Kind::ParameterGate) {
   step.parameterGate->validate(bits,variables);
  } else if(step.kind==Step::Kind::Rotation) {
   step.rotation->validate(bits,variables);
  } else if(step.kind==Step::Kind::Map) {
   if(step.operation->dimension()!=(std::size_t(1)<<step.wires.size()))
    throw std::invalid_argument("Exact operation dimensions do not match its target wires");
  } else if(step.kind==Step::Kind::Measure) {
   if(step.classicalBit>=bits)throw std::out_of_range("Measurement destination is outside the classical register");
  } else if(step.kind==Step::Kind::Readout) {
   for(unsigned bit:step.assignment->bits())if(bit>=bits)throw std::out_of_range("Readout target is outside the classical register");
  } else if(step.kind==Step::Kind::Branch || step.kind==Step::Kind::While || step.kind==Step::Kind::ForRange) {
   if(step.rangeExpression) {
    variables.type(step.variableSlot);step.rangeExpression->validate(bits,variables);
   }
   if(step.expression) {
    if(step.expression->width()!=1)throw std::invalid_argument("Exact control-flow conditions must be one bit");
    step.expression->validate(bits,variables);
   }
   if(depth>=32)throw std::length_error("Exact circuits support at most 32 nested branches/loops");
   if((bits<64 && (step.mask>>bits)) || (step.value&~step.mask))
    throw std::invalid_argument("Branch mask/value is outside the classical register or mask");
   validate(*step.whenTrue,qubits,bits,depth+1,loopDepth+(step.kind==Step::Kind::While || step.kind==Step::Kind::ForRange),count,variables);
   if(step.whenFalse)validate(*step.whenFalse,qubits,bits,depth+1,loopDepth,count,variables);
  }
 }
}
TracePreservingMap runtimeRotation(const QuantumNumerics::RuntimeRotation &rotation,std::uint64_t record,
 unsigned bits,const QuantumClassical::IntegerStorage &variables,const EvaluationOptions &exact) {
 // Floats retain their exact dyadic value; modular angles retain rational pi.
 const std::string text=rotation.typedAngle(record,bits,variables).exactRadians();
 using Axis=QuantumNumerics::RuntimeRotation::Axis;
 const char *name=rotation.axis()==Axis::X ? "Rx" : rotation.axis()==Axis::Y ? "Ry" : "Rz";
 EvaluationOptions options=exact;options.approximation=APPROXIMATION_EXACT;
 // Keep rational-pi phases exponential: fractional powers of -1 obscure
 // conjugate cancellation during exact trace-preservation validation.
 options.complex_number_form=COMPLEX_NUMBER_FORM_EXPONENTIAL;
 // Internal decimal integers and radians are independent of entry preferences.
 options.parse_options=ParseOptions();options.parse_options.angle_unit=ANGLE_UNIT_RADIANS;
 auto matrix=CALCULATOR->calculate(std::string("quantum:")+name+"("+text+")",options);
 return TracePreservingMap({matrix},4,options);
}
TracePreservingMap runtimeGate(const QuantumNumerics::RuntimeGate::Value &gate,const EvaluationOptions &exact) {
 EvaluationOptions options=exact;options.approximation=APPROXIMATION_EXACT;
 // Keep rational-pi phases exponential: fractional powers of -1 obscure
 // conjugate cancellation during exact trace-preservation validation.
 options.complex_number_form=COMPLEX_NUMBER_FORM_EXPONENTIAL;
 options.parse_options=ParseOptions();options.parse_options.angle_unit=ANGLE_UNIT_RADIANS;
 auto base=CALCULATOR->calculate("quantum: "+gate.exactBaseExpression(),options);
 const std::size_t size=std::size_t(1)<<gate.wireCount(),small=std::size_t(1)<<gate.targetCount();
 if(small==1) {auto scalar=base;base.clearMatrix();base.resizeMatrix(1,1,m_zero);*base.getElement(1,1)=scalar;}
 if(!base.isMatrix() || base.rows()!=small || base.columns()!=small)throw std::runtime_error("Runtime gate did not produce its declared matrix");
 MathStructure matrix;matrix.clearMatrix();matrix.resizeMatrix(size,size,m_zero);
 for(std::size_t k=1;k<=size;++k)*matrix.getElement(k,k)=m_one;
 for(std::size_t r=1;r<=small;++r)for(std::size_t c=1;c<=small;++c)
  *matrix.getElement(gate.activeOffset()+r,gate.activeOffset()+c)=*base.getElement(r,c);
 return TracePreservingMap({matrix},size*size,options);
}
MathStructure apply(const MathStructure &rho,const Step &step,const EvaluationOptions &exact,const std::vector<unsigned> &targets) {
 if(step.operation->dimension()==1)return rho; // A complete scalar channel is identity on the state.
 auto function=CALCULATOR->getFunction("qapply");if(!function)throw std::runtime_error("Exact gate application is unavailable");
 MathStructure wires;wires.clearVector();for(unsigned wire:targets)wires.addChild(MathStructure(static_cast<int>(wire)));
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
enum class Flow { Normal, Break, Continue, End };
struct RuntimeRecord {
 std::uint64_t bits;
 QuantumClassical::IntegerStorage variables;
 MathStructure density;
 Flow flow=Flow::Normal;
};
using RuntimeRecords=std::vector<RuntimeRecord>;
// All records in a run share a fixed declaration table. A key therefore needs
// the pending transfer, packed record and each slot's initialized flag and bit pattern.
class RuntimeAccumulator {
 unsigned qubits_,bits_;std::size_t maxCells_;const EvaluationOptions &exact_;
 std::map<std::vector<std::uint64_t>,RuntimeRecord> records_;
public:
 RuntimeAccumulator(unsigned qubits,unsigned bits,std::size_t maxCells,const EvaluationOptions &exact):
  qubits_(qubits),bits_(bits),maxCells_(maxCells),exact_(exact) {}
 void add(std::uint64_t bits,const QuantumClassical::IntegerStorage &variables,const MathStructure &density,Flow flow=Flow::Normal) {
  checkpoint();std::vector<std::uint64_t> key={bits,static_cast<std::uint64_t>(flow)};
  for(std::size_t slot=0;slot<variables.size();++slot) {
   const bool initialized=variables.initialized(slot);key.push_back(initialized);
   key.push_back(initialized ? variables.read(slot).value().bits() : 0);
  }
  for(std::size_t slot=0;slot<variables.numeric().size();++slot) {
   const bool initialized=variables.numeric().initialized(slot);key.push_back(initialized);
   key.push_back(initialized ? variables.numeric().read(slot).bits() : 0);
  }
  auto found=records_.find(key);
  RecordAccumulator sum(qubits_,bits_,maxCells_,exact_);
  if(found!=records_.end())sum.add(bits,found->second.density);
  sum.add(bits,density);auto merged=sum.take();
  if(merged.empty())return;
  if(found==records_.end()) {
   const std::size_t cells=(std::size_t(1)<<qubits_)*(std::size_t(1)<<qubits_);
   if(records_.size()>=maxCells_/cells || (variables.totalSize() && records_.size()>=maxCells_/variables.totalSize()))throw std::length_error("Exact variable record cell budget exceeded");
   records_.emplace(std::move(key),RuntimeRecord{bits,variables,merged.begin()->second,flow});
  } else found->second.density=merged.begin()->second;
 }
 RuntimeRecords take() {
  RuntimeRecords result;result.reserve(records_.size());
  for(auto &item:records_)result.push_back(std::move(item.second));
  records_.clear();return result;
 }
};
RuntimeRecords execute(RuntimeRecords records,unsigned qubits,unsigned bits,const std::vector<Step> &steps,
 std::size_t maxCells,const EvaluationOptions &exact,std::size_t &loopConditionsLeft) {
 for(const auto &step:steps) {
  if(step.kind==Step::Kind::ForRange) {
   RuntimeAccumulator finished(qubits,bits,maxCells,exact);
   // Different incoming histories may capture different ranges. Execute each
   // cursor separately: merging their descendants early would lose hidden
   // iteration state even when visible bits and variable slots match.
   for(const auto &incoming:records) {
    checkpoint();
    if(incoming.flow!=Flow::Normal) {
     finished.add(incoming.bits,incoming.variables,incoming.density,incoming.flow);continue;
    }
    auto cursor=step.rangeExpression->evaluate(incoming.bits,bits,incoming.variables);
    RuntimeRecords pending={incoming};
    while(!pending.empty()) {
     RuntimeAccumulator active(qubits,bits,maxCells,exact);
     for(const auto &record:pending) {
      checkpoint();
      if(loopConditionsLeft==0)throw std::length_error("Exact loop condition budget exceeded");
      --loopConditionsLeft;
      auto variables=record.variables;variables.clear(step.variableSlot);
      if(!cursor.hasValue()) {finished.add(record.bits,variables,record.density);continue;}
      variables.write(step.variableSlot,QuantumClassical::TypedInteger::fromBits(step.rangeExpression->type(),cursor.value().bits()));
      active.add(record.bits,variables,record.density);
     }
     auto body=execute(active.take(),qubits,bits,*step.whenTrue,maxCells,exact,loopConditionsLeft);
     RuntimeAccumulator next(qubits,bits,maxCells,exact);
     for(const auto &record:body) {
      if(record.flow==Flow::End || record.flow==Flow::Break) {
       auto variables=record.variables;variables.clear(step.variableSlot);
       finished.add(record.bits,variables,record.density,record.flow==Flow::End ? Flow::End : Flow::Normal);
      } else next.add(record.bits,record.variables,record.density);
     }
     pending=next.take();
     if(!pending.empty())cursor.advance();
    }
   }
   records=finished.take();continue;
  }
  if(step.kind==Step::Kind::While) {
   RuntimeAccumulator finished(qubits,bits,maxCells,exact);
   while(!records.empty()) {
    checkpoint();RuntimeAccumulator active(qubits,bits,maxCells,exact);
    for(const auto &record:records) {
     checkpoint();
     // A transfer from an earlier branch bypasses this entire nested loop.
     if(record.flow!=Flow::Normal) {
      finished.add(record.bits,record.variables,record.density,record.flow);continue;
     }
     if(loopConditionsLeft==0)throw std::length_error("Exact loop condition budget exceeded");
     --loopConditionsLeft;
     auto &destination=step.expression->evaluate(record.bits,bits,record.variables) ? active : finished;
     destination.add(record.bits,record.variables,record.density);
    }
    // Finished histories never re-enter the body. Active histories merge only
    // at the same loop boundary and only with matching variable state.
    auto body=execute(active.take(),qubits,bits,*step.whenTrue,maxCells,exact,loopConditionsLeft);
    RuntimeAccumulator next(qubits,bits,maxCells,exact);
    for(const auto &record:body) {
     if(record.flow==Flow::End) {
      finished.add(record.bits,record.variables,record.density,Flow::End);continue;
     }
     // Only this loop consumes transfers from its own body. Continue and
     // fallthrough share the next condition boundary; break leaves the loop.
     auto &destination=record.flow==Flow::Break ? finished : next;
     destination.add(record.bits,record.variables,record.density);
    }
    records=next.take();
   }
   records=finished.take();continue;
  }
  checkpoint();RuntimeAccumulator output(qubits,bits,maxCells,exact);
  for(const auto &record:records) {
   checkpoint();
   if(record.flow!=Flow::Normal) {
    output.add(record.bits,record.variables,record.density,record.flow);continue;
   }
   const auto wires=step.wireSelection ? step.wireSelection->evaluate(record.bits,bits,record.variables) : step.wires;
   if(step.kind==Step::Kind::End) {
    output.add(record.bits,record.variables,record.density,Flow::End);
   } else if(step.kind==Step::Kind::Break || step.kind==Step::Kind::Continue) {
    output.add(record.bits,record.variables,record.density,step.kind==Step::Kind::Break ? Flow::Break : Flow::Continue);
   } else if(step.kind==Step::Kind::Measure) {
    for(const auto &outcome:measure({{record.bits,record.density}},qubits,bits,wires[0],step.classicalBit,maxCells,exact))
     output.add(outcome.first,record.variables,outcome.second);
   } else if(step.kind==Step::Kind::Branch) {
    const bool selected=step.expression ? step.expression->evaluate(record.bits,bits,record.variables)!=0 : (record.bits&step.mask)==step.value;
    const auto &body=selected ? *step.whenTrue : *step.whenFalse;
    for(const auto &result:execute({record},qubits,bits,body,maxCells,exact,loopConditionsLeft))
     output.add(result.bits,result.variables,result.density,result.flow);
   } else if(step.kind==Step::Kind::CopyArray) {
    auto variables=record.variables;step.arrayCopy->execute(record.bits,bits,variables);
    output.add(record.bits,variables,record.density);
   } else if(step.kind==Step::Kind::CheckArrayReferences) {
    step.arrayReferences->evaluate(record.bits,bits,record.variables);
    output.add(record.bits,record.variables,record.density);
   } else if(step.kind==Step::Kind::StoreInteger || step.kind==Step::Kind::ClearInteger) {
    auto variables=record.variables;
    if(step.kind==Step::Kind::ClearInteger)variables.clear(step.variableSlot);
    else {
     const auto slot=step.arraySelection ? step.arraySelection->evaluate(record.bits,bits,record.variables) : step.variableSlot;
     variables.write(slot,step.integerExpression->evaluate(record.bits,bits,record.variables));
    }
    output.add(record.bits,variables,record.density);
   } else if(step.kind==Step::Kind::StoreNumeric || step.kind==Step::Kind::ClearNumeric) {
    auto variables=record.variables;
    if(step.kind==Step::Kind::ClearNumeric)variables.numeric().clear(step.variableSlot);
    else {
     const auto slot=step.arraySelection ? step.arraySelection->evaluate(record.bits,bits,record.variables) : step.variableSlot;
     variables.numeric().write(slot,step.numericExpression->evaluateTyped(record.bits,bits,record.variables));
    }
    output.add(record.bits,variables,record.density);
   } else if(step.kind==Step::Kind::Assign) {
    output.add(QuantumClassical::assign(record.bits,bits,wires,*step.expression,record.variables),record.variables,record.density);
   } else if(step.kind==Step::Kind::Readout) {
    for(const auto &outcome:step.assignment->outcomes(record.bits)) {
     MathStructure rho=record.density;
     for(std::size_t r=1;r<=rho.rows();++r) {
      checkpoint();for(std::size_t c=1;c<=rho.columns();++c) {
       auto &cell=*rho.getElement(r,c);cell*=outcome.second;cell.eval(exact);
      }
     }
     output.add(outcome.first,record.variables,rho);
    }
   } else if(step.kind==Step::Kind::ParameterGate) {
    const auto value=step.parameterGate->evaluate(record.bits,bits,record.variables);
    auto density=record.density;
    if(value.power()!=0) {
     const auto map=runtimeGate(value.singleApplication(),exact);
     const auto application=Step::map(map,wires);
     for(int k=0;k<std::abs(value.power());++k){checkpoint();density=apply(density,application,exact,wires);}
    }
    output.add(record.bits,record.variables,density);
   } else if(step.kind==Step::Kind::Rotation) {
    const auto map=runtimeRotation(*step.rotation,record.bits,bits,record.variables,exact);
    output.add(record.bits,record.variables,apply(record.density,Step::map(map,wires),exact,wires));
   } else if(step.kind==Step::Kind::Map) output.add(record.bits,record.variables,apply(record.density,step,exact,wires));
   else {
    auto reset=CALCULATOR->getFunction("qreset");if(!reset)throw std::runtime_error("Exact reset is unavailable");
    MathStructure wire(static_cast<int>(wires[0])),result;
    result.set(reset,&record.density,&wire,NULL);result.eval(exact);checkpoint();
    output.add(record.bits,record.variables,result);
   }
  }
  records=output.take();
 }
 checkpoint();return records;
}
}
Records evaluateCircuit(unsigned qubits,unsigned classicalBits,const std::vector<Step> &steps,
 std::size_t maxCells,const EvaluationOptions &options) {
 return evaluateCircuit(qubits,classicalBits,steps,{},maxCells,options);
}
Records evaluateCircuit(unsigned qubits,unsigned classicalBits,const std::vector<Step> &steps,
 const std::vector<QuantumClassical::IntegerType> &variableTypes,std::size_t maxCells,const EvaluationOptions &options) {
 return evaluateCircuit(qubits,classicalBits,steps,variableTypes,maxCells,options,1000000);
}
Records evaluateCircuit(unsigned qubits,unsigned classicalBits,const std::vector<Step> &steps,
 const std::vector<QuantumClassical::IntegerType> &variableTypes,std::size_t maxCells,const EvaluationOptions &options,
 std::size_t maxLoopConditions,const std::vector<QuantumClassical::NumericType> &numericTypes,
 const std::vector<QuantumClassical::ArrayDeclaration> &arrays) {
 checkpoint();RecordAccumulator initial(qubits,classicalBits,maxCells,options);
 if(variableTypes.size()>maxCells || numericTypes.size()>maxCells-variableTypes.size())throw std::length_error("Exact variable slot budget exceeded");
 const QuantumClassical::IntegerStorage variables(variableTypes,numericTypes,arrays);
 std::size_t count=0;validate(steps,qubits,classicalBits,0,0,count,variables);
 EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;
 const std::size_t n=std::size_t(1)<<qubits;
 MathStructure rho;rho.clearMatrix();rho.resizeMatrix(n,n,m_zero);*rho.getElement(1,1)=m_one;
 initial.add(0,rho);
 RuntimeRecords input;for(const auto &item:initial.take())input.push_back({item.first,variables,item.second});
 RecordAccumulator output(qubits,classicalBits,maxCells,exact);
 for(const auto &item:execute(std::move(input),qubits,classicalBits,steps,maxCells,exact,maxLoopConditions))output.add(item.bits,item.density);
 return output.take();
}
}
