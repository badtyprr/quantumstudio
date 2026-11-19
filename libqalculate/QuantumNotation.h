// GPL-2.0-or-later; see COPYING.
#ifndef QALCULATE_QUANTUM_NOTATION_H
#define QALCULATE_QUANTUM_NOTATION_H
#include <string>
#include <vector>
// A single-letter function applied to input-size variables has a formal
// argument list. The variables themselves still support implicit products.
inline bool quantumSizeApplication(const std::string &name,const std::vector<std::string> &arguments) {
 if(name.size()!=1 || name[0]<'a' || name[0]>'z' || name.find_first_of("einkm")!=std::string::npos || arguments.empty())return false;
 for(const auto &arg:arguments)if(arg!="n" && arg!="m" && arg!="k")return false;
 return true;
}
// Internal translation only; evaluating the output requires quantum functions.
// Returns the byte offset after a leading quantum: marker, or zero if absent.
size_t quantumPrefixLength(const std::string &expression);
// Throws std::runtime_error on malformed input or resource-limit violations.
std::string translateQuantum(const std::string &expression);
#endif
