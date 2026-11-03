// GPL-2.0-or-later; see COPYING. Standalone diagnostic, not a product fast path.
#include "Calculator.h"
#include "QuantumNotation.h"
#include <chrono>
#include <iostream>
#include <stdexcept>

using Clock = std::chrono::steady_clock;
static double seconds(Clock::time_point start) {
 return std::chrono::duration<double>(Clock::now()-start).count();
}
int main() { try {
 Calculator calculator;
 if(!calculator.loadGlobalDefinitions())throw std::runtime_error("Definitions unavailable");
 EvaluationOptions options;options.approximation=APPROXIMATION_EXACT;
 for(int repetition=1;repetition<=2;++repetition) {
  for(const char *expression : {"qidentity(512)","pauli(\"IIIIIIXII\")","pauli(\"IIIIIIYII\")"}) {
   auto start=Clock::now();
   MathStructure left=calculator.calculate(translateQuantum(expression),options);
   MathStructure right=calculator.calculate(translateQuantum(expression),options);
   double construction=seconds(start);
   if(!left.isMatrix() || left.rows()!=512 || left.columns()!=512 || !right.equals(left))
    throw std::runtime_error("Constructor shape/value mismatch");
   start=Clock::now();
   MathStructure result=left;result*=right;result.eval(options);
   double multiplication=seconds(start);
   if(!result.isMatrix() || result.rows()!=512 || result.columns()!=512 || result.isApproximate())
    throw std::runtime_error("Product shape/approximation mismatch");
   for(size_t r=0;r<512;++r)for(size_t c=0;c<512;++c)
    if(!result[r][c].equals(r==c ? m_one : m_zero) || result[r][c].isApproximate())
     throw std::runtime_error("Full exact identity mismatch");
   start=Clock::now();
   std::string formatted=result.print();
   double formatting=seconds(start);
   std::cout<<repetition<<'\t'<<expression<<'\t'<<construction<<'\t'<<multiplication<<'\t'<<formatting<<'\t'<<formatted.size()<<std::endl;
  }
 }
 return 0;
} catch(const std::exception &error) {std::cerr<<error.what()<<std::endl;return 1;} }
