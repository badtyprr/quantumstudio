// GPL-2.0-or-later; see COPYING.
#include "QuantumExactPhaseCircuit.h"
#include <algorithm>
#include <stdexcept>
#include <utility>

namespace QuantumExact {
namespace {
struct Entry {std::size_t row;PhasePolynomial value;};
struct Gate {std::vector<unsigned> wires;std::vector<std::vector<Entry>> columns;};
void reserveTerms(std::size_t &used,std::size_t extra,std::size_t limit) {
 if(extra>limit-used)throw std::length_error("Exact phase circuit term budget exceeded");
 used+=extra;
}
void append(std::string &text,const std::string &part,std::size_t limit,PhaseBudget &budget) {
 budget.charge();if(part.size()>limit-text.size())throw std::length_error("Exact phase probability text budget exceeded");
 text+=part;
}
std::string scalarText(const PhasePolynomial &value,PhaseBudget &budget,std::size_t limit) {
 Number scalar;if(!value.rationalConstant(scalar))return value.toExactString(budget,limit);
 // Preserve the worker's short decimal results without a precision-dependent
 // formatter. A reduced rational terminates exactly iff its denominator has
 // no prime factors other than two and five; otherwise retain its fraction.
 Number denominator=scalar.denominator();std::size_t twos=0,fives=0;
 while(denominator.isEven()){budget.charge();denominator/=2;++twos;}
 while(denominator.isIntegerDivisible(Number(5))){budget.charge();denominator/=5;++fives;}
 if(!denominator.isOne())return value.toExactString(budget,limit);
 const std::size_t digits=std::max(twos,fives);Number scaled=scalar.numerator();
 for(std::size_t k=twos;k<digits;++k){budget.charge();scaled*=2;}
 for(std::size_t k=fives;k<digits;++k){budget.charge();scaled*=5;}
 const auto &integer=scaled.internalRational();
 std::vector<char> buffer(mpz_sizeinbase(mpq_numref(integer),10)+3);
 mpz_get_str(buffer.data(),10,mpq_numref(integer));std::string text(buffer.data());
 const bool negative=!text.empty() && text[0]=='-';if(negative)text.erase(0,1);
 if(digits){if(text.size()<=digits)text.insert(0,digits+1-text.size(),'0');text.insert(text.size()-digits,1,'.');}
 if(negative)text.insert(0,1,'-');
 if(text.size()>limit)throw std::length_error("Exact phase probability text budget exceeded");
 return text;
}
std::string probabilityText(const std::vector<PhasePolynomial> &amplitudes,PhaseBudget &budget,std::size_t limit) {
 PhasePolynomial small;std::string large;
 for(const auto &amplitude:amplitudes) {
  budget.charge();
  if(amplitude.termCount()<=8)small=small.plus(amplitude.times(amplitude.conjugated(budget),budget),budget);
  else {
   if(!large.empty())append(large,"+",limit,budget);
   append(large,"abs(",limit,budget);
   append(large,amplitude.toExactString(budget,limit-large.size()),limit,budget);
   append(large,")^2",limit,budget);
  }
 }
 if(small.termCount() || large.empty()) {
  if(!large.empty())append(large,"+",limit,budget);
  append(large,scalarText(small,budget,limit-large.size()),limit,budget);
 }
 return large;
}
}
bool tryPhaseCircuitWeights(unsigned qubits,unsigned bits,const std::vector<CircuitStep> &steps,
 const std::vector<unsigned> &selected,std::map<std::uint64_t,std::string> &output,
 PhaseBudget &budget,const PhaseCircuitLimits &limits) {
 budget.charge();
 if(qubits>10 || bits>64)throw std::out_of_range("Exact phase circuit register width is out of range");
 if(!limits.maxTerms || !limits.maxProbabilityCharacters || !limits.maxTotalCharacters)
  throw std::invalid_argument("Exact phase circuit limits must be positive");
 if(steps.size()>512)throw std::length_error("Exact phase circuits support at most 512 steps");
 std::uint64_t seen=0;
 for(unsigned bit:selected) {
  budget.charge();if(bit>=bits)throw std::out_of_range("Exact phase output bit is outside the register");
  const auto flag=std::uint64_t(1)<<bit;
  if(seen&flag)throw std::invalid_argument("Exact phase output bits must be distinct");seen|=flag;
 }
 std::vector<Gate> gates;std::vector<std::pair<unsigned,unsigned>> measurements;
 // Decide structural eligibility before converting any gates. A later branch
 // or channel must select the general evaluator rather than accidentally hit
 // a phase-conversion limit in an earlier gate.
 for(const auto &step:steps) {
  budget.charge();
  if(step.wireSelection)return false;
  if(step.kind==CircuitStep::Kind::Measure) {
   if(step.wires.size()!=1 || step.wires[0]>=qubits || step.classicalBit>=bits)
    throw std::out_of_range("Exact phase measurement target is outside the register");
   measurements.emplace_back(step.wires[0],step.classicalBit);continue;
  }
  if(step.kind!=CircuitStep::Kind::Map || !measurements.empty() || step.operation->operators().size()!=1)return false;
 }
 std::size_t compiledTerms=0;
 for(const auto &step:steps) {
  budget.charge();if(step.kind==CircuitStep::Kind::Measure)break;
  std::size_t targets=0;
  for(unsigned wire:step.wires) {
   if(wire>=qubits)throw std::out_of_range("Exact phase gate wire is outside the register");
   const auto bit=std::size_t(1)<<wire;
   if(targets&bit)throw std::invalid_argument("Exact phase gate wires must be distinct");targets|=bit;
  }
  const auto dimension=step.operation->dimension();
  if(dimension!=(std::size_t(1)<<step.wires.size()))throw std::invalid_argument("Exact phase gate dimension differs from target wires");
  reserveTerms(compiledTerms,dimension,limits.maxTerms);
  Gate gate{step.wires,std::vector<std::vector<Entry>>(dimension)};
  const auto &matrix=step.operation->operators()[0];
  for(std::size_t column=0;column<dimension;++column)for(std::size_t row=0;row<dimension;++row) {
   budget.charge();PhasePolynomial coefficient;
   if(!PhasePolynomial::tryFromExpression(*matrix.getElement(row+1,column+1),coefficient,budget))return false;
   if(!coefficient.termCount())continue;
   reserveTerms(compiledTerms,coefficient.termCount(),limits.maxTerms);
   gate.columns[column].push_back({row,std::move(coefficient)});
  }
  gates.push_back(std::move(gate));
 }
 // With no recorded measurements all classical bits retain zero. Certification
 // of every unitary proves total mass one without expanding an unobserved state.
 if(measurements.empty() || selected.empty()) {
  std::map<std::uint64_t,std::string> result{{0,"1"}};output.swap(result);return true;
 }
 const std::size_t dimension=std::size_t(1)<<qubits;
 std::vector<PhasePolynomial> state(dimension);state[0]=PhasePolynomial::term(0,1,0,budget);
 for(const auto &gate:gates) {
  budget.charge();std::vector<PhasePolynomial> next(dimension);std::size_t terms=0,mask=0;
  for(unsigned wire:gate.wires)mask|=std::size_t(1)<<(qubits-1-wire);
  for(std::size_t basis=0;basis<dimension;++basis) {
   budget.charge();if(!state[basis].termCount())continue;
   std::size_t column=0;
   for(unsigned wire:gate.wires)column=(column<<1)|((basis>>(qubits-1-wire))&1);
   for(const auto &entry:gate.columns[column]) {
    budget.charge();std::size_t target=basis&~mask;
    for(std::size_t k=0;k<gate.wires.size();++k)
     if(entry.row&(std::size_t(1)<<(gate.wires.size()-1-k)))target|=std::size_t(1)<<(qubits-1-gate.wires[k]);
    auto value=next[target].plus(state[basis].times(entry.value,budget),budget);
    terms-=next[target].termCount();reserveTerms(terms,value.termCount(),limits.maxTerms);
    next[target]=std::move(value);
   }
  }
  state=std::move(next);
 }
 std::map<std::uint64_t,std::vector<PhasePolynomial>> groups;
 for(std::size_t basis=0;basis<dimension;++basis) {
  budget.charge();if(!state[basis].termCount())continue;
  std::uint64_t record=0;
  for(const auto &measurement:measurements) {
   const auto flag=std::uint64_t(1)<<measurement.second;
   record=(record&~flag)|(((basis>>(qubits-1-measurement.first))&1)?flag:0);
  }
  std::uint64_t key=0;for(unsigned bit:selected)key=(key<<1)|((record>>bit)&1);
  groups[key].push_back(std::move(state[basis]));
 }
 std::map<std::uint64_t,std::string> result;std::size_t characters=0;
 for(const auto &group:groups) {
  budget.charge();auto text=probabilityText(group.second,budget,
     std::min(limits.maxProbabilityCharacters,limits.maxTotalCharacters-characters));
  characters+=text.size();result.emplace(group.first,std::move(text));
 }
 output.swap(result);return true;
}
}
