// GPL-2.0-or-later; see COPYING.
#include "QuantumStabilizer.h"
#include "Calculator.h"
#include "Function.h"
#include <string>
#include <vector>
#include <utility>
namespace {
const MathStructure &element(const MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
MathStructure &element(MathStructure &m,size_t r,size_t c) {return *m.getElement(r+1,c+1);}
unsigned binaryParity(size_t value) {unsigned parity=0;while(value){parity^=1;value&=value-1;}return parity;}
struct SignedPauli {size_t x=0,z=0,d=0;unsigned phase=0;};
Number pauliPhase(unsigned phase) {
 Number value;
 if(phase%2)value.setImaginaryPart(phase%4==1 ? 1 : -1);
 else value=phase%4==0 ? 1 : -1;
 return value;
}
bool readSignedPauli(const MathStructure &matrix,SignedPauli &out,bool hermitian) {
 if(!matrix.isMatrix() || matrix.rows()!=matrix.columns() || matrix.rows()<2 || matrix.rows()>512 || (matrix.rows()&(matrix.rows()-1)))return false;
 out=SignedPauli();out.d=matrix.rows();bool found=false;
 for(size_t c=0;c<out.d;++c) {
  const MathStructure &v=element(matrix,0,c);if(!v.isNumber())return false;
  if(!v.number().isZero()) {if(found)return false;found=true;out.x=c;bool unit=false;for(unsigned p=0;p<4;++p)if(v.number().equals(pauliPhase(p))){out.phase=p;unit=true;break;}if(!unit)return false;}
 }
 if(!found)return false;
 for(size_t bit=1;bit<out.d;bit<<=1) {
  const MathStructure &v=element(matrix,bit,bit^out.x);if(!v.isNumber())return false;
  if(v.number().equals(pauliPhase(out.phase+2)))out.z|=bit;
  else if(!v.number().equals(pauliPhase(out.phase)))return false;
 }
 for(size_t r=0;r<out.d;++r) {
  if(CALCULATOR->aborted())return false;
  Number expected=pauliPhase(out.phase+2*binaryParity(r&out.z));
  for(size_t c=0;c<out.d;++c) {const MathStructure &v=element(matrix,r,c);if(!v.isNumber() || (c==(r^out.x) ? !v.number().equals(expected) : !v.number().isZero()))return false;}
 }
 return !hermitian || (out.phase+binaryParity(out.x&out.z))%2==0;
}
SignedPauli multiplyPauli(const SignedPauli &a,const SignedPauli &b) {
 SignedPauli result;result.d=a.d;result.x=a.x^b.x;result.z=a.z^b.z;result.phase=(a.phase+b.phase+2*binaryParity(a.x&b.z))%4;return result;
}
bool stabilizerGenerators(const MathStructure &input,std::vector<SignedPauli> &generators,size_t &rank) {
 std::vector<MathStructure> matrices;
 if(input.isMatrix() && input.rows()>0 && input.columns()>0 && element(input,0,0).isNumber())matrices.push_back(input);
 else if(input.isVector() && input.size()>0 && input.size()<=32)for(size_t k=0;k<input.size();++k)matrices.push_back(input[k]);
 else {CALCULATOR->error(true,"Stabilizers require one Pauli matrix or a nonempty vector of at most 32 Pauli matrices.",NULL);return false;}
 for(const auto &matrix:matrices) {
  SignedPauli p;if(!readSignedPauli(matrix,p,true) || (!generators.empty() && p.d!=generators[0].d)) {CALCULATOR->error(true,"Stabilizer generators must be Hermitian signed Pauli matrices on the same 1 to 9 qubits.",NULL);return false;}
  for(const auto &previous:generators)if(binaryParity((p.x&previous.z)^(p.z&previous.x))) {CALCULATOR->error(true,"Stabilizer generators must commute.",NULL);return false;}
  generators.push_back(p);
 }
 size_t bits=0;while((size_t(1)<<bits)<generators[0].d)++bits;
 std::vector<SignedPauli> basis(2*bits);std::vector<bool> present(2*bits,false);rank=0;
 for(auto p:generators) {
  for(size_t column=2*bits;column-->0;) {
   size_t word=p.x|(p.z<<bits);if(!(word&(size_t(1)<<column)))continue;
   if(present[column])p=multiplyPauli(p,basis[column]);
   else {basis[column]=p;present[column]=true;++rank;break;}
  }
  if(!p.x && !p.z && p.phase) {CALCULATOR->error(true,"The generators contain -I in their group and have no common +1 eigenspace.",NULL);return false;}
 }
 return true;
}
class QuantumStabilizerFunction: public MathFunction {
 std::string op;
 public:
 QuantumStabilizerFunction(const char *name,int count):MathFunction(name,count),op(name) {}
 ExpressionItem *copy() const {return new QuantumStabilizerFunction(*this);}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &eo) {
  MathStructure args=raw;for(size_t j=0;j<args.size();++j)args[j].eval(eo);
  const MathStructure &a=args[0];
  if(op=="qpauliword") {
   for(size_t j=0;j<4;++j)if(!args[j].isNumber() || !args[j].number().isInteger() || args[j].number()<0 || args[j].number()>511) {
    CALCULATOR->error(true,"Invalid binary Pauli word parameters.",NULL);return 0;
   }
   size_t n=a.number().intValue(),x=args[1].number().intValue(),z=args[2].number().intValue();unsigned phase=args[3].number().intValue();
   if(n<1 || n>9 || phase>3 || x>=(size_t(1)<<n) || z>=(size_t(1)<<n)) {CALCULATOR->error(true,"Binary Pauli words require 1 to 9 qubits, bounded bit masks and a phase from 0 to 3.",NULL);return 0;}
   size_t d=size_t(1)<<n;out.clearMatrix();out.resizeMatrix(d,d,m_zero);
   for(size_t r=0;r<d;++r) {
    if(CALCULATOR->aborted())return 0;
    element(out,r,r^x)=MathStructure(pauliPhase(phase+2*binaryParity(r&z)));
   }
   return 1;
  }
  if(op=="qstabilizerprojector" || op=="qstabilizerdimension" || op=="qstabilizersyndrome" || op=="qstabilizerdistance" || op=="qstabilizerparameters" || op=="qstabilizercorrection") {
   std::vector<SignedPauli> generators;size_t rank=0;if(!stabilizerGenerators(a,generators,rank))return 0;
   size_t d=generators[0].d;
   if(op=="qstabilizerdimension") {out=MathStructure((int)(d>>rank));return 1;}
   if(op=="qstabilizercorrection") {
    const MathStructure &syndrome=args[1];std::vector<unsigned> bits;
    if(syndrome.isNumber() && generators.size()==1) {
     if(syndrome.number().equals(0))bits.push_back(0);
     else if(syndrome.number().equals(1))bits.push_back(1);
    } else if(syndrome.isVector() && syndrome.size()==generators.size()) {
     for(size_t j=0;j<syndrome.size();++j) {
      if(!syndrome[j].isNumber())break;
      if(syndrome[j].number().equals(0))bits.push_back(0);
      else if(syndrome[j].number().equals(1))bits.push_back(1);
      else break;
     }
    }
    if(bits.size()!=generators.size()) {CALCULATOR->error(true,"A correction syndrome requires one exact 0 or 1 per generator, in generator order (a scalar for one generator).",NULL);return 0;}
    size_t n=0;while((size_t(1)<<n)<d)++n;
    size_t best=d*d,best_weight=n+1;
    // Ties use increasing x|(z<<n); enumerate all candidates to prove minimum weight.
    for(size_t word=0;word<d*d && best_weight>0;++word) {
     if(CALCULATOR->aborted())return 0;
     size_t x=word&(d-1),z=word>>n,support=x|z,weight=0;
     while(support) {support&=support-1;++weight;}
     if(weight>=best_weight)continue;
     bool matches=true;
     for(size_t j=0;j<generators.size();++j)if(binaryParity((x&generators[j].z)^(z&generators[j].x))!=bits[j]) {matches=false;break;}
     if(matches) {best=word;best_weight=weight;}
    }
    if(best==d*d) {CALCULATOR->error(true,"The syndrome is inconsistent with the stabilizer generators (including redundant or identity checks).",NULL);return 0;}
    size_t x=best&(d-1),z=best>>n,ys=x&z;unsigned phase=0;
    while(ys) {ys&=ys-1;phase+=3;}
    out.clearMatrix();out.resizeMatrix(d,d,m_zero);
    for(size_t r=0;r<d;++r)element(out,r,r^x)=MathStructure(pauliPhase(phase+2*binaryParity(r&z)));
    return 1;
   }
   if(op=="qstabilizerdistance" || op=="qstabilizerparameters") {
    size_t n=0;while((size_t(1)<<n)<d)++n;
    if(rank==n) {CALCULATOR->error(true,"Logical code distance requires at least one encoded qubit (k > 0); stabilizer-state distance conventions are not used.",NULL);return 0;}
    // Ignore phases for membership: any scalar multiple of a stabilizer acts trivially.
    std::vector<size_t> basis(2*n,0);
    for(const auto &p:generators) {
     size_t word=p.x|(p.z<<n);
     for(size_t bit=2*n;bit-->0;)if(word&(size_t(1)<<bit)) {
      if(basis[bit])word^=basis[bit];else {basis[bit]=word;break;}
     }
    }
    size_t distance=n+1;
    for(size_t word=1;word<d*d && distance>1;++word) {
     if(CALCULATOR->aborted())return 0;
     size_t x=word&(d-1),z=word>>n,support=x|z,weight=0;
     while(support) {support&=support-1;++weight;}
     if(weight>=distance)continue;
     bool commutes=true;for(const auto &p:generators)if(binaryParity((x&p.z)^(z&p.x))) {commutes=false;break;}
     if(!commutes)continue;
     size_t remainder=word;
     for(size_t bit=2*n;bit-->0;)if(remainder&(size_t(1)<<bit))remainder^=basis[bit];
     if(remainder)distance=weight;
    }
    if(distance>n)return 0;
    if(op=="qstabilizerdistance")out=MathStructure((int)distance);
    else {out.clearVector();out.addChild(MathStructure((int)n));out.addChild(MathStructure((int)(n-rank)));out.addChild(MathStructure((int)distance));}
    return 1;
   }
   if(op=="qstabilizersyndrome") {
    SignedPauli error;if(!readSignedPauli(args[1],error,false) || error.d!=d) {CALCULATOR->error(true,"The error must be a Pauli matrix on the same qubits as the stabilizers.",NULL);return 0;}
    out.clearVector();for(const auto &p:generators)out.addChild(MathStructure((int)binaryParity((p.x&error.z)^(p.z&error.x))));return 1;
   }
   std::vector<Number> values(d*d);for(size_t r=0;r<d;++r)values[r*d+r]=1;
   for(const auto &p:generators) {
    std::vector<Number> previous=values;
    for(size_t r=0;r<d;++r) {
     if(CALCULATOR->aborted())return 0;
     Number phase=pauliPhase(p.phase+2*binaryParity(r&p.z));
     for(size_t c=0;c<d;++c) {Number term=previous[(r^p.x)*d+c];term*=phase;values[r*d+c]+=term;values[r*d+c]/=2;}
    }
   }
   out.clearMatrix();out.resizeMatrix(d,d,m_zero);for(size_t r=0;r<d;++r)for(size_t c=0;c<d;++c)element(out,r,c)=MathStructure(values[r*d+c]);return 1;
  }
  return 0;
 }
};
}
void registerQuantumStabilizer(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qpauliword",4),{"qstabilizerprojector",1},{"qstabilizerdimension",1},{"qstabilizersyndrome",2},{"qstabilizerdistance",1},{"qstabilizerparameters",1},{"qstabilizercorrection",2}})calculator.addFunction(new QuantumStabilizerFunction(entry.first,entry.second));
}
