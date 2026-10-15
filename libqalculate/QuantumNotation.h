// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_NOTATION_H
#define QALCULATE_QUANTUM_NOTATION_H
#include <string>
// Internal translation only; evaluating the output requires quantum functions.
// Returns the byte offset after a leading quantum: marker, or zero if absent.
size_t quantumPrefixLength(const std::string &expression);
// Throws std::runtime_error on malformed input or resource-limit violations.
std::string translateQuantum(const std::string &expression);
#endif
