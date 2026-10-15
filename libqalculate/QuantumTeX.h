// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_TEX_H
#define QALCULATE_QUANTUM_TEX_H
#include <string>
// Convert a mathematical TeX fragment (not a document) into quantum surface syntax.
// This internal translation step does not evaluate or fully validate that syntax.
// Throws std::runtime_error for unsupported TeX, bad grouping or resource limits.
std::string quantumTeX(const std::string &input);
#endif
