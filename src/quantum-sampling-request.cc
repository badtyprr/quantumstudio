// GPL-2.0-or-later; see COPYING.
#include "quantum-sampling-request.h"
#include <libqalculate/Calculator.h>
#include <libqalculate/MathStructure.h>
#include <libqalculate/QuantumNumericalState.h>
#include <libqalculate/QuantumTrajectory.h>
#include <cmath>
#include <limits>
#include <sstream>

namespace {
class Reader {
 const std::string &input;
 size_t position = 9; // Version header followed by LF
public:
 bool dynamic() const {return input.compare(0,9,"QSAMPLE2\n")==0;}
 explicit Reader(const std::string &value) : input(value) {
  if(input.size()>1100000 || (input.compare(0,9,"QSAMPLE1\n")!=0 && !dynamic()))
   throw std::runtime_error("Expected a bounded QSAMPLE1 or QSAMPLE2 request.");
 }
 std::uint64_t integer(std::uint64_t maximum) {
  std::uint64_t value=0;size_t start=position;
  while(position<input.size() && input[position]!='\n') {
   unsigned char c=input[position++];
   if(c<'0' || c>'9' || position-start>20 || value>maximum/10 ||
      (value==maximum/10 && static_cast<unsigned>(c-'0')>maximum%10))
    throw std::runtime_error("Invalid or excessive sampling request integer.");
   value=value*10+c-'0';
  }
  if(position==start || position==input.size())throw std::runtime_error("Truncated sampling request integer.");
  ++position;return value;
 }
 std::vector<unsigned> wires(unsigned qubits, unsigned maximum) {
  unsigned count=static_cast<unsigned>(integer(maximum));std::vector<unsigned> result;
  for(unsigned k=0;k<count;++k) {
   if(!qubits)throw std::runtime_error("A zero-qubit state has no wires.");
   unsigned wire=static_cast<unsigned>(integer(qubits-1));
   for(unsigned previous:result)if(wire==previous)throw std::runtime_error("Sampling request wires must be distinct.");
   result.push_back(wire);
  }
  return result;
 }
 std::string expression() {
  size_t length=static_cast<size_t>(integer(4096));
  if(!length || length>input.size()-position)throw std::runtime_error("Empty or truncated gate expression.");
  std::string result=input.substr(position,length);position+=length;
  if(result.find('\0')!=std::string::npos)throw std::runtime_error("Gate expressions cannot contain NUL.");
  return result;
 }
 void end() {if(position!=input.size())throw std::runtime_error("Unexpected trailing sampling request data.");}
};
double component(Number value) {
 if(value.isUndefined() || value.isInfinite(false))
  throw std::runtime_error("Gate entries must be finite numerical values.");
 // Relative precision is undefined around zero (for example cos(pi/2)).
 // An absolute enclosure below the unitary tolerance is safe to round here.
 if(value.isInterval() && !value.intervalToPrecision(12)) {
  double lower=value.lowerEndPoint().floatValue(), upper=value.upperEndPoint().floatValue();
  if(!std::isfinite(lower) || !std::isfinite(upper) || upper<lower || upper-lower>1e-14)
   throw std::runtime_error("Gate interval is too wide for numerical sampling.");
  return lower+(upper-lower)/2;
 }
 double result=value.floatValue();
 if(!std::isfinite(result))throw std::runtime_error("Gate entry is outside the numerical range.");
 return result;
}
struct Gate { std::vector<unsigned> wires;std::vector<QuantumNumerics::Complex> matrix; };
MathStructure evaluate(Calculator &calculator,const std::string &expression) {
 EvaluationOptions numeric;numeric.approximation=APPROXIMATION_APPROXIMATE;
 MathStructure value=calculator.calculate("quantum: "+expression,numeric);
 bool failed=false;
 while(calculator.message()) {
  if(calculator.message()->type()==MESSAGE_ERROR)failed=true;
  calculator.nextMessage();
 }
 if(failed)throw std::runtime_error("Sampling expression could not be evaluated.");
 return value;
}
std::vector<QuantumNumerics::Complex> numericalMatrix(const MathStructure &matrix,size_t dimension) {
 if(!matrix.isMatrix() || matrix.rows()!=dimension || matrix.columns()!=dimension)
  throw std::runtime_error("Sampling matrix dimensions must match its target wires.");
 std::vector<QuantumNumerics::Complex> result;
 for(size_t r=1;r<=dimension;++r)for(size_t c=1;c<=dimension;++c) {
  const MathStructure &cell=*matrix.getElement(r,c);
  if(!cell.isNumber())throw std::runtime_error("Sampling entries must be numerical; assign parameters before sampling.");
  result.emplace_back(component(cell.number().realPart()),component(cell.number().imaginaryPart()));
 }
 return result;
}
Gate readGate(Calculator &calculator,Reader &reader,unsigned qubits) {
 Gate gate;gate.wires=reader.wires(qubits,3);
 if(gate.wires.empty())throw std::runtime_error("A gate needs one to three target wires.");
 gate.matrix=numericalMatrix(evaluate(calculator,reader.expression()),size_t(1)<<gate.wires.size());
 QuantumNumerics::StateVector probe(static_cast<unsigned>(gate.wires.size()),8*sizeof(QuantumNumerics::Complex));
 std::vector<unsigned> local;for(unsigned wire=0;wire<gate.wires.size();++wire)local.push_back(wire);
 probe.apply(gate.matrix,local);
 return gate;
}
QuantumNumerics::TrajectoryStep readChannel(Calculator &calculator,Reader &reader,unsigned qubits) {
 auto wires=reader.wires(qubits,3);
 if(wires.empty())throw std::runtime_error("A channel needs one to three target wires.");
 MathStructure value=evaluate(calculator,reader.expression());
 if(!value.isVector() || value.size()==0 || value.size()>256)
  throw std::runtime_error("A sampled channel needs a vector of 1-256 Kraus matrices.");
 std::vector<std::vector<QuantumNumerics::Complex>> kraus;
 for(size_t k=0;k<value.size();++k)kraus.push_back(numericalMatrix(value[k],size_t(1)<<wires.size()));
 return QuantumNumerics::TrajectoryStep::channel(kraus,wires);
}
QuantumNumerics::TrajectoryStep readAssignment(Calculator &calculator,Reader &reader,unsigned classicalBits) {
 auto bits=reader.wires(classicalBits,8);
 if(bits.empty())throw std::runtime_error("Readout assignment needs one to eight classical bits.");
 const size_t dimension=size_t(1)<<bits.size();
 auto matrix=numericalMatrix(evaluate(calculator,reader.expression()),dimension);
 std::vector<std::vector<double>> probabilities(dimension,std::vector<double>(dimension));
 for(size_t r=0;r<dimension;++r)for(size_t c=0;c<dimension;++c) {
  const auto entry=matrix[r*dimension+c];
  if(entry.imag()!=0)throw std::runtime_error("Readout probabilities must be real.");
  probabilities[r][c]=entry.real();
 }
 return QuantumNumerics::TrajectoryStep::readout(probabilities,bits);
}

}

std::string quantumSamplingRequest(Calculator &calculator,const std::string &input) {
 Reader reader(input);
 unsigned qubits=static_cast<unsigned>(reader.integer(25));
 unsigned shots=static_cast<unsigned>(reader.integer(1000000));
 std::uint64_t seed=reader.integer(std::numeric_limits<std::uint64_t>::max());
 unsigned classicalBits=reader.dynamic()?static_cast<unsigned>(reader.integer(64)):0;
 std::vector<unsigned> measured=reader.wires(reader.dynamic()?classicalBits:qubits,reader.dynamic()?classicalBits:qubits);
 unsigned count=static_cast<unsigned>(reader.integer(4096));
 std::vector<Gate> gates;gates.reserve(count);
 std::vector<QuantumNumerics::TrajectoryStep> steps;steps.reserve(count);
 for(unsigned k=0;k<count;++k) {
  unsigned kind=reader.dynamic()?static_cast<unsigned>(reader.integer(5)):0;
  if(kind==5)steps.push_back(readAssignment(calculator,reader,classicalBits));
  else if(kind==4)steps.push_back(readChannel(calculator,reader,qubits));
  else if(kind==0 || kind==3) {
   std::uint64_t mask=0,value=0;
   if(kind==3) {mask=reader.integer(std::numeric_limits<std::uint64_t>::max());value=reader.integer(std::numeric_limits<std::uint64_t>::max());}
   Gate gate=readGate(calculator,reader,qubits);
   if(!reader.dynamic())gates.push_back(std::move(gate));
   else if(kind==0)steps.push_back(QuantumNumerics::TrajectoryStep::gate(gate.matrix,gate.wires));
   else steps.push_back(QuantumNumerics::TrajectoryStep::conditional(gate.matrix,gate.wires,mask,value));
  } else {
   if(!qubits)throw std::runtime_error("A measurement or reset needs a quantum wire.");
   unsigned wire=static_cast<unsigned>(reader.integer(qubits-1));
   if(kind==1) {
    if(!classicalBits)throw std::runtime_error("A measurement needs a classical bit.");
    unsigned bit=static_cast<unsigned>(reader.integer(classicalBits-1));
    steps.push_back(QuantumNumerics::TrajectoryStep::measure(wire,bit));
   } else steps.push_back(QuantumNumerics::TrajectoryStep::reset(wire));
  }
 }
 reader.end();
 std::map<std::uint64_t,unsigned> counts;
 if(reader.dynamic())counts=QuantumNumerics::sampleTrajectories(qubits,classicalBits,shots,seed,measured,steps,size_t(512)*1024*1024);
 else {
  QuantumNumerics::StateVector state(qubits,size_t(512)*1024*1024);
  for(const Gate &gate:gates)state.apply(gate.matrix,gate.wires);
  counts=state.sampleCounts(shots,measured,seed);
 }
 std::ostringstream output;
 output << "{\"qubits\":" << qubits << ",\"shots\":" << shots << ",\"seed\":\"" << seed << "\",\"wires\":[";
 for(size_t k=0;k<measured.size();++k) {if(k)output << ',';output << measured[k];}
 output << "]";
 if(reader.dynamic())output << ",\"classical_bits\":" << classicalBits;
 output << ",\"counts\":{";
 bool first=true;
 for(const auto &entry:counts) {
  if(!first)output << ',';
  first=false;output << '\"';
  for(size_t bit=measured.size();bit>0;--bit)output << ((entry.first>>(bit-1))&1);
  output << "\":" << entry.second;
 }
 output << "}}";return output.str();
}
