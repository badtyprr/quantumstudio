// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_SAMPLING_REQUEST_H
#define QUANTUM_SAMPLING_REQUEST_H
#include <string>
class Calculator;
// One bounded QSAMPLE1 request. Throws without writing a partial JSON response.
std::string quantumSamplingRequest(Calculator &calculator, const std::string &input);
#endif
