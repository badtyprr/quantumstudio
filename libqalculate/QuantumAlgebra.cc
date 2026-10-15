// GPL-2.0-or-later; see COPYING.
#include "QuantumAlgebra.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
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
MathStructure multiply(MathStructure a, const MathStructure &b, const EvaluationOptions &eo) {
 a*=b; a.eval(eo);
 if(a.isMatrix() && a.rows()==1 && a.columns()==1) { MathStructure scalar=element(a,0,0); return scalar; }
 return a;
}
class QuantumAlgebraFunction: public MathFunction {
 std::string op;
 public:
 QuantumAlgebraFunction(const std::string &name,int n):MathFunction(name,n),op(name) {}
 ExpressionItem *copy() const {return new QuantumAlgebraFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  if((op=="qdag" || op=="qconj" || op=="qdensity" || op=="qnorm" || op=="qnormalize") && !CALCULATOR->getFunction("conj")) {
   CALCULATOR->error(true,"Load global function definitions before quantum conjugation.",NULL);return 0;
  }
  MathStructure args=raw;for(size_t j=0;j<args.size();++j)args[j].eval(eo);
  if(op=="qtensor" || op=="qadjacent" || op=="qtensorpow" || op=="qdag" || op=="qtranspose")for(size_t j=0;j<((op=="qtensor" || op=="qadjacent") ? 2U : 1U);++j) {
   if(!args[j].isVector() || args[j].isMatrix())continue;
   bool flat=true;for(size_t k=0;k<args[j].size();++k)if(args[j][k].isVector())flat=false;
   if(flat && args[j].size()>0 && args[j].size()<=1024) {
    MathStructure row;row.clearMatrix();row.resizeMatrix(1,args[j].size(),m_zero);
    for(size_t k=0;k<args[j].size();++k)element(row,0,k)=args[j][k];
    args[j]=row;
   }
  }
  const MathStructure &a=args[0];
  if(op=="qketstate") {
   if(!a.isMatrix() || a.columns()!=1 || a.rows()==0 || a.rows()>1024) {
    CALCULATOR->error(true,"A named ket must evaluate to a column vector with at most 1024 rows. For an integer basis index, specify the dimension, for example |k>_4.",NULL);return 0;
   }
   out=a;return 1;
  }
  if(op=="qindexxor" || op=="qoplus") {
   // A computed index may contain matrix expressions such as trace(A oplus B).
   if(a.isMatrix() && args[1].isMatrix()) {
    out.set(CALCULATOR->getFunction("qdirectsum"), &a, &args[1], NULL);out.eval(eo);
    return out.isMatrix() ? 1 : 0;
   }
   for(size_t j=0;j<2;++j)if(!args[j].isNumber() || !args[j].number().isInteger() || args[j].number()<0) {
    CALCULATOR->error(true,"Scalar XOR requires nonnegative integer operands.",NULL);return 0;
   }
   Number value=a.number();if(!value.bitXor(args[1].number()))return 0;
   out.set(value);return 1;
  }
  if(op=="qbasis") {
   const MathStructure &dimension=args[1];
   if(!a.isNumber() || !a.number().isInteger() || a.number()<0 || !dimension.isNumber() || !dimension.number().isInteger() || dimension.number()<2 || dimension.number()>1024 || a.number()>=dimension.number()) {
    CALCULATOR->error(true,"basis(index,dimension) requires an integer dimension from 2 to 1024 and a zero-based index in range.",NULL); return 0;
   }
   out.clearMatrix(); out.resizeMatrix(dimension.number().intValue(),1,m_zero); element(out,a.number().intValue(),0)=m_one; return 1;
  }
  if(op=="qdag") { out=dagger(a,eo); return 1; }
  if(op=="qconj") { out=dagger(a,eo); if(a.isMatrix()) out.transposeMatrix(); return 1; }
  if(op=="qtranspose") { out=a; if(a.isMatrix()) out.transposeMatrix(); else if(a.isVector()) { CALCULATOR->error(true,"Transpose requires a matrix or scalar.",NULL); return 0; } return 1; }
  if(op=="qadjacent" && a.isMatrix() && args[1].isMatrix() &&
     ((a.columns()==1 && args[1].columns()==1) || (a.rows()==1 && args[1].rows()==1))) {
   // Juxtaposed state vectors form a tensor product, including grouped sums.
   // Reuse the tensor operation's allocation and cancellation checks.
   out.set(CALCULATOR->getFunction("qtensor"), &a, &args[1], NULL);out.eval(eo);
   return out.isMatrix() || out.isVector() ? 1 : 0;
  }
  if(op=="qmul" || op=="qadjacent") {
   if(a.isMatrix() && args[1].isMatrix() && a.columns()!=args[1].rows()) { CALCULATOR->error(true,"Quantum matrix dimensions do not match.",NULL); return 0; }
   out=multiply(a,args[1],eo); return 1;
  }
  if(!a.isMatrix()) { CALCULATOR->error(true,"Quantum operation requires a matrix (kets are column matrices).",NULL); return 0; }
  if(op=="qtensorpow") {
   if(!args[1].isNumber() || !args[1].number().isInteger() || args[1].number()<0 || args[1].number()>10) { CALCULATOR->error(true,"Tensor power requires an integer exponent from 0 to 10.",NULL); return 0; }
   int count=args[1].number().intValue(); out.setToIdentityMatrix(1);
   for(int k=0;k<count;++k) {
    MathStructure previous=out; out.set(CALCULATOR->getFunction("qtensor"), &previous, &a, NULL); out.eval(eo);
    // A tensor product of bras simplifies to a flat row vector.
    if(!out.isMatrix() && !out.isVector()) return 0;
   } return 1;
  }
  if(op=="qnorm" || op=="qnormalize") {
   if(a.columns()!=1) { CALCULATOR->error(true,"norm and normalize require a column ket.",NULL); return 0; }
   MathStructure norm=multiply(dagger(a,eo),a,eo);
   if(norm.isZero() && op=="qnormalize") { CALCULATOR->error(true,"Cannot normalize the zero ket.",NULL); return 0; }
   norm.raise(Number(1,2)); norm.eval(eo);
   out= op=="qnorm" ? norm : a; if(op=="qnormalize") out/=norm; return 1;
  }
  if(op=="qdensity") {
   if(a.columns()!=1 || a.rows()>1024) { CALCULATOR->error(true,"density requires a column ket with at most 1024 entries.",NULL); return 0; }
   out=multiply(a,dagger(a,eo),eo); return 1;
  }
  if(op=="qtrace") {
   if(a.rows()!=a.columns()) { CALCULATOR->error(true,"Trace requires a square matrix.",NULL); return 0; }
   out.clear(); for(size_t r=0;r<a.rows();++r) out+=element(a,r,r); return 1;
  }
  if(op=="qcontrol" || op=="qcontrolpattern") {
   const MathStructure &count=args[1], &state=args[2];
   if(!count.isNumber() || !count.number().isInteger() || count.number()<1 || count.number()>8) {
    CALCULATOR->error(true,"Controlled gates require an integer control count from 1 to 8.",NULL); return 0;
   }
   size_t blocks=size_t(1)<<count.number().intValue(), n=a.rows();
   if(op=="qcontrolpattern" && args[3]!=count) {
    CALCULATOR->error(true,"The control pattern length must equal the number of controls.",NULL);return 0;
   }
   if(n!=a.columns() || n<2 || (n & (n-1)) || n>512/blocks) {
    CALCULATOR->error(true,"Controlled gates require a square qubit operator and at most 512 total dimensions.",NULL); return 0;
   }
   if(!state.isNumber() || !state.number().isInteger() || state.number()<0 || state.number()>=Number(blocks)) {
    CALCULATOR->error(true,"Control state must be an integer from 0 to 2^controls-1; the leftmost control is the most significant bit.",NULL); return 0;
   }
   size_t offset=n*state.number().intValue();
   out.setToIdentityMatrix(n*blocks);
   for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) element(out,offset+r,offset+c)=element(a,r,c);
   return 1;
  }
  if(op=="qcontrolled") {
   size_t n=a.rows(); if(n!=a.columns() || n>256) { CALCULATOR->error(true,"Controlled gates require a square matrix of dimension at most 256.",NULL); return 0; }
   out.setToIdentityMatrix(n*2); for(size_t r=0;r<n;++r) for(size_t c=0;c<n;++c) element(out,r+n,c+n)=element(a,r,c); return 1;
  }
  const MathStructure &b=args[1]; if(!b.isMatrix()) { CALCULATOR->error(true,"Quantum operation requires two matrices.",NULL); return 0; }
  if(op=="qcomm" || op=="qanticomm") {
   if(a.rows()!=a.columns() || b.rows()!=b.columns() || a.rows()!=b.rows()) { CALCULATOR->error(true,"Commutators require square matrices of the same dimension.",NULL); return 0; }
   out=multiply(a,b,eo); auto reverse=multiply(b,a,eo); if(op=="qcomm") out-=reverse; else out+=reverse; return 1;
  }
  size_t rows=op=="qtensor" ? a.rows()*b.rows() : a.rows()+b.rows();
  size_t cols=op=="qtensor" ? a.columns()*b.columns() : a.columns()+b.columns();
  if(rows>1024 || cols>1024 || rows*cols>1048576) { CALCULATOR->error(true,"Quantum matrix allocation limit exceeded (1048576 elements).",NULL); return 0; }
  out.clearMatrix(); out.resizeMatrix(rows,cols,m_zero);
  for(size_t r=0;r<a.rows();++r) for(size_t c=0;c<a.columns();++c) {
   if(CALCULATOR->aborted()) return 0;
   if(op=="qdirectsum") element(out,r,c)=element(a,r,c);
   else for(size_t j=0;j<b.rows();++j) for(size_t k=0;k<b.columns();++k) { element(out,r*b.rows()+j,c*b.columns()+k)=element(a,r,c); element(out,r*b.rows()+j,c*b.columns()+k)*=element(b,j,k); }
  }
  if(op=="qdirectsum") for(size_t r=0;r<b.rows();++r) for(size_t c=0;c<b.columns();++c) element(out,r+a.rows(),c+a.columns())=element(b,r,c);
  return 1;
 }
};
}
void registerQuantumAlgebra(Calculator &calculator) {
 calculator.addFunction(new QuantumAlgebraFunction("qketstate",1));
 for(const auto &entry:{std::pair<const char *,int>("qbasis",2),{"qindexxor",2},{"qoplus",2},{"qdag",1},{"qconj",1},{"qtranspose",1},{"qmul",2},{"qadjacent",2},{"qtensorpow",2},{"qnorm",1},{"qnormalize",1},{"qdensity",1},{"qtrace",1},{"qcontrol",3},{"qcontrolpattern",4},{"qcontrolled",1},{"qcomm",2},{"qanticomm",2},{"qtensor",2},{"qdirectsum",2}})
  calculator.addFunction(new QuantumAlgebraFunction(entry.first,entry.second));
}
