// GPL-2.0-or-later; see COPYING.
#ifndef QUANTUM_CLASSICAL_RANGE_H
#define QUANTUM_CLASSICAL_RANGE_H
#include "QuantumClassicalInteger.h"
namespace QuantumClassical {
// Inclusive integer range with captured endpoints and an independent cursor.
// The caller promotes endpoints to one type, converts each yielded value to
// the loop binding, and owns execution budgets/cancellation. The step may have
// a different integer type, including a negative signed step for unsigned bounds.
class IntegerRange {
public:
 IntegerRange(Integer start,Integer stop,Integer step);
 bool hasValue() const {return active_;}
 const Integer &value() const;
 void advance();
private:
 Integer current_,stop_;
 std::uint64_t stride_;
 bool descending_,active_;
};
}
#endif
