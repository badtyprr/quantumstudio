// GPL-2.0-or-later; see COPYING. One request per process, UTF-8 stdin/stdout.
#include <libqalculate/Calculator.h>
#include <libqalculate/MathStructure.h>
#include <libqalculate/Function.h>
#include <libqalculate/Variable.h>
#include <stdexcept>
#include <set>
#ifdef _WIN32
#include <io.h>
#include <fcntl.h>
#endif
#include <iostream>
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
  MathStructure label=calculator.calculate("quantum: |"+name+">",exact);
  if(messages(calculator) || !label.isFunction() || label.function()->referenceName()!="qketstate" || label.size()!=1 || !label[0].isSymbolic() || label[0].symbol()!=name)throw std::runtime_error("State name must be an unambiguous named ket label: "+name);
  MathStructure state=calculator.calculate("quantum: "+expression,exact);
  if(messages(calculator) || !state.isMatrix() || state.columns()!=1 || state.rows()==0 || state.rows()>1024)throw std::runtime_error("State "+name+" must resolve to a column vector of at most 1024 rows. Define referenced states earlier; unknown or cyclic references are not allowed.");
  for(size_t r=1;r<=state.rows();++r) {
   const MathStructure &cell=*state.getElement(r,1);
   if(!cell.representsScalar() || cell.isUndefined() || (cell.isNumber() && cell.number().isInfinite(false)))throw std::runtime_error("State amplitudes must be finite scalar expressions: "+name);
  }
  calculator.addVariable(new KnownVariable("",name,state));
 }
 input.erase(0,position);
 if(input.empty() || input.size()>32768 || input.find('\0')!=std::string::npos)throw std::runtime_error("State request expression must contain 1 to 32768 bytes without NUL.");
}
int main(int argc,char **argv) {
 bool json=false, approximate=false, probabilities=false, bloch=false, states=false;
 for(int k=1;k<argc;++k) {
  std::string argument=argv[k];
  if(argument=="--json") json=true;
  else if(argument=="--approx") approximate=true;
  else if(argument=="--probabilities") probabilities=true;
  else if(argument=="--bloch") bloch=true;
  else if(argument=="--states") states=true;
  else { std::cerr << "Usage: quantum-worker.exe [--json] [--approx] [--probabilities] [--bloch] [--states] (expression or state request on UTF-8 stdin)"; return 2; }
 }
#ifdef _WIN32
 if(states && _setmode(_fileno(stdin),_O_BINARY)==-1) {std::cerr << "Cannot open binary state input.";return 2;}
#endif
 std::string input;input.reserve(32768);char byte;
 while(std::cin.get(byte)) {
  if(input.size()==(states ? 1100000U : 32768U)) {std::cerr << (states ? "State request exceeds 1100000 bytes." : "Input exceeds 32768 bytes.");return 2;}
  input.push_back(byte);
 }
 if(std::cin.bad()) {std::cerr << "Cannot read expression from stdin.";return 2;}
 Calculator calculator;
 if(!calculator.loadGlobalDefinitions()) { std::cerr << "Cannot load calculator definitions. Keep the data folder beside QuantumStudio.exe."; return 2; }
 calculator.setPrecision(30);
 if(states)try {defineStates(calculator,input);}catch(const std::exception &error){std::cerr << error.what() << '\n';return 2;}
 EvaluationOptions eo;
 eo.approximation=approximate ? APPROXIMATION_APPROXIMATE : APPROXIMATION_EXACT;
 MathStructure result=calculator.calculate(input,eo);
 bool failed=false;
 while(calculator.message()) {
  if(calculator.message()->type()==MESSAGE_ERROR) failed=true;
  std::cerr << calculator.message()->message() << '\n'; calculator.nextMessage();
 }
 if(failed || result.isUndefined()) return 2;
 PrintOptions po; po.use_unicode_signs=true;
 if(approximate) po.interval_display=INTERVAL_DISPLAY_SIGNIFICANT_DIGITS;
 MathStructure display=result; display.format(po);
 if(!json) std::cout << display.print(po) << std::endl;
 else {
  size_t rows=result.isMatrix() ? result.rows() : 0, cols=result.isMatrix() ? result.columns() : 0;
  std::cout << "{\"text\":"; jsonString(display.print(po));
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
