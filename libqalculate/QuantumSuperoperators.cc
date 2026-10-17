// GPL-2.0-or-later; see COPYING.
#include "QuantumSuperoperators.h"
#include "Calculator.h"
#include "QuantumAlgebra.h"
#include "Function.h"
#include <string>
#include <vector>
#include <utility>
namespace {
const MathStructure &element(const MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure multiply(MathStructure a, const MathStructure &b, const EvaluationOptions &eo) {
 a*=b; a.eval(eo);
 if(a.isMatrix() && a.rows()==1 && a.columns()==1) { MathStructure scalar=element(a,0,0); return scalar; }
 return a;
}
bool zeroMatrix(MathStructure matrix,const EvaluationOptions &eo) {
 matrix.eval(eo);
 if(!matrix.isMatrix()) return matrix.isZero();
 for(size_t r=0;r<matrix.rows();++r) for(size_t c=0;c<matrix.columns();++c) if(!element(matrix,r,c).isZero()) return false;
 return true;
}
MathStructure twoSidedSuperoperator(const MathStructure &left,MathStructure right,const EvaluationOptions &eo) {
 right.transposeMatrix();MathStructure result;
 result.set(CALCULATOR->getFunction("qtensor"),&right,&left,NULL);result.eval(eo);return result;
}
MathStructure dissipator(const MathStructure &collapse,const EvaluationOptions &eo) {
 MathStructure adjoint=quantumAdjoint(collapse,eo), product=multiply(adjoint,collapse,eo), identity;
 identity.setToIdentityMatrix(collapse.rows());
 MathStructure result=twoSidedSuperoperator(collapse,adjoint,eo);
 MathStructure loss=twoSidedSuperoperator(product,identity,eo);loss+=twoSidedSuperoperator(identity,product,eo);
 loss/=2;result-=loss;result.eval(eo);return result;
}
void pauliBasis(size_t d,std::vector<std::vector<size_t>> &locations,std::vector<std::vector<Number>> &phases) {
 locations.assign(d*d,std::vector<size_t>(d));phases.assign(d*d,std::vector<Number>(d));
 for(size_t p=0;p<d*d;++p)for(size_t c=0;c<d;++c) {
  size_t digits=p,row=c,bit=1;int phase=0;
  while(bit<d) {
   unsigned axis=digits%4;digits/=4;
   if(axis==1 || axis==2)row^=bit;
   if(axis==2)phase+=(c & bit) ? 3 : 1;
   if(axis==3 && (c & bit))phase+=2;
   bit<<=1;
  }
  locations[p][c]=row+d*c;
  Number factor;
  if(phase%2)factor.setImaginaryPart(phase%4==1 ? 1 : -1);
  else factor=phase%4==0 ? 1 : -1;
  phases[p][c]=factor;
 }
}
class QuantumSuperoperatorFunction: public MathFunction {
 std::string op;
 public:
 QuantumSuperoperatorFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumSuperoperatorFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t k=0;k<args.size();++k)args[k].eval(eo);
  if(op=="qvec" && args[0].isVector() && !args[0].isMatrix()) {
   bool flat=true;for(size_t k=0;k<args[0].size();++k)if(args[0][k].isVector())flat=false;
   if(flat && args[0].size()>0 && args[0].size()<=1024) {
    MathStructure row;row.clearMatrix();row.resizeMatrix(1,args[0].size(),m_zero);
    for(size_t k=0;k<args[0].size();++k)element(row,0,k)=args[0][k];
    args[0]=row;
   }
  }
  const MathStructure &a=args[0];
  if(op=="qpaulivec" || op=="qunpaulivec") {
   size_t d=a.rows();bool inverse=op=="qunpaulivec";
   if(inverse) {d=2;while(d*d<a.rows() && d<16)d*=2;}
   if(!a.isMatrix() || d<2 || d>16 || (d & (d-1)) || (inverse ? a.columns()!=1 || a.rows()!=d*d : a.columns()!=d)) {
    CALCULATOR->error(true,"paulivec requires a square one-to-four-qubit operator; unpaulivec requires a column with 4, 16, 64, or 256 Pauli coordinates.",NULL);return 0;
   }
   std::vector<std::vector<size_t>> locations;std::vector<std::vector<Number>> phases;pauliBasis(d,locations,phases);
   MathStructure scale{Number(d)};scale.raise(Number(1,2));scale.eval(eo);
   out.clearMatrix();out.resizeMatrix(inverse ? d : d*d,inverse ? d : 1,m_zero);
   for(size_t p=0;p<d*d;++p) {
    if(CALCULATOR->aborted())return 0;
    for(size_t c=0;c<d;++c) {
     size_t r=locations[p][c]%d;Number factor=phases[p][c];
     if(!inverse && factor.isComplex())factor.negate();
     MathStructure term=inverse ? element(a,p,0) : element(a,r,c);if(term.isZero())continue;
     term*=factor;
     if(inverse)element(out,r,c)+=term;else element(out,p,0)+=term;
    }
   }
   out/=scale;out.eval(eo);return 1;
  }
  if(op=="qvec") {
   if(!a.isMatrix() || a.rows()*a.columns()>1024) { CALCULATOR->error(true,"vec requires a matrix with at most 1024 entries.",NULL); return 0; }
   out.clearMatrix(); out.resizeMatrix(a.rows()*a.columns(),1,m_zero);
   for(size_t c=0;c<a.columns();++c) for(size_t r=0;r<a.rows();++r) element(out,c*a.rows()+r,0)=element(a,r,c);
   return 1;
  }
  if(op=="qlindblad" || op=="qliouvillian" || op=="qliouvillianclosed") {
   if(!CALCULATOR->getFunction("conj")) {CALCULATOR->error(true,"Load global functions before constructing a Lindblad generator.",NULL);return 0;}
   if(!a.isMatrix() || a.rows()!=a.columns() || a.rows()<2 || a.rows()>16) {
    CALCULATOR->error(true,"Lindblad generators require square operators of dimension 2 to 16.",NULL);return 0;
   }
   if(op=="qlindblad") {out=dissipator(a,eo);return 1;}
   MathStructure difference=a;difference-=quantumAdjoint(a,eo);
   if(!zeroMatrix(difference,eo)) {CALCULATOR->error(true,"liouvillian requires a Hermitian Hamiltonian.",NULL);return 0;}
   MathStructure identity;identity.setToIdentityMatrix(a.rows());
   out=twoSidedSuperoperator(a,identity,eo);out-=twoSidedSuperoperator(identity,a,eo);
   Number minusI;minusI.setImaginaryPart(-1);out*=minusI;
   if(op=="qliouvillian") {
    const MathStructure &collapses=args[1];
    if(!collapses.isVector() || collapses.size()>256) {CALCULATOR->error(true,"Collapse operators must be a list of at most 256 matrices; use vector(C0,C1,...).",NULL);return 0;}
    for(size_t j=0;j<collapses.size();++j) {
     if(CALCULATOR->aborted())return 0;
     const MathStructure &collapse=collapses[j];
     if(!collapse.isMatrix() || collapse.rows()!=a.rows() || collapse.columns()!=a.columns()) {CALCULATOR->error(true,"Collapse operators must match the Hamiltonian dimensions.",NULL);return 0;}
     out+=dissipator(collapse,eo);
    }
   }
   out.eval(eo);return 1;
  }
  if(op=="qspre" || op=="qspost" || op=="qsprepost") {
   if(!a.isMatrix() || a.rows()>16 || a.columns()>16 || (op!="qsprepost" && a.rows()!=a.columns())) {
    CALCULATOR->error(true,"Left/right superoperators require matrices with at most 16 rows and columns; spre and spost require square matrices.",NULL);return 0;
   }
   MathStructure left=a,right;
   if(op=="qsprepost") {
    right=args[1];
    if(!right.isMatrix() || right.rows()>16 || right.columns()>16) {
     CALCULATOR->error(true,"sprepost requires two matrices with at most 16 rows and columns each.",NULL);return 0;
    }
   } else if(op=="qspre")right.setToIdentityMatrix(a.rows());
   else {right=a;left.setToIdentityMatrix(a.rows());}
   // Column stacking: vec(A X B) = (B^T tensor A) vec(X).
   // This is a transpose, never an adjoint, even for complex B.
   right.transposeMatrix();
   out.set(CALCULATOR->getFunction("qtensor"),&right,&left,NULL);out.eval(eo);return 1;
  }
  if(op=="qunvec") {
   if(!a.isMatrix() || a.columns()!=1 || a.rows()>1024 || !args[1].isNumber() || !args[1].number().isInteger() || args[1].number()<1 || args[1].number()>1024) { CALCULATOR->error(true,"unvec requires a column vector of at most 1024 entries and a positive integer row count.",NULL); return 0; }
   size_t rows=args[1].number().intValue();
   if(a.rows()%rows!=0) { CALCULATOR->error(true,"unvec row count must divide the vector length.",NULL); return 0; }
   size_t columns=a.rows()/rows; out.clearMatrix(); out.resizeMatrix(rows,columns,m_zero);
   for(size_t c=0;c<columns;++c) for(size_t r=0;r<rows;++r) element(out,r,c)=element(a,c*rows+r,0);
   return 1;
  }
  return 0;
 }
};
}
void registerQuantumSuperoperators(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qvec",1),{"qunvec",2},{"qpaulivec",1},{"qunpaulivec",1},{"qlindblad",1},{"qliouvillian",2},{"qliouvillianclosed",1},{"qspre",1},{"qspost",1},{"qsprepost",2}})
  calculator.addFunction(new QuantumSuperoperatorFunction(entry.first,entry.second));
}
