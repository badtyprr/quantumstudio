#include "QuantumStabilizer.h"
// GPL-2.0-or-later; see COPYING. One request per process, UTF-8 stdin/stdout.
#include <libqalculate/Calculator.h>
#include <libqalculate/MathStructure.h>
#include <libqalculate/Function.h>
#include <libqalculate/Variable.h>
#include <libqalculate/Unit.h>
#include <libqalculate/Prefix.h>
#include <libqalculate/QuantumIndexed.h>
#include <libqalculate/QuantumNotation.h>
#include <libqalculate/QuantumTeX.h>
#include <stdexcept>
#include "quantum-sampling-request.h"
#include "quantum-exact-request.h"
#include "quantum-display.h"
#include <set>
#ifdef _WIN32
#include <io.h>
#include <fcntl.h>
#endif
#include <iostream>
#include <algorithm>
#include <cmath>
#include <iomanip>
#include <vector>
static void jsonString(const std::string &s) {
 const char *hex="0123456789abcdef";
 std::cout << '"';
 for(unsigned char c:s) {
  if(c=='"' || c=='\\') std::cout << '\\' << c;
  else if(c<32) std::cout << "\\u00" << hex[c>>4] << hex[c&15];
  else std::cout << c;
 }
 std::cout << '"';
}
static std::string copyText(const MathStructure &,const PrintOptions &,bool quantumMode=false,bool explicitEntries=false);
static std::string copyCollection(const MathStructure &value,const PrintOptions &po,unsigned depth,bool quantumMode) {
 if(!value.isVector())return copyText(value,po,quantumMode);
 std::string text="vector(";
 for(size_t k=0;k<value.size();++k) {if(k)text+=",";text+=depth>1 ? copyCollection(value[k],po,depth-1,quantumMode) : copyText(value[k],po,quantumMode);}
 return text+")";
}
// When formatting changes 2^(-m) into (1/2)^m, juxtaposition such as
// i(1/2)^m can re-enter as (i/2)^m. Keep powers separate from other factors.
static bool needsProductSign(const MathStructure &value) {
 for(size_t k=0;k<value.size();++k) {
  const MathStructure &factor=value[k];
  if(value.isMultiplication() && factor.isPower())return true;
  if(needsProductSign(factor))return true;
 }
 return false;
}
static std::string copyScalar(MathStructure value,PrintOptions po) {
 if(needsProductSign(value))po.short_multiplication=false;
 value.format(po);return value.print(po);
}
// A complete basis has a short, dimension-preserving representation even
// when writing out every zero would exceed the input limit on re-entry.
static bool completeComputationalBasis(const MathStructure &states) {
 if(!states.isVector() || !states.size() || states.isApproximate())return false;
 const size_t dimension=states.size();
 std::vector<bool> seen(dimension,false);
 for(size_t k=0;k<dimension;++k) {
  const MathStructure &ket=states[k];
  if(!ket.isMatrix() || ket.rows()!=dimension || ket.columns()!=1)return false;
  size_t label=dimension;
  for(size_t r=0;r<dimension;++r) {
   const MathStructure &cell=*ket.getElement(r+1,1);
   if(cell.isZero())continue;
   if(label!=dimension || !cell.isOne())return false;
   label=r;
  }
  if(label==dimension || seen[label])return false;
  seen[label]=true;
 }
 return true;
}
static bool containsDeferredQuantum(const MathStructure &value,bool orderedOnly=false) {
 if(value.isFunction()) {
  const std::string &name=value.function()->referenceName();
  if(orderedOnly ? (name=="qnamedket" || name=="qdag" || name=="qtensor" || name=="qadjacent")
                 : name.compare(0,1,"q")==0)return true;
 }
 for(size_t k=0;k<value.size();++k)if(containsDeferredQuantum(value[k],orderedOnly))return true;
 return false;
}
static std::string copyText(const MathStructure &result, const PrintOptions &po,bool quantumMode,bool explicitEntries) {
 // Identify physical units and prefixes separately from quantum variables.
 if(quantumMode && result.isUnit()) {
  const std::string prefix=result.prefix() ? result.prefix()->referenceName() : "";
  return "qphysicalunit(\""+result.unit()->referenceName()+"\",\""+prefix+"\")";
 }
 // Explicit dimensions preserve singleton matrices; commas cannot be mistaken
 // for implicit multiplication by the quantum parser.
 bool scalarMatrix=result.isMatrix();
 if(quantumMode && scalarMatrix) {
  std::string compact=quantumPauliTensorNotation(result);
  if(!compact.empty())return compact;
 }
 if(scalarMatrix)for(size_t r=1;r<=result.rows();++r)for(size_t c=1;c<=result.columns();++c)
  if(result.getElement(r,c)->isVector())scalarMatrix=false;
 // A vector of equal-sized matrices also satisfies isMatrix(). Keep these
 // collections nested instead of flattening their rows into matrix cells.
 if(!scalarMatrix) {
  // Deferred operations retain nested vectors and matrix constructors.
  // Serialize every function argument recursively so their separators survive
  // copy/re-entry even when no typed binary label occurs in the expression.
  if(result.isFunction()) {
   const std::string name=result.function()->referenceName();
   if(quantumMode && name=="qset" && result.size()==1 && completeComputationalBasis(result[0]))
    return "basisset("+std::to_string(result[0].size())+")";
   // A deferred exponent can contain an already parsed scalar product.
   // Explicit multiplication preserves its factors on the first re-entry.
   if(name=="qpower" && result.size()==2 && result[1].isMultiplication() && result[1].size()>=2) {
    std::vector<std::string> factors;bool scalar=true;
    for(size_t k=0;k<result[1].size();++k) {
     scalar=scalar && result[1][k].representsScalar();
     factors.push_back(copyText(result[1][k],po,quantumMode));
    }
    // Equal-status scalar variables can have different internal orders
    // in fresh worker processes. Preserve a reproducible clipboard spelling.
    if(scalar)std::sort(factors.begin(),factors.end());
    std::string exponent;
    for(size_t k=1;k<factors.size();++k)exponent+="qmul(";
    exponent+=factors[0];
    for(size_t k=1;k<factors.size();++k)exponent+=","+factors[k]+")";
    return "qpower("+copyText(result[0],po,quantumMode)+","+exponent+")";
   }
   if((name=="qpovm" || name=="qinstrument") && result.size()==2)
    return name+"("+copyCollection(result[0],po,1,quantumMode)+","+copyCollection(result[1],po,name=="qinstrument" ? 2 : 1,quantumMode)+")";
   if(name=="qensemble" && result.size()==3)
    return name+"("+copyCollection(result[0],po,1,quantumMode)+","+copyCollection(result[1],po,1,quantumMode)+","+copyCollection(result[2],po,1,quantumMode)+")";
   // Quantum input resolves the public matrix constructor to qmatrix on re-entry.
   std::string text=(name=="qmatrix" ? "matrix" : name)+"(";
   for(size_t k=0;k<result.size();++k) {
    if(k)text+=",";
    const bool entries=explicitEntries || name=="qtensor" || name=="qmember" || ((name=="qmatrix" || name=="matrix") && k==2);
    text+=copyText(result[k],po,quantumMode,entries);
   }
   return text+")";
  }
  if(result.isVector()) {
   std::string text="vector(";
   for(size_t k=0;k<result.size();++k) {if(k)text+=",";text+=copyText(result[k],po,quantumMode,explicitEntries);}
   return text+")";
  }
  if(result.isLogicalAnd() || result.isLogicalOr()) {
   // Word operators also re-enter in Quantum mode, where || delimits a norm.
   const char *separator=result.isLogicalAnd() ? " and " : " or ";
   std::vector<std::string> terms;
   for(size_t k=0;k<result.size();++k)terms.push_back(copyText(result[k],po,quantumMode));
   // Simplification may reorder these commutative terms between worker processes.
   std::sort(terms.begin(),terms.end());
   std::string text="(";
   for(size_t k=0;k<terms.size();++k) {
    if(k)text+=separator;
    text+=terms[k];
   }
   return text+")";
  }
  if(quantumMode && result.type()==STRUCT_LOGICAL_NOT && result.size()==1)
   return "!("+copyText(result[0],po,true)+")";
  if(result.isComparison() && result.size()==2) {
   const char *comparison="==";
   switch(result.comparisonType()) {
    case COMPARISON_LESS:comparison="<";break;
    case COMPARISON_GREATER:comparison=">";break;
    case COMPARISON_EQUALS_LESS:comparison="<=";break;
    case COMPARISON_EQUALS_GREATER:comparison=">=";break;
    case COMPARISON_NOT_EQUALS:comparison="!=";break;
    case COMPARISON_EQUALS:break;
   }
   return "("+copyText(result[0],po,quantumMode)+")"+comparison+"("+copyText(result[1],po,quantumMode)+")";
  }
  if(quantumMode && explicitEntries && result.isPower() && result.size()==2)
   return "qpower("+copyText(result[0],po,true,true)+","+copyText(result[1],po,true,true)+")";
  if(quantumMode && (result.isAddition() || result.isMultiplication()) && result.size()>1 &&
     (explicitEntries || result.containsType(STRUCT_VECTOR) || containsDeferredQuantum(result,true))) {
   const std::string op=result.isAddition() ? "qadd(" : "qmul(";
   std::string text=copyText(result[0],po,true,true);
   for(size_t k=1;k<result.size();++k)text=op+text+","+copyText(result[k],po,true,true)+")";
   return text;
  }
  // Arithmetic can enclose unevaluated matrix-valued states. Formatting the
  // whole expression would lose explicit comma-separated matrix dimensions.
  if((result.isAddition() || result.isMultiplication() || result.isPower()) &&
     (result.containsType(STRUCT_VECTOR) || (quantumMode && result.containsType(STRUCT_UNIT)))) {
   std::string text="(";
   const char *separator=result.isAddition() ? ")+ (" : result.isMultiplication() ? ")*(" : ")^(";
   std::vector<std::string> terms;
   bool scalarProduct=quantumMode && result.isMultiplication();
   for(size_t k=0;k<result.size();++k) {
    terms.push_back(copyText(result[k],po,quantumMode));
    scalarProduct=scalarProduct && result[k].representsScalar();
   }
   if(scalarProduct)std::sort(terms.begin(),terms.end());
   for(size_t k=0;k<terms.size();++k) {if(k)text+=separator;text+=terms[k];}
   return text+")";
  }
  return copyScalar(result,po);
 }
 if(result.rows()==1 && result.columns()==1)
  return "qmul(("+copyText(*result.getElement(1,1),po,quantumMode)+"),qbasis(0,1))";
 bool useVector=explicitEntries;
 if(quantumMode && !useVector)useVector=containsDeferredQuantum(result);
 std::string text="matrix("+std::to_string(result.rows())+","+std::to_string(result.columns())+(useVector ? ",vector(" : ",[");
 for(size_t r=1;r<=result.rows();++r)for(size_t c=1;c<=result.columns();++c) {
  if(r!=1 || c!=1)text+=",";
  const MathStructure &cell=*result.getElement(r,c);
  text+=quantumMode && (useVector || cell.containsType(STRUCT_UNIT)) ? copyText(cell,po,quantumMode,useVector) : copyScalar(cell,po);
 }
 return text+(useVector ? "))" : "])");
}
// Keep ordered lists of states distinct from both sets and matrices.
static bool displayKetCollection(const MathStructure &value,const PrintOptions &po,std::string &shown) {
 bool set=value.isFunction() && value.function()->referenceName()=="qset" && value.size()==1;
 const MathStructure &entries=set ? value[0] : value;
 if(!entries.isVector() || entries.size()==0)return false;
 bool hasState=false;
 std::string text=set ? "\\{" : "vector(";
 for(size_t k=0;k<entries.size();++k) {
  const MathStructure &member=entries[k];
  bool basis=member.containsFunction(CALCULATOR->getFunction("qbasis"));
  bool state=basis || (member.isMatrix() && (set || member.columns()==1)) || (member.isFunction() && member.function()->referenceName()=="qketstate");
  if(!set && !state)return false;
  hasState=hasState || state;
  if(k)text+=", ";
  if(basis || (member.isMatrix() && member.rows()==1))text+=copyText(member,po);
  else {MathStructure display=member;display.format(po);text+=QuantumDisplay::print(display,po);}
 }
 if(hasState)shown=text+(set ? "\\}" : ")");
 return hasState;
}
// Decimal matching needs the numeric components before formatting splits a
// complex number into a display sum or rewrites a negative precision flag.
static bool decimalMatch(const MathStructure &value) {
 return value.isFunction() && value.function()->referenceName()=="qdecimalmatch";
}
static bool messages(Calculator &calculator) {
 bool failed=false;
 while(calculator.message()) {
  if(calculator.message()->type()==MESSAGE_ERROR)failed=true;
  std::cerr << calculator.message()->message() << '\n';calculator.nextMessage();
 }
 return failed;
}
// Lengths count UTF-8 bytes, not characters. Never parse lengths with an
// unbounded allocation or permit a definition to consume the next record.
static size_t fieldSize(const std::string &input,size_t &position,size_t maximum) {
 size_t value=0, start=position;
 while(position<input.size() && input[position]!='\n') {
  unsigned char c=input[position++];
  if(c<'0' || c>'9' || position-start>7)throw std::runtime_error("Invalid state request length.");
  value=value*10+c-'0';
  if(value>maximum)throw std::runtime_error("State request field exceeds its limit.");
 }
 if(position==start || position==input.size())throw std::runtime_error("Truncated state request length.");
 ++position;return value;
}
static void defineStates(Calculator &calculator,std::string &input) {
 const std::string magic="QSTATES1\n";
 if(input.compare(0,magic.size(),magic)!=0)throw std::runtime_error("Expected QSTATES1 state request.");
 size_t position=magic.size(),count=fieldSize(input,position,32);
 std::set<std::string> names;
 EvaluationOptions exact;exact.approximation=APPROXIMATION_EXACT;
 for(size_t k=0;k<count;++k) {
  size_t nameSize=fieldSize(input,position,128),expressionSize=fieldSize(input,position,32768);
  if(!nameSize || !expressionSize || nameSize+expressionSize>input.size()-position)throw std::runtime_error("Empty or truncated state definition.");
  std::string name=input.substr(position,nameSize);position+=nameSize;
  std::string expression=input.substr(position,expressionSize);position+=expressionSize;
  if(expression.find('\0')!=std::string::npos)throw std::runtime_error("State definitions cannot contain NUL.");
  if(name.find_first_of("\r\n\t")!=std::string::npos || name.find('\0')!=std::string::npos || name.front()==' ' || name.back()==' ' || !names.insert(name).second || calculator.getActiveVariable(name))throw std::runtime_error("Duplicate, reserved, or invalid state name: "+name);
  std::string familyName,labelName=name;std::vector<MathStructure> parameters;std::vector<bool> complexParameters;
  std::vector<Variable*> bindings,previousVariables;std::vector<Unit*> previousUnits;
  size_t open=name.find('(');
  if(open!=std::string::npos) {
   if(open==0 || name.back()!=')')throw std::runtime_error("Use name(parameters) for a state family.");
   familyName=name.substr(0,open);std::string list=name.substr(open+1,name.size()-open-2);
   std::vector<std::string> parameterNames;std::set<std::string> unique;
   size_t start=0;
   do {
    size_t comma=list.find(',',start);std::string part=list.substr(start,comma==std::string::npos ? comma : comma-start);
    size_t first=part.find_first_not_of(' '),last=part.find_last_not_of(' ');part=first==std::string::npos ? "" : part.substr(first,last-first+1);
    bool complex=false;size_t colon=part.find(':');
    if(colon!=std::string::npos) {
     std::string domain=part.substr(colon+1);size_t begin=domain.find_first_not_of(' '),end=domain.find_last_not_of(' ');
     domain=begin==std::string::npos ? "" : domain.substr(begin,end-begin+1);
     if(domain!="complex")throw std::runtime_error("Use parameter:complex for a complex state-family amplitude.");
     part=part.substr(0,colon);size_t endName=part.find_last_not_of(' ');part=endName==std::string::npos ? "" : part.substr(0,endName+1);complex=true;
    }
    complexParameters.push_back(complex);
    if(!unique.insert(part).second)throw std::runtime_error("State-family parameters must be distinct.");
    parameterNames.push_back(part);if(parameterNames.size()>16)throw std::runtime_error("State families support at most 16 parameters.");
    if(comma==std::string::npos)break;start=comma+1;
   }while(true);
   labelName=familyName+"(";
   for(size_t j=0;j<parameterNames.size();++j) {if(j)labelName+=",";labelName+=parameterNames[j];}
   labelName+=")";
   std::vector<std::string> identifiers=parameterNames;identifiers.push_back(familyName);
   for(const std::string &part:identifiers) {
    if(part.empty() || std::isdigit((unsigned char)part.front()))throw std::runtime_error("Family names and parameters must be identifiers.");
    for(unsigned char c:part)if(c<128 && !std::isalnum(c) && c!='_')throw std::runtime_error("Family names and parameters must be identifiers.");
   }
   if(!names.insert("family:"+familyName).second)throw std::runtime_error("Duplicate state family.");
   for(const auto &parameterName:parameterNames) {
    Variable *previous=calculator.getActiveVariable(parameterName);Unit *unit=calculator.getActiveUnit(parameterName);
    if(previous)previous->setActive(false);if(unit)unit->setActive(false);
    previousVariables.push_back(previous);previousUnits.push_back(unit);
    Variable *binding=new UnknownVariable("",parameterName);calculator.addVariable(binding,false,false);bindings.push_back(binding);
    MathStructure parameter=calculator.calculate("quantum: "+parameterName,exact);
    bool local=(parameter.isVariable() && parameter.variable()==binding) || (parameter.isSymbolic() && parameter.symbol()==parameterName);
    if(messages(calculator) || !local)throw std::runtime_error("A family parameter must be an unambiguous scalar variable.");
    parameters.push_back(parameter);
   }
  }
  // Validate a declaration's spelling before evaluation can resolve it through
  // an earlier state family (for example a fixed psi_t after psi(alpha)).
  MathStructure label=familyName.empty() ? calculator.parse("quantum: |"+name+">",exact.parse_options) : calculator.calculate("quantum: |"+labelName+">",exact);
  if(familyName.empty() && label.isFunction() && label.function()->referenceName()=="qnamedket" && label.size()==1) {
   MathStructure text=label[0];label.set(calculator.getFunction("qketstate"),&text,NULL);
  }
  if(messages(calculator) || !label.isFunction() || (familyName.empty() ? label.function()->referenceName()!="qketstate" || label.size()!=1 || !label[0].isSymbolic() || label[0].symbol()!=name : label.function()->referenceName()!=(parameters.size()==1 ? "qstatecall" : "qstatecalls") || label.size()!=2 || label[0].symbol()!=familyName))throw std::runtime_error("State name must be an unambiguous named ket label: "+name);
  MathStructure state=calculator.parse("quantum: "+expression,exact.parse_options);
  for(size_t j=0;j<parameters.size();++j)if(complexParameters[j])declareQuantumComplexParameter(calculator,state,parameters[j]);
  state.eval(exact);
  if(messages(calculator) || !state.isMatrix() || state.columns()!=1 || state.rows()==0 || state.rows()>1024)throw std::runtime_error("State "+name+" must resolve to a column vector of at most 1024 rows. Define referenced states earlier; unknown or cyclic references are not allowed.");
  for(size_t r=1;r<=state.rows();++r) {
   const MathStructure &cell=*state.getElement(r,1);
   if(!cell.representsScalar() || cell.isUndefined() || (cell.isNumber() && cell.number().isInfinite(false)))throw std::runtime_error("State amplitudes must be finite scalar expressions: "+name);
  }
  if(familyName.empty())calculator.addVariable(new KnownVariable("",name,state));
  else {
   defineQuantumStateFamily(calculator,familyName,state,parameters);
   for(size_t k=bindings.size();k>0;--k) {
    bindings[k-1]->setActive(false);if(previousVariables[k-1])previousVariables[k-1]->setActive(true);
    if(previousUnits[k-1])previousUnits[k-1]->setActive(true);
   }
  }
 }
 input.erase(0,position);
 if(input.empty() || input.size()>32768 || input.find('\0')!=std::string::npos)throw std::runtime_error("State request expression must contain 1 to 32768 bytes without NUL.");
}
int main(int argc,char **argv) {
 bool json=false, approximate=false, probabilities=false, bloch=false, states=false, sample=false, exactCircuit=false;
 for(int k=1;k<argc;++k) {
  std::string argument=argv[k];
  if(argument=="--json") json=true;
  else if(argument=="--approx") approximate=true;
  else if(argument=="--probabilities") probabilities=true;
  else if(argument=="--bloch") bloch=true;
  else if(argument=="--states") states=true;
  else if(argument=="--sample") sample=true;
  else if(argument=="--exact-circuit") exactCircuit=true;
  else { std::cerr << "Usage: quantum-worker.exe [--json] [--approx] [--probabilities] [--bloch] [--states] or --sample or --exact-circuit (expression or structured request on UTF-8 stdin)"; return 2; }
 }
 if(sample && argc!=2) {std::cerr << "--sample is a separate request mode; do not combine flags.";return 2;}
 if(exactCircuit && argc!=2) {std::cerr << "--exact-circuit is a separate request mode; do not combine flags.";return 2;}
#ifdef _WIN32
 if((states || sample || exactCircuit) && _setmode(_fileno(stdin),_O_BINARY)==-1) {std::cerr << "Cannot open binary state input.";return 2;}
#endif
 std::string input;input.reserve(32768);char byte;bool prefixChecked=false;
 while(std::cin.get(byte)) {
  if(input.size()==((states || sample || exactCircuit) ? 1100000U : 32768U)) {std::cerr << ((states || sample || exactCircuit) ? "Structured request exceeds 1100000 bytes." : "Input exceeds 32768 bytes.");return 2;}
  input.push_back(byte);
  // .NET Framework's redirected stdin writer can emit a UTF-8 preamble.
  // Remove it only at the transport boundary, before applying payload limits.
  if(!prefixChecked && input.size()==3) {
   prefixChecked=true;
   if(input.compare(0,3,"\xEF\xBB\xBF")==0)input.clear();
  }
 }
 if(std::cin.bad()) {std::cerr << "Cannot read expression from stdin.";return 2;}
 Calculator calculator;
 if(!calculator.loadGlobalDefinitions()) { std::cerr << "Cannot load calculator definitions. Keep the data folder beside QuantumStudio.exe."; return 2; }
 calculator.setPrecision(30);
 if(exactCircuit)try {std::cout << quantumExactRequest(calculator,input) << std::endl;return 0;}
 catch(const std::exception &error){std::cerr << error.what() << '\n';return 2;}
 if(sample)try {std::cout << quantumSamplingRequest(calculator,input) << std::endl;return 0;}
 catch(const std::exception &error){std::cerr << error.what() << '\n';return 2;}
 if(states)try {defineStates(calculator,input);}catch(const std::exception &error){std::cerr << error.what() << '\n';return 2;}
 EvaluationOptions eo;
 eo.approximation=approximate ? APPROXIMATION_APPROXIMATE : APPROXIMATION_EXACT;
 std::vector<std::string> independentLines;
 size_t quantumStart=quantumPrefixLength(input);
 if(quantumStart && input.find("\\begin")!=std::string::npos)try {
  quantumTeX(input.substr(quantumStart),&independentLines);
 } catch(const std::exception &error) {std::cerr << error.what() << '\n';return 2;}
 MathStructure result=calculator.calculate(input,eo);
 bool failed=false;
 while(calculator.message()) {
  if(calculator.message()->type()==MESSAGE_ERROR) failed=true;
  std::cerr << calculator.message()->message() << '\n'; calculator.nextMessage();
 }
 if(failed || result.isUndefined()) return 2;
 bool multipleLines=independentLines.size()>1;
 if(multipleLines && (!result.isVector() || result.size()!=independentLines.size())) {
  std::cerr << "The calculation did not preserve the independent expressions.";return 2;
 }
 PrintOptions po; po.use_unicode_signs=true;
 // Exact set elements and chained equalities must retain rational operands
 // when their decimal expansions would require rounding.
 if(result.isFunction() && !result.isApproximate() && (result.function()->referenceName()=="qset" ||
    result.function()->referenceName()=="qequalchain")) {
  po.number_fraction_format=FRACTION_FRACTIONAL;po.restrict_fraction_length=false;
 }
 if(approximate) po.interval_display=INTERVAL_DISPLAY_SIGNIFICANT_DIGITS;
 // Wide Pauli tables have compact exact forms. Formatting each dense zero
 // before replacing the text can exhaust the interactive calculation deadline.
 std::vector<std::string> pauliLines;
 if(json && multipleLines)for(size_t i=0;i<result.size();++i) {
  if(!result[i].isMatrix()) {pauliLines.clear();break;}
  std::string word=quantumPauliTensorNotation(result[i]);
  if(word.empty()) {pauliLines.clear();break;}
  pauliLines.push_back(word);
 }
 MathStructure display;
 if(pauliLines.empty()) {display=result;display.format(po);}
 if(!json) std::cout << display.print(po) << std::endl;
 else {
  size_t rows=!multipleLines && result.isMatrix() ? result.rows() : 0, cols=!multipleLines && result.isMatrix() ? result.columns() : 0;
  std::string plain=pauliLines.empty() ? display.print(po) : "";
  std::string shown;
  if(multipleLines)for(size_t i=0;i<result.size();++i) {
   if(i)shown+="\n\n";
   if(!pauliLines.empty()) {shown+=std::to_string(i+1)+".  "+pauliLines[i];continue;}
   MathStructure line=result[i];if(!decimalMatch(line))line.format(po);
   std::string lineDisplay=QuantumDisplay::print(line,po);
   if(lineDisplay.size()>32768 && !result[i].isApproximate()) {
    PrintOptions exact=po;exact.number_fraction_format=FRACTION_FRACTIONAL;exact.restrict_fraction_length=false;
    std::string compact=copyText(result[i],exact,true);
    if(compact.size()<32768)lineDisplay=compact;
   }
   shown+=std::to_string(i+1)+".  "+lineDisplay;
  } else if(displayKetCollection(result,po,shown))rows=cols=0;
  else shown=QuantumDisplay::print(decimalMatch(result) ? result : display,po);
  if(!pauliLines.empty() || (multipleLines && plain.size()>32768 && shown.size()<32768))plain=shown;
  std::cout << "{\"text\":"; jsonString(plain);
  std::cout << ",\"display_text\":"; jsonString(shown);
  // Clipboard serialization must preserve rational values even when their
  // display is a rounded decimal. Decimal-exact mode still limits long
  // denominators, so use unrestricted fractions for this serialization.
  PrintOptions copyOptions=po;
  copyOptions.number_fraction_format=FRACTION_FRACTIONAL;
  copyOptions.restrict_fraction_length=false;
  std::string copied;
  if(multipleLines) {
   copied="\\begin{gathered}";
   for(size_t i=0;i<result.size();++i) {if(i)copied+="\\\\";copied+=pauliLines.empty() ? copyText(result[i],copyOptions,true) : pauliLines[i];}
   copied+="\\end{gathered}";
  } else copied=copyText(result,copyOptions,quantumStart!=0);
  std::cout << ",\"copy_text\":"; jsonString(copied);
  std::cout << ",\"approximate\":" << (result.isApproximate() ? "true" : "false") << ",\"rows\":" << rows << ",\"columns\":" << cols << ",\"cells\":[";
  if(rows*cols<=128) for(size_t r=0;r<rows;++r) {
   if(r) std::cout << ',';
   std::cout << '[';
   for(size_t c=0;c<cols;++c) {
    if(c) std::cout << ',';
    MathStructure cell=*result.getElement(r+1,c+1); cell.format(po); jsonString(cell.print(po));
   }
   std::cout << ']';
  }
  std::cout << "],\"probabilities\":[";
  if(probabilities && cols==1 && rows>=2 && rows<=64) {
   std::vector<double> values;double sum=0;bool valid=true;
   EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
   calculator.beginTemporaryStopMessages();
   for(size_t r=0;r<rows;++r) {
    MathStructure value=*result.getElement(r+1,1);value.eval(numeric);
    if(!value.isNumber() || value.number().isComplex() || value.number().isUndefined() || value.number().isInfinite(false)) {valid=false;break;}
    Number number=value.number();
    if(number.isInterval() && !number.intervalToPrecision(12)) {valid=false;break;}
    double probability=number.floatValue();
    if(!std::isfinite(probability) || probability<0 || probability>1) {valid=false;break;}
    values.push_back(probability);sum+=probability;
   }
   calculator.endTemporaryStopMessages(false);
   if(valid && std::abs(sum-1)<1e-9)for(size_t r=0;r<values.size();++r) {if(r)std::cout << ',';std::cout << std::setprecision(17) << values[r];}
  }
  std::cout << "],\"bloch\":[";
  if(bloch && rows==3 && cols==1) {
   std::vector<double> values;double lengthSquared=0;bool valid=true;
   EvaluationOptions numeric=eo;numeric.approximation=APPROXIMATION_APPROXIMATE;
   calculator.beginTemporaryStopMessages();
   for(size_t r=0;r<3;++r) {
    MathStructure value=*result.getElement(r+1,1);value.eval(numeric);
    if(!value.isNumber() || value.number().isComplex() || value.number().isUndefined() || value.number().isInfinite(false)) {valid=false;break;}
    Number number=value.number();
    if(number.isInterval() && !number.intervalToPrecision(12)) {valid=false;break;}
    double coordinate=number.floatValue();if(!std::isfinite(coordinate)) {valid=false;break;}
    values.push_back(coordinate);lengthSquared+=coordinate*coordinate;
   }
   calculator.endTemporaryStopMessages(false);
   if(valid && lengthSquared<=1+1e-10)for(size_t r=0;r<3;++r) {if(r)std::cout << ',';std::cout << std::setprecision(17) << values[r];}
  }
  std::cout << "]}" << std::endl;
 }
 return 0;
}
