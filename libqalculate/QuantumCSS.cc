// GPL-2.0-or-later; see COPYING.
#include "QuantumCSS.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <vector>
#include <utility>
namespace {
const MathStructure &element(const MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
MathStructure &element(MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
unsigned binaryParity(size_t value) {unsigned parity=0;while(value){parity^=1;value&=value-1;}return parity;}
bool binaryMatrix(const MathStructure &a,std::vector<std::vector<unsigned char>> &matrix) {
 size_t rows=a.isMatrix() ? a.rows() : 1, columns=a.isMatrix() ? a.columns() : a.isVector() ? a.size() : 1;
 if(rows==0 || columns==0 || rows>128 || columns>128) {CALCULATOR->error(true,"GF(2) operations require a nonempty matrix with at most 128 rows and columns.",NULL);return false;}
 matrix.assign(rows,std::vector<unsigned char>(columns));
 for(size_t r=0;r<rows;++r)for(size_t c=0;c<columns;++c) {
  const MathStructure &value=a.isMatrix() ? element(a,r,c) : a.isVector() ? a[c] : a;
  if(!value.isNumber() || (!value.number().isZero() && !value.number().isOne())) {CALCULATOR->error(true,"GF(2) matrix entries must be 0 or 1.",NULL);return false;}
  matrix[r][c]=value.number().isOne() ? 1 : 0;
 }
 return true;
}
class QuantumCSSFunction: public MathFunction {
 std::string op;
 public:
 QuantumCSSFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumCSSFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t j=0;j<args.size();++j)args[j].eval(eo);
  if(op=="qcssgenerators" || op=="qcssstate" || op=="qcssencoder") {
   std::vector<std::vector<unsigned char>> checks[2];
   for(size_t kind=0;kind<2;++kind) {
    if(args[kind].isVector() && args[kind].size()==0)continue;
    if(!binaryMatrix(args[kind],checks[kind]))return 0;
   }
   size_t count=checks[0].size()+checks[1].size();
   if(count==0 || count>32) {CALCULATOR->error(true,"CSS construction requires 1 to 32 total check rows; either X or Z checks may be empty, but not both.",NULL);return 0;}
   size_t n=checks[0].empty() ? checks[1][0].size() : checks[0][0].size();
   if(n<1 || n>9 || (!checks[0].empty() && !checks[1].empty() && checks[1][0].size()!=n)) {CALCULATOR->error(true,"CSS check matrices must have the same 1 to 9 columns, one per qubit.",NULL);return 0;}
   for(const auto &x:checks[0])for(const auto &z:checks[1]) {
    unsigned parity=0;for(size_t j=0;j<n;++j)parity^=x[j]&z[j];
    if(parity) {CALCULATOR->error(true,"CSS checks must satisfy Hx Hz^T = 0 over GF(2), so every X check commutes with every Z check.",NULL);return 0;}
   }
   size_t d=size_t(1)<<n;
   if(op=="qcssstate" || op=="qcssencoder") {
    size_t u=0;
    if(op=="qcssstate") {
     if(!args[2].isNumber() || !args[2].number().isInteger() || args[2].number()<0 || args[2].number()>=Number(d)) {CALCULATOR->error(true,"A CSS coset representative must be an integer basis index from 0 to 2^n-1.",NULL);return 0;}
     u=args[2].number().intValue();
    }
    for(const auto &row:checks[1]) {
     size_t mask=0;for(auto bit:row)mask=(mask<<1)|bit;
     if(binaryParity(u&mask)) {CALCULATOR->error(true,"The CSS coset representative must satisfy every Z parity check.",NULL);return 0;}
    }
    std::vector<size_t> span(1,0);std::vector<bool> present(d,false);present[0]=true;
    for(const auto &row:checks[0]) {
     if(CALCULATOR->aborted())return 0;
     size_t mask=0;for(auto bit:row)mask=(mask<<1)|bit;
     size_t old_size=span.size();for(size_t j=0;j<old_size;++j) {
      size_t word=span[j]^mask;if(!present[word]) {present[word]=true;span.push_back(word);}
     }
    }
    MathStructure amplitude{Number(span.size())};amplitude.raise(Number(-1,2));amplitude.eval(eo);
    if(op=="qcssencoder") {
     std::vector<size_t> logical,closure=span;
     // Canonical quotient basis: greedily extend the X row space using
     // ascending integer words in ker(Hz). Earlier words label lower bits.
     for(size_t candidate=1;candidate<d;++candidate) {
      if(CALCULATOR->aborted())return 0;
      if(present[candidate])continue;
      bool allowed=true;
      for(const auto &row:checks[1]) {
       size_t mask=0;for(auto bit:row)mask=(mask<<1)|bit;
       if(binaryParity(candidate&mask)) {allowed=false;break;}
      }
      if(!allowed)continue;
      logical.push_back(candidate);size_t old_size=closure.size();
      for(size_t j=0;j<old_size;++j) {size_t word=closure[j]^candidate;present[word]=true;closure.push_back(word);}
     }
     size_t columns=size_t(1)<<logical.size();out.clearMatrix();out.resizeMatrix(d,columns,m_zero);
     for(size_t column=0;column<columns;++column) {
      size_t representative=0;for(size_t j=0;j<logical.size();++j)if(column&(size_t(1)<<j))representative^=logical[j];
      for(size_t word:span)element(out,representative^word,column)=amplitude;
     }
     return 1;
    }
    out.clearMatrix();out.resizeMatrix(d,1,m_zero);
    for(size_t word:span)element(out,u^word,0)=amplitude;
    return 1;
   }
   out.clearVector();
   for(size_t kind=0;kind<2;++kind)for(const auto &row:checks[kind]) {
    if(CALCULATOR->aborted())return 0;
    size_t mask=0;for(auto bit:row)mask=(mask<<1)|bit;
    MathStructure generator;generator.clearMatrix();generator.resizeMatrix(d,d,m_zero);
    for(size_t r=0;r<d;++r) {
     if(kind==0)element(generator,r,r^mask)=m_one;
     else element(generator,r,r)=MathStructure(binaryParity(r&mask) ? -1 : 1);
    }
    out.addChild(generator);
   }
   return 1;
  }
  return 0;
 }
};
}
void registerQuantumCSS(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qcssgenerators",2),{"qcssstate",3},{"qcssencoder",2}})calculator.addFunction(new QuantumCSSFunction(entry.first,entry.second));
}
