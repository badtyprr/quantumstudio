// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_TEX_H
#define QALCULATE_QUANTUM_TEX_H
#include <string>
#include <vector>
// Convert a mathematical TeX fragment (not a document) into quantum surface syntax.
// This internal translation step does not evaluate or fully validate that syntax.
// Throws std::runtime_error for unsupported TeX, bad grouping or resource limits.
std::string quantumTeX(const std::string &input);
// Reports independent expressions only when the whole fragment is an alignment.
// Embedded alignments remain ordinary mathematical operands.
std::string quantumTeX(const std::string &input, std::vector<std::string> *lines);
#endif
