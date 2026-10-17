// GPL-2.0-or-later; see COPYING.
#include "quantum-exact-request.h"
#include "quantum-classical-request.h"
#include <libqalculate/Calculator.h>
#include <libqalculate/QuantumExactCircuit.h>
#include <limits>
#include <sstream>
#include <stdexcept>

namespace {
using Step=QuantumExact::CircuitStep;
class Reader {
 const std::string &input;size_t position=8;
public:
 bool typed() const {return input.compare(0,8,"QEXACT3\n")==0;}
 bool classical() const {return input.compare(0,8,"QEXACT2\n")==0 || typed();}
 explicit Reader(const std::string &value):input(value) {
  if(input.size()>1100000 || (input.compare(0,8,"QEXACT1\n") && !classical()))
   throw std::runtime_error("Expected a bounded QEXACT1, QEXACT2 or QEXACT3 request.");
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
 unsigned &total,const EvaluationOptions &exact) {
 if(++total>512)throw std::length_error("Exact circuits support at most 512 steps.");
 const unsigned kind=static_cast<unsigned>(reader.integer(reader.classical()?8:6));
 if(kind==7) {
  auto targets=reader.targets(bits,bits);
  return Step::assign(targets,QuantumClassicalRequest::read(reader,bits,reader.typed()));
 }
 if(kind==6 || kind==8) {
  if(depth>=32)throw std::length_error("Exact circuits support at most 32 nested branches.");
  std::uint64_t mask=0,value=0;
  if(kind==6) {mask=reader.integer(std::numeric_limits<std::uint64_t>::max());value=reader.integer(std::numeric_limits<std::uint64_t>::max());}
  auto condition=kind==8 ? QuantumClassicalRequest::read(reader,bits,reader.typed()) : QuantumClassical::Bits::constant(1,0);
  std::vector<Step> bodies[2];
  for(auto &body:bodies) {
   unsigned count=static_cast<unsigned>(reader.integer(512-total));
   for(unsigned k=0;k<count;++k)body.push_back(readStep(calculator,reader,qubits,bits,depth+1,total,exact));
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
 auto selected=reader.targets(bits,bits);
 unsigned count=static_cast<unsigned>(reader.integer(512)),total=0;std::vector<Step> steps;
 for(unsigned k=0;k<count;++k)steps.push_back(readStep(calculator,reader,qubits,bits,0,total,exact));
 reader.end();
 auto records=QuantumExact::evaluateCircuit(qubits,bits,steps,1048576,exact);
 auto probabilities=QuantumExact::weights(records,qubits,bits,selected,1048576,exact);
 PrintOptions print;print.use_unicode_signs=false;print.number_fraction_format=FRACTION_DECIMAL_EXACT;
 std::ostringstream output;output<<"{\"qubits\":"<<qubits<<",\"classical_bits\":"<<bits<<",\"bits\":[";
 for(size_t k=0;k<selected.size();++k){if(k)output<<',';output<<selected[k];}
 output<<"],\"probabilities\":{";bool first=true;
 for(const auto &entry:probabilities) {
  if(!first)output<<',';first=false;
  std::string label;for(size_t k=selected.size();k>0;--k)label+=((entry.first>>(k-1))&1)?'1':'0';
  jsonString(output,label);output<<':';
  MathStructure value=entry.second;value.format(print);jsonString(output,value.print(print));
 }
 output<<"}}";return output.str();
}
