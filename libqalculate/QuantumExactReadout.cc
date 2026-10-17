// GPL-2.0-or-later; see COPYING.
#include "QuantumExactReadout.h"
#include "Calculator.h"
#include <stdexcept>

namespace QuantumExact {
namespace {
void checkpoint() {
 if(CALCULATOR->aborted())throw std::runtime_error("Exact readout evaluation cancelled");
}
}
ReadoutAssignment::ReadoutAssignment(const std::vector<unsigned> &bits,
 const MathStructure &table,const EvaluationOptions &options):mask_(0) {
 checkpoint();
 if(bits.empty() || bits.size()>8)throw std::invalid_argument("Exact readout needs one to eight classical bits");
 for(unsigned bit:bits) {
  if(bit>=64)throw std::out_of_range("Readout target exceeds the classical record");
  const std::uint64_t flag=std::uint64_t(1)<<bit;
  if(mask_&flag)throw std::invalid_argument("Readout targets must be distinct");
  mask_|=flag;
 }
 const std::size_t n=std::size_t(1)<<bits.size();
 if(!table.isMatrix() || table.rows()!=n || table.columns()!=n)
  throw std::invalid_argument("Readout table dimensions must match its selected bits");
 bits_=bits;table_=table;
 EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;
 for(std::size_t r=1;r<=n;++r) {
  checkpoint();MathStructure total(0);
  for(std::size_t c=1;c<=n;++c) {
   checkpoint();auto &entry=*table_.getElement(r,c);entry.eval(exact);
   if(entry.isApproximate())throw std::domain_error("Exact readout requires exact probabilities");
   if(!entry.representsScalar() || entry.isUndefined() ||
      (entry.isNumber() && (entry.number().isInfinite(false) || entry.number().isComplex())) || entry.representsNegative())
    throw std::invalid_argument("Readout probabilities must be finite, real and nonnegative");
   if(!entry.representsReal() || !entry.representsNonNegative())
    throw std::domain_error("Cannot prove readout probabilities are real and nonnegative with the current assumptions");
   total+=entry;
  }
  total-=1;total.eval(exact);checkpoint();
  if(!total.isZero()) {
   if(total.representsNonZero())throw std::invalid_argument("Readout probability rows must sum to one");
   throw std::domain_error("Cannot prove readout rows sum to one with the current assumptions");
  }
 }
}
std::map<std::uint64_t,MathStructure> ReadoutAssignment::outcomes(std::uint64_t record) const {
 checkpoint();std::size_t row=0;
 for(unsigned bit:bits_)row=(row<<1)|((record>>bit)&1);
 std::map<std::uint64_t,MathStructure> output;
 for(std::size_t column=0;column<table_.columns();++column) {
  checkpoint();const auto &probability=*table_.getElement(row+1,column+1);
  if(probability.isZero())continue;
  std::uint64_t key=record&~mask_;
  for(std::size_t k=0;k<bits_.size();++k)
   key|=std::uint64_t((column>>(bits_.size()-1-k))&1)<<bits_[k];
  output.emplace(key,probability);
 }
 return output;
}
}
