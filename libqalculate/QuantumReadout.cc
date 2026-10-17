#include "QuantumReadout.h"
#include <cmath>
#include <stdexcept>

namespace QuantumNumerics {
ReadoutAssignment::ReadoutAssignment(const std::vector<unsigned> &targets,
 const std::vector<std::vector<double>> &probabilities):mask(0) {
 // Bound a correlated assignment table to 256 by 256, independently of the
 // size of the classical register. Validate before retaining any table data.
 if(targets.empty() || targets.size()>8)
  throw std::invalid_argument("Readout assignment needs one to eight classical bits");
 for(unsigned bit:targets) {
  if(bit>=64)throw std::out_of_range("Readout target exceeds the classical register");
  const std::uint64_t flag=std::uint64_t(1)<<bit;
  if(mask&flag)throw std::invalid_argument("Readout targets must be distinct");
  mask|=flag;
 }
 const std::size_t dimension=std::size_t(1)<<targets.size();
 if(probabilities.size()!=dimension)throw std::invalid_argument("Readout table dimensions must match target bits");
 for(const auto &row:probabilities) {
  if(row.size()!=dimension)throw std::invalid_argument("Readout table must be square");
  long double total=0;
  for(double probability:row) {
   if(!std::isfinite(probability) || probability<0 || probability>1)
    throw std::invalid_argument("Readout probabilities must be finite and between zero and one");
   total+=probability;
  }
  if(std::abs(total-1.L)>1e-12L)throw std::invalid_argument("Readout table rows must sum to one");
  totals.push_back(total);
 }
 bits=targets;rows=probabilities;
}

std::uint64_t ReadoutAssignment::apply(std::uint64_t memory,double uniformDraw) const {
 if(rows.empty())throw std::logic_error("Readout assignment has been moved from");
 if(!std::isfinite(uniformDraw) || uniformDraw<0 || uniformDraw>=1)
  throw std::invalid_argument("Readout draw must be finite and in [0,1)");
 std::size_t input=0;
 for(unsigned bit:bits)input=(input<<1)|((memory>>bit)&1);
 const auto &row=rows[input];
 const long double threshold=static_cast<long double>(uniformDraw)*totals[input];
 long double cumulative=0;
 std::size_t selected=0;
 for(std::size_t outcome=0;outcome<row.size();++outcome) {
  if(row[outcome]==0)continue;
  selected=outcome;cumulative+=row[outcome];
  if(threshold<cumulative)break;
 }
 std::uint64_t result=memory&~mask;
 for(std::size_t i=0;i<bits.size();++i)
  result|=std::uint64_t((selected>>(bits.size()-1-i))&1)<<bits[i];
 return result;
}
}
