// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_WIRE_SELECTION_H
#define QUANTUM_WIRE_SELECTION_H
#include "QuantumClassicalIntegerExpression.h"
#include <string>

namespace QuantumClassical {
// A finite ordered register (or alias) and a runtime index into that register.
// Mapping is explicit: noncontiguous aliases never become offset arithmetic.
class WireSelection {
public:
 struct Target {std::vector<unsigned> wires;IntegerExpression index;};
 WireSelection(const std::vector<Target> &targets,const std::string &source="");
 // Call-entry preflight spans the full register, independently of gate arity.
 static WireSelection references(const std::vector<Target> &targets,const std::string &source="");
 unsigned size() const {return static_cast<unsigned>(targets_.size());}
 // Validate references in every body without reading undefined runtime slots.
 void validate(unsigned qubits,unsigned bits,const IntegerStorage &storage) const;
 // All indices read the same pre-operation state. Reject negative/out-of-range
 // indices and physical-wire collisions before any quantum mutation.
 std::vector<unsigned> evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const;
private:
 WireSelection(const std::vector<Target> &targets,const std::string &source,unsigned limit);
 const std::vector<Target> targets_;
 const std::string source_;
 std::string diagnostic(const std::string &message) const;
};
}
#endif
