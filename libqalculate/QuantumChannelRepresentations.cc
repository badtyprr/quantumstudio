// GPL-2.0-or-later; see COPYING.
#include "QuantumChannelRepresentations.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <vector>
#include <utility>
namespace {
const MathStructure &element(const MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
MathStructure &element(MathStructure &m, size_t r, size_t c) { return *m.getElement(r+1,c+1); }
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
class QuantumChannelRepresentationFunction: public MathFunction {
 std::string op;
 public:
 QuantumChannelRepresentationFunction(const char *name):MathFunction(name,1),op(name) {}
 ExpressionItem *copy() const {return new QuantumChannelRepresentationFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure a=raw[0];a.eval(eo);
  if(op=="qsuperop" || op=="qchoi" || op=="qptm" || op=="qchi") {
   if(!CALCULATOR->getFunction("conj")) { CALCULATOR->error(true,"Load global functions before converting a quantum channel.",NULL); return 0; }
   if(!a.isVector() || a.size()==0 || a.size()>256) { CALCULATOR->error(true,"Channel conversion requires a list of 1 to 256 Kraus matrices; use vector(K0,K1,...).",NULL); return 0; }
   std::vector<MathStructure> operators; size_t input=0, output=0;
   for(size_t k=0;k<a.size();++k) {
    MathStructure matrix=a[k];
    if(matrix.isVector() && !matrix.isMatrix()) {
     bool flat=true; for(size_t j=0;j<matrix.size();++j) if(matrix[j].isVector()) flat=false;
     if(flat && matrix.size()>0 && matrix.size()<=32) {
      MathStructure row; row.clearMatrix(); row.resizeMatrix(1,matrix.size(),m_zero);
      for(size_t j=0;j<matrix.size();++j) element(row,0,j)=matrix[j];
      matrix=row;
     }
    }
    if(!matrix.isMatrix() || matrix.rows()>32 || matrix.columns()>32 || matrix.rows()*matrix.columns()>512) { CALCULATOR->error(true,"Kraus matrices require at most 32 rows, 32 columns, and 512 entries each.",NULL); return 0; }
    if(k==0) {input=matrix.columns();output=matrix.rows();}
    else if(matrix.rows()!=output || matrix.columns()!=input) { CALCULATOR->error(true,"All Kraus matrices must have matching input and output dimensions.",NULL); return 0; }
    operators.push_back(matrix);
   }
   if((op=="qptm" || op=="qchi") && (input!=output || input<2 || (input & (input-1)))) {
    CALCULATOR->error(true,"Pauli channel representations require square Kraus matrices for one to four qubits.",NULL);return 0;
   }
   bool choiBasis=op=="qchoi" || op=="qchi";
   size_t rows=choiBasis ? input*output : output*output;
   size_t columns=choiBasis ? rows : input*input;
   out.clearMatrix(); out.resizeMatrix(rows,columns,m_zero);
   for(const auto &matrix:operators) {
    MathStructure conjugated=matrix;
    for(size_t r=0;r<output;++r)for(size_t c=0;c<input;++c) {
     MathStructure value=element(matrix,r,c);
     element(conjugated,r,c).set(CALCULATOR->getFunction("conj"),&value,NULL);
     element(conjugated,r,c).eval(eo);
    }
    for(size_t r=0;r<output;++r) {
     if(CALCULATOR->aborted()) return 0;
     for(size_t i=0;i<input;++i) {
      if(element(matrix,r,i).isZero()) continue;
      for(size_t s=0;s<output;++s) for(size_t j=0;j<input;++j) {
       if(element(conjugated,s,j).isZero()) continue;
       MathStructure term=element(matrix,r,i); term*=element(conjugated,s,j);
       size_t row=choiBasis ? r+output*i : r+output*s;
       size_t column=choiBasis ? s+output*j : i+input*j;
       element(out,row,column)+=term;
      }
     }
    }
   }
   if(op=="qptm" || op=="qchi") {
    out.eval(eo);
    // Columns of the unnormalized Pauli change-of-basis matrix have d
    // nonzero entries. Exploit that sparsity instead of multiplying dense
    // d^2-by-d^2 matrices. Basis order is II, IX, IY, IZ, XI, ... .
    size_t d=input, count=d*d;
    std::vector<std::vector<size_t>> locations;std::vector<std::vector<Number>> phases;pauliBasis(d,locations,phases);
    MathStructure transformed;transformed.clearMatrix();transformed.resizeMatrix(count,count,m_zero);
    for(size_t column=0;column<count;++column) {
     if(CALCULATOR->aborted())return 0;
     std::vector<MathStructure> intermediate(count);
     for(size_t r=0;r<count;++r)for(size_t c=0;c<d;++c) {
      const MathStructure &entry=element(out,r,locations[column][c]);if(entry.isZero())continue;
      MathStructure term=entry;term*=phases[column][c];intermediate[r]+=term;
     }
     for(auto &entry:intermediate)entry.eval(eo);
     for(size_t row=0;row<count;++row) {
      MathStructure result;
      for(size_t c=0;c<d;++c) {
       MathStructure term=intermediate[locations[row][c]];if(term.isZero())continue;
       Number factor=phases[row][c];if(factor.isComplex())factor.negate();
       term*=factor;result+=term;
      }
      result/=Number(d);result.eval(eo);element(transformed,row,column)=result;
     }
    }
    out=transformed;
   }
   return 1;
  }
  return 0;
 }
};
}
void registerQuantumChannelRepresentations(Calculator &calculator) {
 for(const char *name:{"qsuperop","qchoi","qptm","qchi"})calculator.addFunction(new QuantumChannelRepresentationFunction(name));
}
