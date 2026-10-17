// GPL-2.0-or-later; see COPYING.
#include "QuantumExactOperation.h"
#include "QuantumAlgebra.h"
#include "Calculator.h"
#include <stdexcept>

namespace QuantumExact {
namespace {
void checkpoint() {
 if(CALCULATOR->aborted()) throw std::runtime_error("Exact operation validation cancelled");
}
}
TracePreservingMap::TracePreservingMap(const std::vector<MathStructure> &operators,
 std::size_t maxEntries,const EvaluationOptions &options):dimension_(0) {
 checkpoint();
 if(!CALCULATOR->getFunction("conj")) throw std::invalid_argument("Load global definitions before exact operation validation");
 if(operators.empty()) throw std::invalid_argument("A Kraus map needs at least one operator");
 if(operators.size()>256) throw std::length_error("A Kraus map supports at most 256 operators");
 const auto &first=operators.front();
 if(!first.isMatrix() || !first.rows() || first.rows()!=first.columns())
  throw std::invalid_argument("Kraus operators must be square matrices");
 const std::size_t n=first.rows();
 if(n>1024) throw std::length_error("Exact operation dimension exceeds 1024");
 if(n&(n-1)) throw std::invalid_argument("Circuit operator dimensions must be powers of two");
 if(n*n>maxEntries || operators.size()>maxEntries/(n*n))
  throw std::length_error("Exact operation entry budget exceeded");
 EvaluationOptions exact=options;exact.approximation=APPROXIMATION_EXACT;
 MathStructure sum;sum.clearMatrix();sum.resizeMatrix(n,n,m_zero);
 for(const auto &raw:operators) {
  checkpoint();
  if(!raw.isMatrix() || raw.rows()!=n || raw.columns()!=n)
   throw std::invalid_argument("All Kraus operators must have matching square dimensions");
  MathStructure op=raw;
  for(std::size_t r=1;r<=n;++r) {
   checkpoint();
   for(std::size_t c=1;c<=n;++c) {
    auto &cell=*op.getElement(r,c);cell.eval(exact);
    if(cell.isApproximate()) throw std::domain_error("Exact operation validation requires exact entries; approximate matrices need numerical validation");
    if(!cell.representsScalar() || cell.isUndefined() || (cell.isNumber() && cell.number().isInfinite(false)))
     throw std::invalid_argument("Kraus entries must be finite scalar expressions");
   }
  }
  MathStructure gram=quantumAdjoint(op,exact);gram*=op;gram.eval(exact);checkpoint();
  if(n==1 && !gram.isVector()) {
   *sum.getElement(1,1)+=gram;
  } else {
   if(!gram.isMatrix() || gram.rows()!=n || gram.columns()!=n)
    throw std::domain_error("Cannot evaluate exact Kraus completeness");
   for(std::size_t r=1;r<=n;++r)for(std::size_t c=1;c<=n;++c)
    *sum.getElement(r,c)+=*gram.getElement(r,c);
  }
  operators_.push_back(op);
 }
 bool unknown=false;
 for(std::size_t r=1;r<=n;++r) {
  checkpoint();
  for(std::size_t c=1;c<=n;++c) {
   MathStructure residual=*sum.getElement(r,c);
   if(r==c)residual-=1;
   residual.eval(exact);checkpoint();
   if(residual.isZero())continue;
   if(residual.representsNonZero())throw std::invalid_argument("Kraus operators do not preserve trace: sum(K-adjoint K) is not identity");
   unknown=true;
  }
 }
 if(unknown)throw std::domain_error("Cannot prove trace preservation with the current symbolic assumptions");
 dimension_=n;
}
}
