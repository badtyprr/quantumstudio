// GPL-2.0-or-later; see COPYING.
#include "QuantumSubsystem.h"
#include "Calculator.h"
#include "Function.h"
#include <algorithm>
#include <string>
#include <vector>
#include <utility>
namespace {
const MathStructure &element(const MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure dagger(const MathStructure &a, const EvaluationOptions &eo) {
 MathStructure out=a;
 if(out.isMatrix()) {
  out.transposeMatrix();
  for(size_t r=0;r<out.rows();++r) for(size_t c=0;c<out.columns();++c) {
   MathStructure v=element(out,r,c); element(out,r,c).set(CALCULATOR->getFunction("conj"), &v, NULL); element(out,r,c).eval(eo);
  }
 } else { out.set(CALCULATOR->getFunction("conj"), &a, NULL); out.eval(eo); }
 return out;
}
class QuantumSubsystemFunction: public MathFunction {
 std::string op;
 public:
 QuantumSubsystemFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumSubsystemFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t k=0;k<args.size();++k)args[k].eval(eo);
  if((op=="qpermute" || op=="qpermutedim") && args[0].isVector() && !args[0].isMatrix()) {
   bool flat=true;for(size_t k=0;k<args[0].size();++k)if(args[0][k].isVector())flat=false;
   if(flat && args[0].size()>0 && args[0].size()<=1024) {
    MathStructure row;row.clearMatrix();row.resizeMatrix(1,args[0].size(),m_zero);
    for(size_t k=0;k<args[0].size();++k)element(row,0,k)=args[0][k];
    args[0]=row;
   }
  }
  const MathStructure &a=args[0];
  if(!a.isMatrix()){CALCULATOR->error(true,"Subsystem operations require a matrix (kets are column matrices).",NULL);return 0;}
  if(op=="qapply") {
   const MathStructure &state=args[1];
   if(!a.isMatrix() || a.rows()!=a.columns() || !state.isMatrix() || (state.columns()!=1 && state.columns()!=state.rows()) || state.rows()>1024 || state.rows()*state.columns()>262144) { CALCULATOR->error(true,"apply requires a square gate and a column ket or square density matrix (at most 1024 rows and 262144 elements).",NULL); return 0; }
   if(state.columns()!=1 && !CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global function definitions before applying a gate to a density matrix.",NULL); return 0; }
   size_t n=state.rows(), dim=a.rows(), bits=0, gatebits=0;
   while((size_t(1)<<bits)<n) ++bits;
   while((size_t(1)<<gatebits)<dim) ++gatebits;
   if(n!=(size_t(1)<<bits) || dim!=(size_t(1)<<gatebits) || gatebits>bits) { CALCULATOR->error(true,"apply requires power-of-two gate and state dimensions.",NULL); return 0; }
   std::vector<size_t> targets; size_t mask=0;
   size_t count=args[2].isVector() ? args[2].size() : 1;
   if(count!=gatebits) { CALCULATOR->error(true,"One target index is required for each gate qubit.",NULL); return 0; }
   for(size_t k=0;k<count;++k) {
    const MathStructure &target=args[2].isVector() ? args[2][k] : args[2];
    if(!target.isNumber() || !target.number().isInteger() || target.number()<0 || target.number()>=Number(bits)) { CALCULATOR->error(true,"Target qubit index is out of range (leftmost is 0).",NULL); return 0; }
    size_t bit=size_t(1)<<(bits-1-target.number().intValue());
    if(mask & bit) { CALCULATOR->error(true,"Target qubit indices must be unique.",NULL); return 0; }
    mask|=bit; targets.push_back(bit);
   }
   auto leftApply=[&](const MathStructure &input,MathStructure &output) {
   output.clearMatrix(); output.resizeMatrix(n,input.columns(),m_zero);
   for(size_t j=0;j<n;++j) {
    if(CALCULATOR->aborted()) return 0;
    size_t column=0; for(size_t bit:targets) column=(column<<1) | ((j & bit) ? 1 : 0);
    for(size_t r=0;r<dim;++r) {
     if(element(a,r,column).isZero()) continue;
     size_t index=j & ~mask;
     for(size_t k=0;k<count;++k) if(r & (size_t(1)<<(count-1-k))) index|=targets[k];
     for(size_t c=0;c<input.columns();++c) {
      if(element(input,j,c).isZero()) continue;
      MathStructure term=element(a,r,column); term*=element(input,j,c); element(output,index,c)+=term;
     }
    }
   } return 1;
   };
   if(!leftApply(state,out)) return 0;
   // (U (U rho)-dagger)-dagger = U rho U-dagger. No full-system gate needed.
   if(state.columns()!=1) {
    MathStructure adjoint=dagger(out,eo), second;
    if(!leftApply(adjoint,second)) return 0;
    out=dagger(second,eo);
   }
   return 1;
  }
  if(op=="qpermute" || op=="qpermutedim") {
   if(!a.isMatrix() || (a.rows()!=1 && a.columns()!=1 && a.rows()!=a.columns()) || a.rows()*a.columns()>262144) {
    CALCULATOR->error(true,"permute requires a ket, bra, or square matrix with at most 262144 elements.",NULL); return 0;
   }
   size_t n=std::max(a.rows(),a.columns());
   if(n>1024) { CALCULATOR->error(true,"Permutation dimension must not exceed 1024.",NULL); return 0; }
   std::vector<size_t> dimensions;
   if(op=="qpermutedim") {
    if(!args[2].isVector() || args[2].size()==0 || args[2].size()>32) { CALCULATOR->error(true,"Permutation dimensions require a list of 1 to 32 factors.",NULL); return 0; }
    size_t product=1;
    for(size_t k=0;k<args[2].size();++k) {
     const MathStructure &d=args[2][k];
     if(!d.isNumber() || !d.number().isInteger() || d.number()<1 || d.number()>1024) { CALCULATOR->error(true,"Subsystem dimensions must be integers from 1 to 1024.",NULL); return 0; }
     size_t dimension=d.number().intValue();
     if(product>1024/dimension) { CALCULATOR->error(true,"Permutation dimension product exceeds 1024.",NULL); return 0; }
     product*=dimension; dimensions.push_back(dimension);
    }
    if(product!=n) { CALCULATOR->error(true,"Permutation dimensions must multiply to the state or operator dimension.",NULL); return 0; }
   } else {
    size_t product=1; while(product<n) {dimensions.push_back(2);product*=2;}
    if(product!=n) { CALCULATOR->error(true,"Non-qubit permutations require explicit subsystem dimensions.",NULL); return 0; }
   }
   const MathStructure &order=args[1];
   if(!order.isVector() || order.size()!=dimensions.size()) { CALCULATOR->error(true,"Permutation order must list every subsystem exactly once.",NULL); return 0; }
   std::vector<size_t> permutation; std::vector<bool> seen(dimensions.size(),false);
   for(size_t k=0;k<order.size();++k) {
    if(!order[k].isNumber() || !order[k].number().isInteger() || order[k].number()<0 || order[k].number()>=Number(dimensions.size())) { CALCULATOR->error(true,"Permutation index is out of range.",NULL); return 0; }
    size_t index=order[k].number().intValue();
    if(seen[index]) { CALCULATOR->error(true,"Permutation indices must be unique.",NULL); return 0; }
    seen[index]=true; permutation.push_back(index);
   }
   std::vector<size_t> mapping(n), digits(dimensions.size());
   for(size_t old=0;old<n;++old) {
    size_t value=old, dest=0;
    for(size_t k=dimensions.size();k>0;--k) {digits[k-1]=value%dimensions[k-1];value/=dimensions[k-1];}
    for(size_t index:permutation) dest=dest*dimensions[index]+digits[index];
    mapping[old]=dest;
   }
   out.clearMatrix(); out.resizeMatrix(a.rows(),a.columns(),m_zero);
   for(size_t r=0;r<a.rows();++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<a.columns();++c) element(out,a.rows()==1 ? 0 : mapping[r],a.columns()==1 ? 0 : mapping[c])=element(a,r,c);
   }
   return 1;
  }
  if(op=="qptracedim" || op=="qptransposedim") {
   size_t n=a.rows(); const MathStructure &dims=args[2];
   if(n!=a.columns() || n>512 || !dims.isVector() || dims.size()==0 || dims.size()>32) { CALCULATOR->error(true,"Explicit subsystem dimensions require a square matrix of at most 512 rows and a list of 1 to 32 dimensions.",NULL); return 0; }
   std::vector<size_t> dimensions, strides(dims.size()); size_t total=1;
   for(size_t k=0;k<dims.size();++k) {
    if(!dims[k].isNumber() || !dims[k].number().isInteger() || dims[k].number()<1 || dims[k].number()>512) { CALCULATOR->error(true,"Subsystem dimensions must be integers from 1 to 512.",NULL); return 0; }
    size_t dimension=dims[k].number().intValue();
    if(total>512/dimension) { CALCULATOR->error(true,"Subsystem dimension product exceeds 512.",NULL); return 0; }
    total*=dimension; dimensions.push_back(dimension);
   }
   if(total!=n) { CALCULATOR->error(true,"Subsystem dimension product must equal the matrix dimension.",NULL); return 0; }
   size_t stride=1; for(size_t k=dimensions.size();k>0;--k) {strides[k-1]=stride; stride*=dimensions[k-1];}
   std::vector<bool> selected(dimensions.size(),false);
   size_t count=args[1].isVector() ? args[1].size() : 1;
   for(size_t k=0;k<count;++k) {
    const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
    if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(dimensions.size())) { CALCULATOR->error(true,"Subsystem index is out of range (leftmost is 0).",NULL); return 0; }
    size_t which=index.number().intValue();
    if(selected[which]) { CALCULATOR->error(true,"Subsystem indices must be unique.",NULL); return 0; }
    selected[which]=true;
   }
   size_t remaining=1; for(size_t k=0;k<dimensions.size();++k) if(!selected[k]) remaining*=dimensions[k];
   std::vector<size_t> kept(n,0), removed(n,0);
   for(size_t j=0;j<n;++j) for(size_t k=0;k<dimensions.size();++k) {
    size_t digit=(j/strides[k])%dimensions[k];
    if(selected[k]) removed[j]+=digit*strides[k]; else kept[j]=kept[j]*dimensions[k]+digit;
   }
   bool transpose=op=="qptransposedim";
   out.clearMatrix(); out.resizeMatrix(transpose ? n : remaining,transpose ? n : remaining,m_zero);
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<n;++c) {
     if(transpose) element(out,r-removed[r]+removed[c],c-removed[c]+removed[r])=element(a,r,c);
     else if(removed[r]==removed[c]) element(out,kept[r],kept[c])+=element(a,r,c);
    }
   }
   if(!transpose && remaining==1) { MathStructure scalar=element(out,0,0); out=scalar; }
   return 1;
  }
  if(op=="qptrace" || op=="qptranspose") {
   size_t n=a.rows(), bits=0;
   while((size_t(1)<<bits)<n && bits<11) ++bits;
   if(n!=a.columns() || n!=(size_t(1)<<bits) || bits>10) { CALCULATOR->error(true,"Partial trace/transpose requires a qubit matrix of at most 10 qubits.",NULL); return 0; }
   size_t count=args[1].isVector() ? args[1].size() : 1, mask=0;
   for(size_t k=0;k<count;++k) {
    const MathStructure &index=args[1].isVector() ? args[1][k] : args[1];
    if(!index.isNumber() || !index.number().isInteger() || index.number()<0 || index.number()>=Number(bits)) { CALCULATOR->error(true,"Partial trace indices must be integers in range (leftmost subsystem is 0).",NULL); return 0; }
    size_t bit=size_t(1)<<(bits-1-index.number().intValue());
    if(mask & bit) { CALCULATOR->error(true,"Partial trace subsystem indices must be unique.",NULL); return 0; }
    mask|=bit;
   }
   if(op=="qptranspose") {
    out.clearMatrix(); out.resizeMatrix(n,n,m_zero);
    for(size_t r=0;r<n;++r) {
     if(CALCULATOR->aborted()) return 0;
     for(size_t c=0;c<n;++c) element(out,(r & ~mask)|(c & mask),(c & ~mask)|(r & mask))=element(a,r,c);
    } return 1;
   }
   size_t remaining=n>>count;
   std::vector<size_t> compressed(n,0);
   for(size_t i=0;i<n;++i) for(size_t bit=n>>1;bit;bit>>=1) if(!(bit & mask)) compressed[i]=(compressed[i]<<1) | ((i & bit) ? 1 : 0);
   out.clearMatrix(); out.resizeMatrix(remaining,remaining,m_zero);
   for(size_t r=0;r<n;++r) {
    if(CALCULATOR->aborted()) return 0;
    for(size_t c=0;c<n;++c) if((r & mask)==(c & mask)) element(out,compressed[r],compressed[c])+=element(a,r,c);
   } return 1;
  }
  return 0;
 }
};
}
void registerQuantumSubsystem(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qapply",3),{"qpermute",2},{"qpermutedim",3},{"qptrace",2},{"qptracedim",3},{"qptranspose",2},{"qptransposedim",3}})
  calculator.addFunction(new QuantumSubsystemFunction(entry.first,entry.second));
}
