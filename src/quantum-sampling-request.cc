// GPL-2.0-or-later; see COPYING.
#include "quantum-sampling-request.h"
#include "quantum-classical-request.h"
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
 bool copies() const {return input.compare(0,10,"QSAMPLE17\n")==0;}
 bool views() const {return input.compare(0,10,"QSAMPLE16\n")==0 || copies();}
 bool arrays() const {return input.compare(0,10,"QSAMPLE15\n")==0 || views();}
 bool wireSelectors() const {return input.compare(0,10,"QSAMPLE14\n")==0 || arrays();}
 bool numeric() const {return input.compare(0,10,"QSAMPLE13\n")==0 || wireSelectors();}
 bool parameterGates() const {return input.compare(0,10,"QSAMPLE12\n")==0 || numeric();}
 bool rotations() const {return input.compare(0,10,"QSAMPLE11\n")==0 || parameterGates();}
 bool ranges() const {return input.compare(0,10,"QSAMPLE10\n")==0 || rotations();}
 bool termination() const {return input.compare(0,9,"QSAMPLE9\n")==0 || ranges();}
 bool transfers() const {return input.compare(0,9,"QSAMPLE8\n")==0 || termination();}
 bool loops() const {return input.compare(0,9,"QSAMPLE7\n")==0 || transfers();}
 bool bitExpressions() const {return input.compare(0,9,"QSAMPLE6\n")==0 || loops();}
 bool variables() const {return input.compare(0,9,"QSAMPLE5\n")==0 || bitExpressions();}
 bool typed() const {return input.compare(0,9,"QSAMPLE4\n")==0 || variables();}
 bool classical() const {return input.compare(0,9,"QSAMPLE3\n")==0 || typed();}
 bool dynamic() const {return input.compare(0,9,"QSAMPLE2\n")==0 || classical();}
 explicit Reader(const std::string &value) : input(value) {
  if(input.size()>1100000 || (input.compare(0,9,"QSAMPLE1\n")!=0 && !dynamic()))
   throw std::runtime_error("Expected a bounded QSAMPLE1 through QSAMPLE17 request.");
  if(ranges())position=10;
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

QuantumNumerics::TrajectoryStep readStep(Calculator &calculator,Reader &reader,unsigned qubits,unsigned classicalBits,unsigned depth,unsigned &total,const QuantumClassical::IntegerStorage *variables) {
 using Step=QuantumNumerics::TrajectoryStep;
 if(++total>4096)throw std::length_error("Sampling branches exceed 4096 total operations.");
 const unsigned kind=static_cast<unsigned>(reader.integer(reader.copies()?24:reader.views()?23:reader.arrays()?22:reader.wireSelectors()?20:reader.numeric()?19:reader.parameterGates()?17:reader.rotations()?16:reader.ranges()?15:reader.termination()?14:reader.transfers()?13:reader.loops()?11:(reader.variables()?10:(reader.classical()?8:6))));
 if(kind==24)return Step::copyArray(QuantumClassicalRequest::arrayCopy(reader));
 if(kind==23) {
  auto check=QuantumClassicalRequest::arrayReferenceCheck(reader);
  return Step::checkArrayReferences(check);
 }
 if(kind==21 || kind==22) {
  unsigned nodes=0;auto selection=QuantumClassicalRequest::arraySelection(reader,0,nodes);
  selection.validate(classicalBits,*variables);nodes=0;
  if(kind==21) {
   variables->array(selection.array()).integerType();
   auto value=QuantumClassicalRequest::integerNode(reader,0,nodes,true,true,true);
   value.validate(classicalBits,*variables);return Step::storeArray(selection,value);
  }
  variables->array(selection.array()).numericType();
  auto value=QuantumClassicalRequest::realNode(reader,0,nodes,true);
  value.validate(classicalBits,*variables);return Step::storeArray(selection,value);
 }
 if(kind==20) {
  if(depth>=32)throw std::length_error("Runtime wire selection exceeds nesting limits");
  auto selection=QuantumClassicalRequest::wireSelection(reader,qubits,classicalBits,*variables);
  auto operation=readStep(calculator,reader,qubits,classicalBits,depth+1,total,variables);
  return operation.selectWires(selection);
 }
 if(kind==18 || kind==19) {
  const auto slot=static_cast<std::size_t>(reader.integer(4095));variables->numeric().type(slot);
  if(kind==19)return Step::clearNumeric(slot);
  unsigned nodes=0;auto value=QuantumClassicalRequest::realNode(reader,0,nodes,true);
  value.validate(classicalBits,*variables);return Step::storeNumeric(slot,value);
 }
 if(kind==17) {
  auto wires=reader.wires(qubits,3);
  return Step::parameterized(QuantumClassicalRequest::parameterGate(reader,classicalBits,*variables,reader.numeric()),wires);
 }
 if(kind==16) {
  if(!qubits)throw std::out_of_range("Runtime rotation needs a quantum wire.");
  const auto wire=static_cast<unsigned>(reader.integer(qubits-1));
  return Step::rotate(QuantumClassicalRequest::rotation(reader,classicalBits,*variables,reader.numeric()),wire);
 }
 if(kind==12)return Step::breakLoop();
 if(kind==13)return Step::continueLoop();
 if(kind==14)return Step::endProgram();
 if(kind==15) {
  if(depth>=32)throw std::length_error("Circuit control flow exceeds 32 nesting levels.");
  const auto slot=static_cast<std::size_t>(reader.integer(4095));variables->type(slot);
  auto range=QuantumClassicalRequest::range(reader,classicalBits,*variables,reader.numeric());
  const unsigned count=static_cast<unsigned>(reader.integer(4096-total));
  std::vector<Step> body;body.reserve(count);
  for(unsigned k=0;k<count;++k)body.push_back(readStep(calculator,reader,qubits,classicalBits,depth+1,total,variables));
  return Step::forRange(slot,range,body);
 }
 if(kind==9 || kind==10) {
  const auto slot=static_cast<std::size_t>(reader.integer(4095));variables->type(slot);
  if(kind==10)return Step::clearInteger(slot);
  unsigned nodes=0;auto value=QuantumClassicalRequest::integerNode(reader,0,nodes,true,reader.bitExpressions(),reader.numeric());
  value.validate(classicalBits,*variables);return Step::storeInteger(slot,value);
 }
 if(kind==11) {
  if(depth>=32)throw std::length_error("Circuit control flow exceeds 32 nesting levels.");
  auto condition=QuantumClassicalRequest::read(reader,classicalBits,reader.typed(),variables,reader.bitExpressions(),reader.numeric());
  const unsigned count=static_cast<unsigned>(reader.integer(4096-total));
  std::vector<Step> body;body.reserve(count);
  for(unsigned k=0;k<count;++k)body.push_back(readStep(calculator,reader,qubits,classicalBits,depth+1,total,variables));
  return Step::whileLoop(condition,body);
 }
 if(kind==7) {
  auto targets=reader.wires(classicalBits,classicalBits);
  return Step::assign(targets,QuantumClassicalRequest::read(reader,classicalBits,reader.typed(),variables,reader.bitExpressions(),reader.numeric()));
 }
 if(kind==6 || kind==8) {
  if(depth>=32)throw std::length_error("Sampling branches exceed 32 nesting levels.");
  std::uint64_t mask=0,value=0;
  if(kind==6) {mask=reader.integer(std::numeric_limits<std::uint64_t>::max());value=reader.integer(std::numeric_limits<std::uint64_t>::max());}
  auto condition=kind==8 ? QuantumClassicalRequest::read(reader,classicalBits,reader.typed(),variables,reader.bitExpressions(),reader.numeric()) : QuantumClassical::Bits::constant(1,0);
  std::vector<Step> bodies[2];
  for(auto &body:bodies) {
   const unsigned count=static_cast<unsigned>(reader.integer(4096-total));
   body.reserve(count);
   for(unsigned k=0;k<count;++k)body.push_back(readStep(calculator,reader,qubits,classicalBits,depth+1,total,variables));
  }
  return kind==8 ? Step::branch(condition,bodies[0],bodies[1]) : Step::branch(mask,value,bodies[0],bodies[1]);
 }
 if(kind==5)return readAssignment(calculator,reader,classicalBits);
 if(kind==4)return readChannel(calculator,reader,qubits);
 if(kind==0 || kind==3) {
  std::uint64_t mask=0,value=0;
  if(kind==3) {mask=reader.integer(std::numeric_limits<std::uint64_t>::max());value=reader.integer(std::numeric_limits<std::uint64_t>::max());}
  Gate gate=readGate(calculator,reader,qubits);
  return kind==0 ? Step::gate(gate.matrix,gate.wires) : Step::conditional(gate.matrix,gate.wires,mask,value);
 }
 if(!qubits)throw std::runtime_error("A measurement or reset needs a quantum wire.");
 unsigned wire=static_cast<unsigned>(reader.integer(qubits-1));
 if(kind==1) {
  if(!classicalBits)throw std::runtime_error("A measurement needs a classical bit.");
  unsigned bit=static_cast<unsigned>(reader.integer(classicalBits-1));
  return Step::measure(wire,bit);
 }
 return Step::reset(wire);
}

}

std::string quantumSamplingRequest(Calculator &calculator,const std::string &input) {
 Reader reader(input);
 unsigned qubits=static_cast<unsigned>(reader.integer(25));
 unsigned shots=static_cast<unsigned>(reader.integer(1000000));
 std::uint64_t seed=reader.integer(std::numeric_limits<std::uint64_t>::max());
 unsigned classicalBits=reader.dynamic()?static_cast<unsigned>(reader.integer(64)):0;
 std::vector<QuantumClassical::IntegerType> types;
 if(reader.variables()) {
  const auto slots=reader.integer(4096);
  for(std::uint64_t slot=0;slot<slots;++slot)types.push_back(QuantumClassicalRequest::integerType(reader));
 }
 std::vector<QuantumClassical::NumericType> numericTypes;
 if(reader.numeric()) {
  const auto slots=reader.integer(4096-types.size());
  for(std::uint64_t slot=0;slot<slots;++slot)numericTypes.push_back(QuantumClassicalRequest::numericType(reader));
 }
 const auto arrays=QuantumClassicalRequest::arrays(reader);
 const std::size_t loopBudget=reader.loops()?static_cast<std::size_t>(reader.integer(1000000)):1000000;
 const QuantumClassical::IntegerStorage declarations(types,numericTypes,arrays);
 std::vector<unsigned> measured=reader.wires(reader.dynamic()?classicalBits:qubits,reader.dynamic()?classicalBits:qubits);
 unsigned count=static_cast<unsigned>(reader.integer(4096));
 std::vector<Gate> gates;gates.reserve(count);
 std::vector<QuantumNumerics::TrajectoryStep> steps;steps.reserve(count);
 unsigned total=0;
 for(unsigned k=0;k<count;++k) {
  if(reader.dynamic())steps.push_back(readStep(calculator,reader,qubits,classicalBits,0,total,reader.variables()?&declarations:nullptr));
  else gates.push_back(readGate(calculator,reader,qubits));
 }
 reader.end();
 std::map<std::uint64_t,unsigned> counts;
 if(reader.dynamic())counts=QuantumNumerics::sampleTrajectories(qubits,classicalBits,shots,seed,measured,steps,types,size_t(512)*1024*1024,QuantumNumerics::Cancellation(),loopBudget,numericTypes,arrays);
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
