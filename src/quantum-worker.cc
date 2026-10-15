// GPL-2.0-or-later; see COPYING. One request per process, UTF-8 stdin/stdout.
#include <libqalculate/Calculator.h>
#include <libqalculate/MathStructure.h>
#include <iostream>
#include <iterator>
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
int main(int argc,char **argv) {
 bool json=false, approximate=false, probabilities=false, bloch=false;
 for(int k=1;k<argc;++k) {
  std::string argument=argv[k];
  if(argument=="--json") json=true;
  else if(argument=="--approx") approximate=true;
  else if(argument=="--probabilities") probabilities=true;
  else if(argument=="--bloch") bloch=true;
  else { std::cerr << "Usage: quantum-worker.exe [--json] [--approx] [--probabilities] [--bloch] (expression on UTF-8 stdin)"; return 2; }
 }
 Calculator calculator;
 if(!calculator.loadGlobalDefinitions()) { std::cerr << "Cannot load calculator definitions. Keep the data folder beside QuantumStudio.exe."; return 2; }
 calculator.setPrecision(30);
 std::string input((std::istreambuf_iterator<char>(std::cin)), std::istreambuf_iterator<char>());
 if(input.size()>32768) { std::cerr << "Input exceeds 32768 bytes."; return 2; }
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
   if(r) std::cout << ','; std::cout << '[';
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
