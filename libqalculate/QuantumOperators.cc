// GPL-2.0-or-later; see COPYING.
#include "QuantumOperators.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <utility>
namespace {
MathStructure &element(MathStructure &m,size_t r,size_t c){return *m.getElement(r+1,c+1);}
class QuantumOperatorFunction: public MathFunction {
 std::string op;
 public:
 QuantumOperatorFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumOperatorFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t k=0;k<args.size();++k)args[k].eval(eo);
  const MathStructure &a=args[0];
  if(op=="qjx" || op=="qjy" || op=="qjz" || op=="qjplus" || op=="qjminus") {
   Number twiceSpin;
   if(a.isNumber()) {twiceSpin=a.number();twiceSpin*=2;}
   if(!a.isNumber() || !twiceSpin.isInteger() || twiceSpin<1 || twiceSpin>63) {
    CALCULATOR->error(true,"Spin operators require integer or half-integer j from 1/2 to 63/2, with hbar=1 and basis m=j,j-1,...,-j.",NULL);return 0;
   }
   int twice=twiceSpin.intValue(), dimension=twice+1;
   out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
   if(op=="qjz") {
    for(int k=0;k<dimension;++k)element(out,k,k)=MathStructure(Number(twice-2*k,2));
   } else {
    for(int k=1;k<dimension;++k) {
     MathStructure value(k*(twice-k+1));value.raise(Number(1,2));
     if(op=="qjx" || op=="qjy")value*=Number(1,2);
     value.eval(eo);
     if(op=="qjy") {
      Number imaginary;imaginary.setImaginaryPart(1);value*=imaginary;value.eval(eo);
      element(out,k,k-1)=value;value*=Number(-1);value.eval(eo);element(out,k-1,k)=value;
     } else {
      if(op!="qjminus")element(out,k-1,k)=value;
      if(op!="qjplus")element(out,k,k-1)=value;
     }
    }
   }
   return 1;
  }
  if(op=="qfdestroy" || op=="qfcreate") {
   const MathStructure &site=args[1];
   if(!a.isNumber() || !a.number().isInteger() || a.number()<1 || a.number()>9 || !site.isNumber() || !site.number().isInteger() || site.number()<0 || site.number()>=a.number()) {
    CALCULATOR->error(true,"Fermionic operators require 1 to 9 modes and an integer site from 0 to modes-1 (leftmost is 0).",NULL);return 0;
   }
   size_t modes=a.number().intValue(), index=site.number().intValue(), dimension=size_t(1)<<modes, bit=size_t(1)<<(modes-1-index);
   out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
   for(size_t column=0;column<dimension;++column) {
    if(CALCULATOR->aborted())return 0;
    bool occupied=(column & bit)!=0;
    if(occupied!=(op=="qfdestroy"))continue;
    size_t prefix=column>>(modes-index);bool odd=false;
    while(prefix) {odd=!odd;prefix&=prefix-1;}
    element(out,column^bit,column)=odd ? MathStructure(-1) : m_one;
   }
   return 1;
  }
  if(op=="qdestroy" || op=="qcreate" || op=="qnumberop") {
   if(!a.isNumber() || !a.number().isInteger() || a.number()<2 || a.number()>512) {
    CALCULATOR->error(true,"Bosonic operators require an integer truncation dimension from 2 to 512.",NULL);return 0;
   }
   size_t dimension=a.number().intValue();out.clearMatrix();out.resizeMatrix(dimension,dimension,m_zero);
   for(size_t k=1;k<dimension;++k) {
    if(CALCULATOR->aborted())return 0;
    MathStructure value((int)k);
    if(op=="qnumberop")element(out,k,k)=value;
    else {
     value.raise(Number(1,2));value.eval(eo);
     element(out,op=="qdestroy" ? k-1 : k,op=="qdestroy" ? k : k-1)=value;
    }
   }
   return 1;
  }
  if(op=="qspinadd") {
   const MathStructure &b=args[1];
   if(a.isVector()!=b.isVector()) {
    const MathStructure &matrix=a.isVector() ? a : b, &scalar=a.isVector() ? b : a;
    if(!matrix.isMatrix() || matrix.rows()!=matrix.columns() || matrix.rows()>512 || !scalar.representsScalar()) {
     CALCULATOR->error(true,"In a spin expression scalar offsets require a square operator (at most 512 rows).",NULL);return 0;
    }
    out=matrix;for(size_t k=0;k<matrix.rows();++k)element(out,k,k)+=scalar;out.eval(eo);return 1;
   }
   if(a.isVector() && (a.isMatrix()!=b.isMatrix() || (a.isMatrix() ? (a.rows()!=b.rows() || a.columns()!=b.columns()) : a.size()!=b.size()))) {
    CALCULATOR->error(true,"Spin-expression addition requires matching matrix or vector dimensions.",NULL);return 0;
   }
   out=a;out+=b;out.eval(eo);return 1;
  }
  return 0;
 }
};
}
void registerQuantumOperators(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qjx",1),{"qjy",1},{"qjz",1},{"qjplus",1},{"qjminus",1},{"qfdestroy",2},{"qfcreate",2},{"qdestroy",1},{"qcreate",1},{"qnumberop",1},{"qspinadd",2}})
  calculator.addFunction(new QuantumOperatorFunction(entry.first,entry.second));
}
