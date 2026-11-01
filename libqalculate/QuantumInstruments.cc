// GPL-2.0-or-later; see COPYING.
#include "Calculator.h"
#include "Function.h"
#include "QuantumAlgebra.h"
#include "QuantumMatrixPower.h"
#include <cmath>
#include <complex>
#include <vector>

namespace {
enum class Verdict { Valid, Invalid, Unknown };
Verdict combine(Verdict a,Verdict b) {
 if(a==Verdict::Invalid || b==Verdict::Invalid)return Verdict::Invalid;
 return a==Verdict::Unknown || b==Verdict::Unknown ? Verdict::Unknown : Verdict::Valid;
}
const MathStructure &cell(const MathStructure &a,size_t r,size_t c) {return *a.getElement(r+1,c+1);}
MathStructure &cell(MathStructure &a,size_t r,size_t c) {return *a.getElement(r+1,c+1);}
Verdict zero(MathStructure a,const EvaluationOptions &eo) {
 a.eval(eo);
 if(a.isZero())return Verdict::Valid;
 return a.representsNonZero() ? Verdict::Invalid : Verdict::Unknown;
}
Verdict normalizedZero(MathStructure value,const EvaluationOptions &eo,bool approximate) {
 Verdict result=zero(value,eo);
 if(result!=Verdict::Invalid || !approximate)return result;
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;value.eval(numeric);
 if(value.isNumber() && !value.number().isUndefined() && !value.number().isInfinite(false) &&
    std::hypot(value.number().realPart().floatValue(),value.number().imaginaryPart().floatValue())<=1e-12)return Verdict::Valid;
 return result;
}
Verdict nonnegative(const MathStructure &a) {
 if(a.isVector())return Verdict::Invalid;
 if(a.isNumber() && (a.number().isUndefined() || a.number().isInfinite(false) || !a.number().isReal()))return Verdict::Invalid;
 if(a.representsNegative())return Verdict::Invalid;
 return a.representsNonNegative() ? Verdict::Valid : Verdict::Unknown;
}
// Exact Schur complements prove positivity without rounding a negative eigenvalue
// to zero. Unknown signs stay unknown; a zero pivot requires a zero row.
Verdict positiveSemidefinite(MathStructure a,const EvaluationOptions &eo) {
 Verdict result=Verdict::Valid;
 MathStructure adjoint=quantumAdjoint(a,eo);
 for(size_t r=0;r<a.rows();++r)for(size_t c=0;c<a.columns();++c) {
  const MathStructure &v=cell(a,r,c);
  if(v.isNumber() && (v.number().isUndefined() || v.number().isInfinite(false)))return Verdict::Invalid;
  MathStructure difference=v;difference-=cell(adjoint,r,c);
  result=combine(result,zero(difference,eo));
 }
 // Inspect every diagonal and every zero-diagonal row before a symbolic
 // Schur pivot can defer the remaining factorization.
 for(size_t r=0;r<a.rows();++r) {
  result=combine(result,nonnegative(cell(a,r,r)));
  if(cell(a,r,r).isZero())for(size_t c=0;c<a.rows();++c)result=combine(result,zero(cell(a,r,c),eo));
 }
 if(result==Verdict::Invalid)return result;
 for(size_t k=0;k<a.rows();++k) {
  if(CALCULATOR->aborted())return Verdict::Unknown;
  MathStructure pivot=cell(a,k,k);pivot.eval(eo);
  result=combine(result,nonnegative(pivot));
  if(result==Verdict::Invalid)return result;
  if(pivot.isZero()) {
   for(size_t j=k+1;j<a.rows();++j)result=combine(result,zero(cell(a,k,j),eo));
  } else if(pivot.representsPositive()) {
   for(size_t r=k+1;r<a.rows();++r)for(size_t c=k+1;c<a.rows();++c) {
    MathStructure term=cell(a,r,k);term*=cell(a,k,c);term/=pivot;
    cell(a,r,c)-=term;cell(a,r,c).eval(eo);
   }
  } else result=combine(result,Verdict::Unknown);
 }
 return result;
}
bool isKind(const MathStructure &a,const char *name) {return a.isFunction() && a.function()->referenceName()==name;}
bool fail(const char *message) {CALCULATOR->error(true,message,NULL);return false;}
Verdict labelsEqual(const MathStructure &left,const MathStructure &right,const EvaluationOptions &eo) {
 if(left.equals(right))return Verdict::Valid;
 if((left.isSymbolic() || left.isNumber()) && (right.isSymbolic() || right.isNumber()))return Verdict::Invalid;
 MathStructure difference=left;difference-=right;return zero(difference,eo);
}
bool validateLabels(const MathStructure &labels,Verdict &validity,const EvaluationOptions &eo) {
 if(!labels.isVector() || labels.size()==0 || labels.size()>64)return fail("Require 1 to 64 outcome labels.");
 for(size_t k=0;k<labels.size();++k) {
  if(labels[k].isVector())return fail("Outcome labels must be scalar values or text.");
  for(size_t j=0;j<k;++j) {
   Verdict same=labelsEqual(labels[k],labels[j],eo);
   if(same==Verdict::Valid)return fail("Outcome labels must be distinct.");
   if(same==Verdict::Unknown)validity=combine(validity,Verdict::Unknown);
  }
 }
 return true;
}

bool evaluateCollection(MathStructure &value,const EvaluationOptions &eo,unsigned depth=0) {
 if(depth>32)return fail("Measurement collection nesting exceeds 32 levels.");
 value.eval(eo);
 if(value.isVector()) {
  for(size_t k=0;k<value.size();++k)if(!evaluateCollection(value[k],eo,depth+1))return false;
  value.childrenUpdated();
 }
 return true;
}
void preserveSingleton(MathStructure &value) {
 if(!value.isVector()) {MathStructure scalar=value;value.clearMatrix();value.resizeMatrix(1,1,m_zero);cell(value,0,0)=scalar;}
}
MathStructure rowMatrix(MathStructure value) {
 if(value.isVector() && !value.isMatrix()) {
  for(size_t k=0;k<value.size();++k)if(value[k].isVector())return value;
  MathStructure row;row.clearMatrix();row.resizeMatrix(1,value.size(),m_zero);
  for(size_t k=0;k<value.size();++k)cell(row,0,k)=value[k];return row;
 }
 return value;
}
struct Measurement {
 MathStructure labels;
 std::vector<MathStructure> effects;
 size_t input=0,output=0;
 bool deferred=false;
 Verdict validity=Verdict::Valid;
};
bool dimension(const MathStructure &value,Verdict &validity) {
 if(value.isNumber()) {
  if(!value.number().isInteger() || value.number()<1 || value.number()>64)return fail("Measurement dimensions must be integers from 1 to 64.");
  return true;
 }
 if(!value.representsScalar() || !value.containsUnknowns())return fail("Invalid measurement dimension.");
 validity=combine(validity,Verdict::Unknown);return true;
}
bool matchingDimension(const MathStructure &left,const MathStructure &right,Verdict &validity,const EvaluationOptions &eo) {
 MathStructure difference=left;difference-=right;Verdict result=zero(difference,eo);
 if(result==Verdict::Invalid)return fail("Measurement dimensions are incompatible.");
 validity=combine(validity,result);return true;
}
bool readMeasurement(const MathStructure &value,Measurement &m,const EvaluationOptions &eo,bool approximate) {
 bool instrument=isKind(value,"qinstrument");
 if((!instrument && !isKind(value,"qpovm")) || value.size()!=2)return fail("Expected a labeled POVM or instrument.");
 m.labels=value[0];m.labels.eval(eo);
 MathStructure members=value[1];if(!evaluateCollection(members,eo))return false;
 if(!validateLabels(m.labels,m.validity,eo))return false;
 if(!members.isVector() || members.size()!=m.labels.size())return fail("Measurements require equally many labels and outcomes.");
 MathStructure input,output;bool first=true;
 for(size_t k=0;k<m.labels.size();++k) {
  MathStructure group;if(instrument)group=members[k];else {group.clearVector();group.addChild(members[k]);}
  if(!group.isVector() || group.size()==0 || group.size()>64)return fail("Each instrument outcome requires 1 to 64 Kraus matrices.");
  MathStructure effect;bool deferredGroup=false;
  for(size_t j=0;j<group.size();++j) {
   MathStructure op=group[j];op.eval(eo);if(instrument)op=rowMatrix(op);MathStructure rows,columns;
   if(!quantumMatrixShape(op,rows,columns,eo))return fail("Measurement operators require matrices or explicit matrix declarations.");
   rows.eval(eo);columns.eval(eo);
   if(!dimension(rows,m.validity) || !dimension(columns,m.validity))return false;
   if(!instrument && !matchingDimension(rows,columns,m.validity,eo))return false;
   if(first) {input=columns;output=rows;first=false;}
   if(!matchingDimension(columns,input,m.validity,eo) || !matchingDimension(rows,output,m.validity,eo))return false;
   if(!op.isMatrix()) {m.deferred=true;deferredGroup=true;m.validity=combine(m.validity,Verdict::Unknown);continue;}
   for(size_t r=0;r<op.rows();++r)for(size_t c=0;c<op.columns();++c) {
    const MathStructure &entry=cell(op,r,c);
    if(entry.isVector() || (entry.isNumber() && (entry.number().isUndefined() || entry.number().isInfinite(false))))
     return fail("Measurement operators require finite scalar entries.");
   }
   MathStructure term=op;
   if(instrument) {term=quantumAdjoint(op,eo);term*=op;term.eval(eo);if(op.columns()==1)preserveSingleton(term);}
   if(!j)effect=term;else effect+=term;
  }
  if(deferredGroup) {m.effects.push_back(MathStructure());continue;}
  effect.eval(eo);if(input.isOne())preserveSingleton(effect);
  if(!effect.isMatrix())return fail("Measurement effects lost their matrix shape.");
  m.validity=combine(m.validity,positiveSemidefinite(effect,eo));m.effects.push_back(effect);
 }
 if(m.validity==Verdict::Invalid)return fail("Invalid measurement: an effect is not positive semidefinite.");
 if(input.isNumber())m.input=input.number().intValue();if(output.isNumber())m.output=output.number().intValue();
 if(m.deferred)return true;
 MathStructure sum=m.effects[0];for(size_t k=1;k<m.effects.size();++k)sum+=m.effects[k];sum.eval(eo);if(m.input==1)preserveSingleton(sum);
 for(size_t r=0;r<m.input;++r)for(size_t c=0;c<m.input;++c) {
  MathStructure difference=cell(sum,r,c);if(r==c)difference-=1;
  m.validity=combine(m.validity,normalizedZero(difference,eo,approximate));
 }
 if(m.validity==Verdict::Invalid)return fail("Invalid measurement: effects must sum to identity.");
 return true;
}

MathStructure product(MathStructure a,const MathStructure &b,const EvaluationOptions &eo) {
 bool singleton=a.isMatrix() && b.isMatrix() && a.rows()==1 && b.columns()==1;
 a*=b;a.eval(eo);
 if(singleton)preserveSingleton(a);
 return a;
}
MathStructure trace(const MathStructure &a,const EvaluationOptions &eo) {
 MathStructure result;for(size_t j=0;j<a.rows();++j)result+=cell(a,j,j);result.eval(eo);return result;
}
bool stateDensity(MathStructure state,MathStructure &density,size_t &dimension,Verdict &validity,const EvaluationOptions &eo,bool approximate) {
 state.eval(eo);
 if(!state.isMatrix()) {
  MathStructure rows,columns;
  if(!quantumMatrixShape(state,rows,columns,eo))return fail("A state requires a ket, density matrix or explicit matrix declaration.");
  rows.eval(eo);columns.eval(eo);
  if(!::dimension(rows,validity) || !::dimension(columns,validity))return false;
  if(dimension && !matchingDimension(rows,MathStructure(Number(dimension)),validity,eo))return false;
  if(!columns.isOne() && !matchingDimension(rows,columns,validity,eo))return false;
  if(rows.isNumber())dimension=rows.number().intValue();density=state;validity=combine(validity,Verdict::Unknown);return true;
 }
 if(!state.isMatrix() || state.rows()==0 || state.rows()>64 || (state.columns()!=1 && state.columns()!=state.rows()))return fail("A measurement state requires a ket or square density matrix of dimension 1 to 64.");
 if(dimension && dimension!=state.rows())return fail("Measurement state dimensions are incompatible.");
 dimension=state.rows();
 density=state.columns()==1 ? product(state,quantumAdjoint(state,eo),eo) : state;
 validity=combine(validity,positiveSemidefinite(density,eo));
 MathStructure norm=trace(density,eo);norm-=1;validity=combine(validity,normalizedZero(norm,eo,approximate));
 if(validity==Verdict::Invalid)return fail("Measurement states must be positive semidefinite and normalized.");
 return true;
}
bool ensemble(const MathStructure &value,MathStructure &average,Verdict &validity,const EvaluationOptions &eo,bool approximate) {
 if(!isKind(value,"qensemble") || value.size()!=3)return fail("Expected a labeled ensemble.");
 MathStructure labels=value[0],weights=value[1],states=value[2];
 if(!evaluateCollection(labels,eo) || !evaluateCollection(weights,eo) || !evaluateCollection(states,eo))return false;
 if(!validateLabels(labels,validity,eo))return false;
 if(!weights.isVector() || !states.isVector() || labels.size()!=weights.size() || labels.size()!=states.size())return fail("Ensembles require 1 to 64 labels, probabilities and states of matching lengths.");
 size_t dimension=0;MathStructure total;
 for(size_t k=0;k<labels.size();++k) {
  validity=combine(validity,nonnegative(weights[k]));total+=weights[k];
  MathStructure density;if(!stateDensity(states[k],density,dimension,validity,eo,approximate))return false;
  density*=weights[k];if(!k)average=density;else average+=density;
 }
 total-=1;validity=combine(validity,normalizedZero(total,eo,approximate));average.eval(eo);
 if(validity==Verdict::Invalid)return fail("Ensemble probabilities must be nonnegative and sum to one.");
 return true;
}
bool branches(const MathStructure &measurement,const Measurement &m,const MathStructure &state,MathStructure &probabilities,MathStructure &states,const EvaluationOptions &eo,Verdict &validity,bool approximate) {
 size_t dimension=m.input;MathStructure density;
 if(!stateDensity(state,density,dimension,validity,eo,approximate))return false;
 probabilities.clearVector();states.clearVector();
 MathStructure groups;if(isKind(measurement,"qinstrument")) {groups=measurement[1];if(!evaluateCollection(groups,eo))return false;}
 for(size_t k=0;k<m.effects.size();++k) {
  probabilities.addChild(trace(product(m.effects[k],density,eo),eo));
  if(groups.isVector()) {
   MathStructure branch;
   for(size_t j=0;j<groups[k].size();++j) {
    MathStructure op=groups[k][j];op.eval(eo);op=rowMatrix(op);
    MathStructure term=product(product(op,density,eo),quantumAdjoint(op,eo),eo);
    if(!j)branch=term;else branch+=term;
   }
   branch.eval(eo);states.addChild(branch);
  }
 }
 return true;
}

bool numericCompletion(MathStructure &out,size_t columns,const EvaluationOptions &eo) {
 using Complex=std::complex<double>;size_t size=out.rows();std::vector<Complex> u(size*size);
 EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
 for(size_t r=0;r<size;++r)for(size_t c=0;c<columns;++c) {
  MathStructure value=cell(out,r,c);value.eval(numeric);
  if(!value.isNumber() || value.number().isUndefined() || value.number().isInfinite(false))return false;
  Number real=value.number().realPart(),imag=value.number().imaginaryPart();
  if((real.isInterval() && !real.intervalToPrecision(10)) || (imag.isInterval() && !imag.intervalToPrecision(10)))return fail("Naimark roots have unresolved numerical uncertainty.");
  u[r*size+c]=Complex(real.floatValue(),imag.floatValue());
 }
 for(size_t seed=0;seed<size && columns<size;++seed) {
  if(CALCULATOR->aborted())return false;
  std::vector<Complex> v(size);v[seed]=1;
  for(unsigned pass=0;pass<2;++pass)for(size_t c=0;c<columns;++c) {
   Complex overlap=0;for(size_t r=0;r<size;++r)overlap+=std::conj(u[r*size+c])*v[r];
   for(size_t r=0;r<size;++r)v[r]-=overlap*u[r*size+c];
  }
  double norm=0;for(auto z:v)norm+=std::norm(z);
  if(norm<1e-24)continue;
  norm=std::sqrt(norm);for(size_t r=0;r<size;++r)u[r*size+columns]=v[r]/norm;++columns;
 }
 if(columns!=size)return fail("Naimark numerical completion is rank deficient.");
 for(size_t a=0;a<size;++a)for(size_t b=0;b<size;++b) {
  Complex inner=0;for(size_t r=0;r<size;++r)inner+=std::conj(u[r*size+a])*u[r*size+b];
  if(!std::isfinite(std::abs(inner)) || std::abs(inner-Complex(a==b ? 1 : 0))>1e-10)return fail("Naimark numerical completion is not unitary within 1e-10.");
 }
 for(size_t r=0;r<size;++r)for(size_t c=0;c<size;++c) {
  Number real,imag;real.setFloat(u[r*size+c].real());imag.setFloat(u[r*size+c].imag());real.setImaginaryPart(imag);real.setApproximate(true);real.setPrecision(10);cell(out,r,c)=real;
 }
 out.setApproximate(true,true);return true;
}
bool effectRoot(MathStructure &root,const MathStructure &effect,const EvaluationOptions &eo) {
 if(effect.rows()==2) {
  MathStructure determinant=cell(effect,0,0);determinant*=cell(effect,1,1);
  MathStructure off=cell(effect,0,1);off*=cell(effect,1,0);determinant-=off;determinant.eval(eo);
  if(determinant.representsNonNegative()) {
   determinant.raise(Number(1,2));determinant.eval(eo);
   MathStructure scale=trace(effect,eo);scale+=determinant;scale+=determinant;scale.eval(eo);
   if(scale.isZero()) {root=effect;return true;}
   if(scale.representsPositive()) {
    scale.raise(Number(1,2));scale.eval(eo);root=effect;
    cell(root,0,0)+=determinant;cell(root,1,1)+=determinant;root/=scale;root.eval(eo);return true;
   }
  }
 }
 return quantumMatrixPower(root,effect,MathStructure(Number(1,2)),eo);
}
// Ancilla is the first tensor factor. The first input-dimension columns
// implement the initialized ancilla; the rest are completed by two-pass MGS.
bool naimark(MathStructure &out,const Measurement &m,size_t ancilla,const EvaluationOptions &eo) {
 size_t size=ancilla*m.input;
 out.clearMatrix();out.resizeMatrix(size,size,m_zero);bool approximateRoots=false;
 for(size_t k=0;k<m.effects.size();++k) {
  MathStructure root;
  if(!effectRoot(root,m.effects[k],eo))return false;
  if(!root.isMatrix())return false;
  approximateRoots|=root.isApproximate();
  for(size_t r=0;r<m.input;++r)for(size_t c=0;c<m.input;++c)cell(out,k*m.input+r,c)=cell(root,r,c);
 }
 if(approximateRoots)return numericCompletion(out,m.input,eo);
 size_t columns=m.input;
 for(size_t seed=0;seed<size && columns<size;++seed) {
  if(CALCULATOR->aborted())return false;
  std::vector<MathStructure> v(size);v[seed]=1;
  for(unsigned pass=0;pass<2;++pass)for(size_t c=0;c<columns;++c) {
   MathStructure overlap;
   for(size_t r=0;r<size;++r) {
    MathStructure conjugate(CALCULATOR->getFunction("conj"),&cell(out,r,c),NULL);conjugate.eval(eo);
    conjugate*=v[r];overlap+=conjugate;
   }
   overlap.eval(eo);
   for(size_t r=0;r<size;++r) {MathStructure term=cell(out,r,c);term*=overlap;v[r]-=term;v[r].eval(eo);}
  }
  MathStructure norm;
  for(const auto &component:v) {
   MathStructure conjugate(CALCULATOR->getFunction("conj"),&component,NULL);conjugate.eval(eo);
   conjugate*=component;norm+=conjugate;
  }
  norm.eval(eo);
  if(norm.isZero())continue;
  if(norm.isNumber() && norm.number().isApproximate() && norm.number().isReal() && std::abs(norm.number().floatValue())<1e-24)continue;
  if(!norm.representsPositive())return false;
  norm.raise(Number(1,2));norm.eval(eo);
  for(size_t r=0;r<size;++r) {v[r]/=norm;v[r].eval(eo);cell(out,r,columns)=v[r];}
  ++columns;
 }
 if(columns!=size)return fail("Naimark unitary completion did not find a complete orthonormal basis.");
 MathStructure gram=product(quantumAdjoint(out,eo),out,eo);
 for(size_t r=0;r<size;++r)for(size_t c=0;c<size;++c) {
  MathStructure difference=cell(gram,r,c);if(r==c)difference-=1;difference.eval(eo);
  if(difference.isZero())continue;
  EvaluationOptions numerical=eo;numerical.approximation=APPROXIMATION_APPROXIMATE;difference.eval(numerical);
  if(!difference.isNumber() || difference.number().isUndefined() || difference.number().isInfinite(false) ||
     std::hypot(difference.number().realPart().floatValue(),difference.number().imaginaryPart().floatValue())>1e-10)
   return fail("Naimark unitary completion failed its orthonormality check.");
 }
 return true;
}
class MeasurementValue: public MathFunction {
 std::string kind;
public:
 MeasurementValue(const char *name,int count):MathFunction(name,count),kind(name) {}
 ExpressionItem *copy() const {return new MeasurementValue(*this);}
 bool representsScalar(const MathStructure&) const {return kind=="qmeasurementvalid";}
 bool representsNonMatrix(const MathStructure&) const {return kind=="qmeasurementvalid";}
 bool preservesSingletonMatrix() const {return true;}
 int calculate(MathStructure &out,const MathStructure &raw,const EvaluationOptions &options) {
  const bool approximate=options.approximation==APPROXIMATION_APPROXIMATE;
  EvaluationOptions eo=options;eo.approximation=APPROXIMATION_EXACT;
  MathStructure value;
  bool constructor=kind=="qpovm" || kind=="qinstrument" || kind=="qensemble";
  bool changed=false;
  if(constructor) {
   value=MathStructure(static_cast<MathFunction*>(this),static_cast<MathStructure*>(NULL));
   for(size_t k=0;k<raw.size();++k) {MathStructure argument=raw[k];if(!evaluateCollection(argument,eo))return 0;changed|=!argument.equals(raw[k]);value.addChild(argument);}
  }
  else value=raw[0];

  if(kind=="qensemble" || kind=="qensembleaverage" || kind=="qensemblevalid") {
   Verdict validity=Verdict::Valid;MathStructure average;
   if(!ensemble(value,average,validity,eo,approximate))return 0;
   if(constructor) {if(!changed)return 0;out=value;return 1;}
   if(validity!=Verdict::Valid)return 0;
   if(kind=="qensemblevalid")out=1;else out=average;return 1;
  }
  Measurement m;if(!readMeasurement(value,m,eo,approximate))return 0;
  if(constructor) {if(!changed)return 0;out=value;return 1;} // Keep every unresolved obligation.
  if(kind=="qmeasurementvalid") {if(m.validity!=Verdict::Valid)return 0;out=1;return 1;}
  if(kind=="qoutcomelabels") {if(m.validity!=Verdict::Valid)return 0;out=m.labels;return 1;}
  if(kind=="qeffects") {if(m.validity!=Verdict::Valid)return 0;out.clearVector();for(const auto &effect:m.effects)out.addChild(effect);return 1;}

  if(kind=="qnaimark") {
   MathStructure ancilla=raw[1];ancilla.eval(eo);
   if(!ancilla.isNumber() && ancilla.representsScalar() && ancilla.containsUnknowns())return 0;
   if(!ancilla.isNumber() || !ancilla.number().isInteger() || ancilla.number()<Number(m.effects.size()) || ancilla.number()>64 || ancilla.number()*Number(m.input)>128) {
    fail("Naimark ancilla dimension must be an integer at least the outcome count, at most 64, with total dimension at most 128.");return 0;
   }
   if(m.validity!=Verdict::Valid)return 0;
   return naimark(out,m,ancilla.number().intValue(),eo) ? 1 : 0;
  }
  if(kind=="qprobabilities" || kind=="qbranches" || kind=="qpoststate") {
   if(kind!="qprobabilities" && !isKind(value,"qinstrument")) {fail("Post-measurement states require an instrument; a POVM alone does not specify them.");return 0;}
   MathStructure probabilities,states;Verdict validity=m.validity;
   if(m.deferred) {size_t dim=m.input;MathStructure density;stateDensity(raw[1],density,dim,validity,eo,approximate);return 0;}
   if(!branches(value,m,raw[1],probabilities,states,eo,validity,approximate))return 0;
   if(validity!=Verdict::Valid)return 0;
   if(kind=="qprobabilities") {out=probabilities;return 1;}
   if(kind=="qbranches") {
    out.clearVector();
    for(size_t k=0;k<m.labels.size();++k) {MathStructure row;row.clearVector();row.addChild(m.labels[k]);row.addChild(probabilities[k]);row.addChild(states[k]);out.addChild(row);}
    return 1;
   }
   MathStructure label=raw[2];label.eval(eo);
   if(label.isVector()) {fail("An outcome selector must be a scalar value or text.");return 0;}
   bool unknownMatch=false;
   for(size_t k=0;k<m.labels.size();++k)unknownMatch|=labelsEqual(label,m.labels[k],eo)==Verdict::Unknown;
   for(size_t k=0;k<m.labels.size();++k)if(labelsEqual(label,m.labels[k],eo)==Verdict::Valid) {
    if(probabilities[k].isZero()) {fail("A zero-probability outcome has no normalized post-measurement state.");return 0;}
    if(!probabilities[k].representsPositive())return 0;
    out=states[k];out/=probabilities[k];out.eval(eo);return 1;
   }
   if(unknownMatch)return 0;
   fail("The requested outcome label is not present in this instrument.");return 0;
  }
  return 0;
 }
};
}
void registerQuantumInstruments(Calculator &calculator) {
 for(const auto &entry:{std::pair<const char *,int>("qpovm",2),{"qinstrument",2},{"qmeasurementvalid",1},{"qoutcomelabels",1},{"qeffects",1},{"qensemble",3},{"qensembleaverage",1},{"qensemblevalid",1},{"qprobabilities",2},{"qbranches",2},{"qpoststate",3},{"qnaimark",2}})
  calculator.addFunction(new MeasurementValue(entry.first,entry.second));
}

