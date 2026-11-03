// GPL-2.0-or-later; see COPYING.
#include "QuantumSubsystem.h"
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "Function.h"
#include <algorithm>
#include <string>
#include <vector>
#include <utility>
namespace {
const MathStructure &element(const MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
bool mappedSubsystems(const MathStructure &value) {
 return value.isFunction() && value.function()->referenceName()=="qsubsystems" && value.size()==3;
}
bool subsystemError(const char *message) {CALCULATOR->error(true,message,NULL);return false;}
bool validSubsystems(const MathStructure &matrix,const MathStructure &labels,const MathStructure &dims) {
 if(mappedSubsystems(matrix))return subsystemError("A subsystem mapping is already attached; nested redeclarations are not allowed.");
 if(!labels.isVector() || labels.size()==0 || labels.size()>32)
  return subsystemError("A subsystem mapping requires an ordered list of 1 to 32 labels.");
 for(size_t k=0;k<labels.size();++k) {
  const std::string name=labels[k].isSymbolic() ? labels[k].symbol() : "";
  bool valid=!name.empty() && name.size()<=64;
  for(size_t j=0;j<name.size();++j) {
   unsigned char c=name[j];bool letter=(c>='A' && c<='Z') || (c>='a' && c<='z');
   if(!letter && (j==0 || !((c>='0' && c<='9') || c=='_')))valid=false;
  }
  if(!valid)return subsystemError("Subsystem labels must be literal identifiers of 1 to 64 ASCII letters, digits or underscores, starting with a letter.");
  for(size_t j=0;j<k;++j)if(labels[j].equals(labels[k]))return subsystemError("Duplicate subsystem labels in mapping.");
 }
 if(!dims.isVector() || dims.size()!=labels.size())return subsystemError("Subsystem labels and dimensions must have matching lengths.");
 size_t product=1;
 for(size_t k=0;k<dims.size();++k) {
  if(!dims[k].isNumber() || !dims[k].number().isInteger() || dims[k].number()<1 || dims[k].number()>512)
   return subsystemError("Subsystem dimensions must be integers from 1 to 512.");
  size_t dimension=dims[k].number().intValue();
  if(product>512/dimension)return subsystemError("Subsystem dimension product exceeds 512.");
  product*=dimension;
 }
 if(!matrix.isMatrix() || matrix.rows()!=matrix.columns() || matrix.rows()>512)
  return subsystemError("A subsystem mapping requires a square matrix of at most 512 rows.");
 if(product!=matrix.rows())return subsystemError("Subsystem dimension product must equal the matrix dimension.");
 return true;
}
class QuantumSubsystemFunction: public MathFunction {
 std::string op;
 public:
 QuantumSubsystemFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumSubsystemFunction(*this);}
 bool representsScalar(const MathStructure &args) const {return op=="qsubsystems" ? false : MathFunction::representsScalar(args);}
 bool representsNonMatrix(const MathStructure &args) const {return op=="qsubsystems" ? false : MathFunction::representsNonMatrix(args);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if(op=="qsubsystems") {
   // The notation parser quotes labels, so evaluating their vector constructor
   // never turns names into assigned variables, gates or scalar constants.
   MathStructure matrix=raw[0],labels=raw[1],dims=raw[2];matrix.eval(eo);labels.eval(eo);dims.eval(eo);
   if(!validSubsystems(matrix,labels,dims))return 0;
   if(matrix.equals(raw[0]) && labels.equals(raw[1]) && dims.equals(raw[2]))return 0;
   out=MathStructure(static_cast<MathFunction*>(this),static_cast<MathStructure*>(NULL));
   out.addChild(matrix);out.addChild(labels);out.addChild(dims);return 1;
  }
  if(op=="qptrace" || op=="qptracedim" || op=="qptraceselect") {
   MathStructure state=raw[0];state.eval(eo);
   if(mappedSubsystems(state)) {
    if(op=="qptracedim") {subsystemError("A named subsystem mapping already supplies dimensions; do not pass conflicting explicit dimensions.");return 0;}
    if(!validSubsystems(state[0],state[1],state[2]))return 0;
    MathStructure selected=raw[1];selected.eval(eo);
    size_t count=selected.isVector() ? selected.size() : 1;
    if(count>32) {subsystemError("Too many traced subsystem labels.");return 0;}
    MathStructure indices;indices.clearVector();std::vector<bool> seen(state[1].size(),false);
    for(size_t k=0;k<count;++k) {
     const MathStructure &label=selected.isVector() ? selected[k] : selected;
     if(!label.isSymbolic()) {subsystemError("A mapped partial trace requires subsystem labels, not numeric indices.");return 0;}
     size_t index=0;while(index<state[1].size() && !label.equals(state[1][index]))++index;
     if(index==state[1].size()) {subsystemError("Unknown subsystem label in partial trace.");return 0;}
     if(seen[index]) {subsystemError("Duplicate traced subsystem labels.");return 0;}
     seen[index]=true;indices.addChild(MathStructure(Number(index)));
    }
    MathStructure args;args.clearVector();args.addChild(state[0]);args.addChild(indices);args.addChild(state[2]);
    return CALCULATOR->getFunction("qptracedim")->calculate(out,args,eo);
   }
   if(op=="qptraceselect") {
    // The same spelling can denote metadata on a mapped value or an assigned
    // numeric index on an ordinary matrix. Resolve only after seeing the value.
    MathStructure indices=raw[2];indices.eval(eo);
    for(size_t k=0;k<(indices.isVector() ? indices.size() : 1);++k)
     if(!(indices.isVector() ? indices[k] : indices).isNumber()) {
      subsystemError("Named partial traces require an explicit subsystems(matrix, labels, dimensions) mapping.");return 0;
     }
    MathStructure args;args.clearVector();args.addChild(state);args.addChild(indices);
    return CALCULATOR->getFunction("qptrace")->calculate(out,args,eo);
   }
   MathStructure selected=raw[1];selected.eval(eo);
   for(size_t k=0;k<(selected.isVector() ? selected.size() : 1);++k)
    if((selected.isVector() ? selected[k] : selected).isSymbolic()) {
     subsystemError("Named partial traces require an explicit subsystems(matrix, labels, dimensions) mapping.");return 0;
    }
  }
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
   if(!a.isMatrix() || a.rows()!=a.columns() || !state.isMatrix() || (state.columns()!=1 && state.columns()!=state.rows()) || state.rows()>1024 || state.rows()*state.columns()>1048576) { CALCULATOR->error(true,"apply requires a square gate and a column ket or square density matrix (at most 1024 rows and 1048576 elements).",NULL); return 0; }
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
   // Right-multiply by U-dagger directly. Only the small local gate needs
   // conjugation; transposing/conjugating full density matrices duplicates them.
   if(state.columns()!=1) {
    MathStructure adjoint=quantumAdjoint(a,eo), second;
    second.clearMatrix();second.resizeMatrix(n,n,m_zero);
    for(size_t j=0;j<n;++j) {
     if(CALCULATOR->aborted())return 0;
     size_t column=0;for(size_t bit:targets)column=(column<<1) | ((j & bit) ? 1 : 0);
     for(size_t r=0;r<dim;++r) {
      if(element(adjoint,column,r).isZero())continue;
      size_t index=j & ~mask;
      for(size_t k=0;k<count;++k)if(r & (size_t(1)<<(count-1-k)))index|=targets[k];
      for(size_t row=0;row<n;++row) {
       if(element(out,row,j).isZero())continue;
       MathStructure term=element(out,row,j);term*=element(adjoint,column,r);element(second,row,index)+=term;
      }
     }
    }
    out=second;
   }
   return 1;
  }
  if(op=="qpermute" || op=="qpermutedim") {
   if(!a.isMatrix() || (a.rows()!=1 && a.columns()!=1 && a.rows()!=a.columns()) || a.rows()*a.columns()>1048576) {
    CALCULATOR->error(true,"permute requires a ket, bra, or square matrix with at most 1048576 elements.",NULL); return 0;
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
 for(const auto &entry:{std::pair<const char *,int>("qapply",3),{"qsubsystems",3},{"qpermute",2},{"qpermutedim",3},{"qptrace",2},{"qptraceselect",3},{"qptracedim",3},{"qptranspose",2},{"qptransposedim",3}})
  calculator.addFunction(new QuantumSubsystemFunction(entry.first,entry.second));
}
