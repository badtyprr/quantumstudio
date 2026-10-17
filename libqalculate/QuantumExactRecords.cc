// GPL-2.0-or-later; see COPYING.
#include "QuantumExactRecords.h"
#include "Calculator.h"
#include <stdexcept>

namespace QuantumExact {
namespace {
void checkpoint() {
 if(CALCULATOR->aborted()) throw std::runtime_error("Exact classical-record evaluation cancelled");
}
std::size_t validate(const Records &input, unsigned qubits, unsigned bits, std::size_t maxCells) {
 if(qubits>10 || bits>64) throw std::out_of_range("Exact records support at most 10 qubits and 64 classical bits");
 const std::size_t n=std::size_t(1)<<qubits, cells=n*n;
 if(cells>maxCells || input.size()>maxCells/cells) throw std::length_error("Exact record cell budget exceeded");
 for(const auto &record:input) {
  checkpoint();
  if(bits<64 && (record.first>>bits)) throw std::out_of_range("Classical record exceeds register");
  const auto &rho=record.second;
  if(!rho.isMatrix() || rho.rows()!=n || rho.columns()!=n) throw std::invalid_argument("Exact records require square density matrices matching the qubit count");
  for(std::size_t r=1;r<=n;++r) for(std::size_t c=1;c<=n;++c) {
   const auto &cell=*rho.getElement(r,c);
   if(!cell.representsScalar() || cell.isUndefined() || (cell.isNumber() && cell.number().isInfinite(false)))
    throw std::invalid_argument("Exact record entries must be finite scalar expressions");
  }
 }
 return n;
}
void accumulate(Records &output, std::uint64_t record, const MathStructure &rho,
                std::size_t maxCells, const EvaluationOptions &options) {
 const std::size_t n=rho.rows();
 bool nonzero=false;
 for(std::size_t r=1;r<=n;++r) for(std::size_t c=1;c<=n;++c)
  if(!rho.getElement(r,c)->isZero()) nonzero=true;
 if(!nonzero) return;
 auto found=output.find(record);
 if(found==output.end()) {
  if(output.size()>=maxCells/(n*n)) throw std::length_error("Exact record cell budget exceeded");
  output.emplace(record,rho);
 } else {
  MathStructure combined=found->second;
  for(std::size_t r=1;r<=n;++r) {
   checkpoint();
   for(std::size_t c=1;c<=n;++c) {
    auto &cell=*combined.getElement(r,c);
    cell+=*rho.getElement(r,c);cell.eval(options);
   }
  }
  checkpoint();found->second=combined;
 }
}
}
RecordAccumulator::RecordAccumulator(unsigned qubits,unsigned bits,std::size_t maxCells,
 const EvaluationOptions &options):qubits_(qubits),bits_(bits),maxCells_(maxCells),options_(options) {
 validate({},qubits_,bits_,maxCells_);
}
void RecordAccumulator::add(std::uint64_t record,const MathStructure &density) {
 validate({{record,density}},qubits_,bits_,maxCells_);
 accumulate(records_,record,density,maxCells_,options_);
}
Records RecordAccumulator::take() {Records output;output.swap(records_);return output;}
Records measure(const Records &input, unsigned qubits, unsigned classicalBits,
 unsigned wire, unsigned destination, std::size_t maxCells, const EvaluationOptions &options) {
 const std::size_t n=validate(input,qubits,classicalBits,maxCells);
 if(wire>=qubits || destination>=classicalBits) throw std::out_of_range("Measurement target is outside its register");
 const std::size_t mask=std::size_t(1)<<(qubits-1-wire);
 const std::uint64_t flag=std::uint64_t(1)<<destination;
 Records output;
 for(const auto &record:input) for(unsigned outcome=0;outcome<2;++outcome) {
  checkpoint();
  MathStructure projected;projected.clearMatrix();projected.resizeMatrix(n,n,m_zero);
  for(std::size_t r=0;r<n;++r) {
   checkpoint();
   if(bool(r&mask)!=bool(outcome)) continue;
   for(std::size_t c=0;c<n;++c) if(bool(c&mask)==bool(outcome))
    *projected.getElement(r+1,c+1)=*record.second.getElement(r+1,c+1);
  }
  accumulate(output,(record.first&~flag)|(outcome ? flag : 0),projected,maxCells,options);
 }
 checkpoint();
 return output;
}
std::map<std::uint64_t,MathStructure> weights(const Records &input, unsigned qubits,
 unsigned classicalBits, const std::vector<unsigned> &outputBits,
 std::size_t maxCells, const EvaluationOptions &options) {
 const std::size_t n=validate(input,qubits,classicalBits,maxCells);
 std::uint64_t seen=0;
 for(unsigned bit:outputBits) {
  if(bit>=classicalBits) throw std::out_of_range("Output bit is outside the classical register");
  const std::uint64_t flag=std::uint64_t(1)<<bit;
  if(seen&flag) throw std::invalid_argument("Output bits must be distinct");
  seen|=flag;
 }
 std::map<std::uint64_t,MathStructure> output;
 for(const auto &record:input) {
  checkpoint();
  std::uint64_t key=0;
  for(unsigned bit:outputBits) key=(key<<1)|((record.first>>bit)&1);
  MathStructure trace(0);
  for(std::size_t r=1;r<=n;++r) trace+=*record.second.getElement(r,r);
  trace.eval(options);
  if(trace.isZero()) continue;
  auto found=output.find(key);
  if(found==output.end()) output.emplace(key,trace);
  else {found->second+=trace;found->second.eval(options);}
 }
 checkpoint();
 return output;
}
}
