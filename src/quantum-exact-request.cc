// GPL-2.0-or-later; see COPYING.
#include "quantum-exact-request.h"
#include "quantum-classical-request.h"
#include <libqalculate/Calculator.h>
#include <libqalculate/QuantumExactCircuit.h>
#include <libqalculate/QuantumExactPhaseCircuit.h>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace {
using Step=QuantumExact::CircuitStep;
class Reader {
 const std::string &input;size_t position=8;
public:
 bool parameterGates() const {return input.compare(0,9,"QEXACT11\n")==0;}
 bool rotations() const {return input.compare(0,9,"QEXACT10\n")==0 || parameterGates();}
 bool ranges() const {return input.compare(0,8,"QEXACT9\n")==0 || rotations();}
 bool termination() const {return input.compare(0,8,"QEXACT8\n")==0 || ranges();}
 bool transfers() const {return input.compare(0,8,"QEXACT7\n")==0 || termination();}
 bool loops() const {return input.compare(0,8,"QEXACT6\n")==0 || transfers();}
 bool bitExpressions() const {return input.compare(0,8,"QEXACT5\n")==0 || loops();}
 bool variables() const {return input.compare(0,8,"QEXACT4\n")==0 || bitExpressions();}
 bool typed() const {return input.compare(0,8,"QEXACT3\n")==0 || variables();}
 bool classical() const {return input.compare(0,8,"QEXACT2\n")==0 || typed();}
 explicit Reader(const std::string &value):input(value) {
  if(input.size()>1100000 || (input.compare(0,8,"QEXACT1\n") && !classical()))
   throw std::runtime_error("Expected a bounded QEXACT1 through QEXACT11 request.");
  if(rotations())position=9;
 }
 std::uint64_t integer(std::uint64_t maximum) {
  std::uint64_t value=0;size_t start=position;
  while(position<input.size() && input[position]!='\n') {
   unsigned char c=input[position++];
   if(c<'0' || c>'9' || position-start>20 || value>maximum/10 ||
      (value==maximum/10 && unsigned(c-'0')>maximum%10))
    throw std::runtime_error("Invalid or excessive exact circuit integer.");
   value=value*10+c-'0';
  }
  if(position==start || position==input.size())throw std::runtime_error("Truncated exact circuit integer.");
  ++position;return value;
 }
 std::vector<unsigned> targets(unsigned available,unsigned maximum) {
  unsigned count=static_cast<unsigned>(integer(maximum));std::vector<unsigned> result;
  for(unsigned k=0;k<count;++k) {
   if(!available)throw std::runtime_error("Target register is empty.");
   unsigned target=static_cast<unsigned>(integer(available-1));
   for(unsigned previous:result)if(previous==target)throw std::runtime_error("Targets must be distinct.");
   result.push_back(target);
  }
  return result;
 }
 std::string expression() {
  size_t length=static_cast<size_t>(integer(4096));
  if(!length || length>input.size()-position)throw std::runtime_error("Empty or truncated exact circuit expression.");
  std::string result=input.substr(position,length);position+=length;
  if(result.find('\0')!=std::string::npos)throw std::runtime_error("Expressions cannot contain NUL.");
  return result;
 }
 void end(){if(position!=input.size())throw std::runtime_error("Trailing exact circuit data.");}
};
MathStructure expression(Calculator &calculator,Reader &reader,const EvaluationOptions &exact) {
 auto value=calculator.calculate("quantum: "+reader.expression(),exact);bool failed=false;
 while(calculator.message()) {
  if(calculator.message()->type()==MESSAGE_ERROR)failed=true;
  calculator.nextMessage();
 }
 if(failed)throw std::runtime_error("Exact circuit expression could not be evaluated.");
 return value;
}
Step readStep(Calculator &calculator,Reader &reader,unsigned qubits,unsigned bits,unsigned depth,
 unsigned &total,const EvaluationOptions &exact,const QuantumClassical::IntegerStorage *variables) {
 if(++total>512)throw std::length_error("Exact circuits support at most 512 steps.");
 const unsigned kind=static_cast<unsigned>(reader.integer(reader.parameterGates()?17:reader.rotations()?16:reader.ranges()?15:reader.termination()?14:reader.transfers()?13:reader.loops()?11:(reader.variables()?10:(reader.classical()?8:6))));
 if(kind==17) {
  auto wires=reader.targets(qubits,3);
  return Step::parameterized(QuantumClassicalRequest::parameterGate(reader,bits,*variables),wires);
 }
 if(kind==16) {
  if(!qubits)throw std::out_of_range("Runtime rotation needs a quantum wire.");
  const auto wire=static_cast<unsigned>(reader.integer(qubits-1));
  return Step::rotate(QuantumClassicalRequest::rotation(reader,bits,*variables),wire);
 }
 if(kind==12)return Step::breakLoop();
 if(kind==13)return Step::continueLoop();
 if(kind==14)return Step::endProgram();
 if(kind==15) {
  if(depth>=32)throw std::length_error("Circuit control flow exceeds 32 nesting levels.");
  const auto slot=static_cast<std::size_t>(reader.integer(4095));variables->type(slot);
  auto range=QuantumClassicalRequest::range(reader,bits,*variables);
  const unsigned count=static_cast<unsigned>(reader.integer(512-total));
  std::vector<Step> body;body.reserve(count);
  for(unsigned k=0;k<count;++k)body.push_back(readStep(calculator,reader,qubits,bits,depth+1,total,exact,variables));
  return Step::forRange(slot,range,body);
 }
 if(kind==9 || kind==10) {
  const auto slot=static_cast<std::size_t>(reader.integer(4095));variables->type(slot);
  if(kind==10)return Step::clearInteger(slot);
  unsigned nodes=0;auto value=QuantumClassicalRequest::integerNode(reader,0,nodes,true,reader.bitExpressions());
  value.validate(bits,*variables);return Step::storeInteger(slot,value);
 }
 if(kind==11) {
  if(depth>=32)throw std::length_error("Circuit control flow exceeds 32 nesting levels.");
  auto condition=QuantumClassicalRequest::read(reader,bits,reader.typed(),variables,reader.bitExpressions());
  const unsigned count=static_cast<unsigned>(reader.integer(512-total));
  std::vector<Step> body;body.reserve(count);
  for(unsigned k=0;k<count;++k)body.push_back(readStep(calculator,reader,qubits,bits,depth+1,total,exact,variables));
  return Step::whileLoop(condition,body);
 }
 if(kind==7) {
  auto targets=reader.targets(bits,bits);
  return Step::assign(targets,QuantumClassicalRequest::read(reader,bits,reader.typed(),variables,reader.bitExpressions()));
 }
 if(kind==6 || kind==8) {
  if(depth>=32)throw std::length_error("Exact circuits support at most 32 nested branches.");
  std::uint64_t mask=0,value=0;
  if(kind==6) {mask=reader.integer(std::numeric_limits<std::uint64_t>::max());value=reader.integer(std::numeric_limits<std::uint64_t>::max());}
  auto condition=kind==8 ? QuantumClassicalRequest::read(reader,bits,reader.typed(),variables,reader.bitExpressions()) : QuantumClassical::Bits::constant(1,0);
  std::vector<Step> bodies[2];
  for(auto &body:bodies) {
   unsigned count=static_cast<unsigned>(reader.integer(512-total));
   for(unsigned k=0;k<count;++k)body.push_back(readStep(calculator,reader,qubits,bits,depth+1,total,exact,variables));
  }
  return kind==8 ? Step::branch(condition,bodies[0],bodies[1]) : Step::branch(mask,value,bodies[0],bodies[1]);
 }
 if(kind==5) {
  auto targets=reader.targets(bits,8);
  return Step::readout(QuantumExact::ReadoutAssignment(targets,expression(calculator,reader,exact),exact));
 }
 if(kind==0 || kind==3 || kind==4) {
  std::uint64_t mask=0,value=0;
  if(kind==3) {mask=reader.integer(std::numeric_limits<std::uint64_t>::max());value=reader.integer(std::numeric_limits<std::uint64_t>::max());}
  auto wires=reader.targets(qubits,qubits);
  auto matrix=expression(calculator,reader,exact);
  std::vector<MathStructure> operators;
  if(kind==4) {
   if(!matrix.isVector() || !matrix.size() || matrix.size()>256)
    throw std::runtime_error("A channel requires a vector of 1-256 Kraus matrices.");
   for(size_t k=0;k<matrix.size();++k)operators.push_back(matrix[k]);
  } else operators.push_back(matrix);
  Step map=Step::map(QuantumExact::TracePreservingMap(operators,1048576,exact),wires);
  return kind==3 ? Step::branch(mask,value,{map}) : map;
 }
 if(!qubits)throw std::runtime_error("Measurement or reset requires a quantum wire.");
 unsigned wire=static_cast<unsigned>(reader.integer(qubits-1));
 if(kind==2)return Step::reset(wire);
 if(!bits)throw std::runtime_error("Measurement requires a classical bit.");
 return Step::measure(wire,static_cast<unsigned>(reader.integer(bits-1)));
}
void jsonString(std::ostream &output,const std::string &text) {
 const char *hex="0123456789abcdef";output<<'"';
 for(unsigned char c:text) {
  if(c=='"' || c=='\\')output<<'\\'<<c;
  else if(c<32)output<<"\\u00"<<hex[c>>4]<<hex[c&15];
  else output<<c;
 }
 output<<'"';
}
}
std::string quantumExactRequest(Calculator &calculator,const std::string &input) {
 Reader reader(input);EvaluationOptions exact;exact.approximation=APPROXIMATION_EXACT;
 unsigned qubits=static_cast<unsigned>(reader.integer(10)),bits=static_cast<unsigned>(reader.integer(64));
 std::vector<QuantumClassical::IntegerType> types;
 if(reader.variables()) {
  const auto slots=reader.integer(4096);
  for(std::uint64_t slot=0;slot<slots;++slot)types.push_back(QuantumClassicalRequest::integerType(reader));
 }
 const std::size_t loopBudget=reader.loops()?static_cast<std::size_t>(reader.integer(1000000)):1000000;
 const QuantumClassical::IntegerStorage declarations(types);
 auto selected=reader.targets(bits,bits);
 unsigned count=static_cast<unsigned>(reader.integer(512)),total=0;std::vector<Step> steps;
 for(unsigned k=0;k<count;++k)steps.push_back(readStep(calculator,reader,qubits,bits,0,total,exact,reader.variables()?&declarations:nullptr));
 reader.end();
 PrintOptions print;print.use_unicode_signs=false;print.number_fraction_format=FRACTION_DECIMAL_EXACT;
 std::map<std::uint64_t,std::string> probabilities;
 QuantumExact::PhaseBudget phaseBudget(262144,4096,100000000,[&]{return calculator.aborted();});
 if(!QuantumExact::tryPhaseCircuitWeights(qubits,bits,steps,selected,probabilities,phaseBudget,{262144,1000000,4000000})) {
  auto records=QuantumExact::evaluateCircuit(qubits,bits,steps,types,1048576,exact,loopBudget);
  auto weights=QuantumExact::weights(records,qubits,bits,selected,1048576,exact);
  for(const auto &entry:weights) {
   MathStructure value=entry.second;value.format(print);probabilities.emplace(entry.first,value.print(print));
  }
 }
 std::ostringstream output;output<<"{\"qubits\":"<<qubits<<",\"classical_bits\":"<<bits<<",\"bits\":[";
 for(size_t k=0;k<selected.size();++k){if(k)output<<',';output<<selected[k];}
 output<<"],\"probabilities\":{";bool first=true;
 for(const auto &entry:probabilities) {
  if(!first)output<<',';first=false;
  std::string label;for(size_t k=selected.size();k>0;--k)label+=((entry.first>>(k-1))&1)?'1':'0';
  jsonString(output,label);output<<':';
  jsonString(output,entry.second);
 }
 output<<"}}";return output.str();
}
