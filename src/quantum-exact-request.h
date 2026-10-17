// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_EXACT_REQUEST_H
#define QUANTUM_EXACT_REQUEST_H
#include <string>
class Calculator;
// Bounded QEXACT1 request, all-or-nothing JSON response. See exact-circuit-protocol.md.
std::string quantumExactRequest(Calculator &calculator,const std::string &input);
#endif
