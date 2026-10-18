// GPL-2.0-or-later; see COPYING.
#include "QuantumClassicalRange.h"
#include <stdexcept>
namespace QuantumClassical {
namespace {
std::uint64_t ordered(const Integer &value) {
 // Sign extension followed by a sign-bit flip gives signed integers the same
 // monotonic unsigned ordering as nonnegative integers, even at INT64_MIN.
 const auto bits=value.cast(Integer::Signedness::Unsigned,64).bits();
 return value.signedness()==Integer::Signedness::Signed ? bits^(std::uint64_t(1)<<63) : bits;
}
}
IntegerRange::IntegerRange(Integer start,Integer stop,Integer step):
 current_(start),stop_(stop),stride_(0),descending_(step.negative()),active_(false) {
 const int order=start.compare(stop); // Also rejects endpoints not yet promoted.
 const auto bits=step.cast(Integer::Signedness::Unsigned,64).bits();
 stride_=descending_ ? std::uint64_t(0)-bits : bits;
 if(!stride_)throw std::invalid_argument("Integer range step must not be zero");
 active_=descending_ ? order>=0 : order<=0;
}
const Integer &IntegerRange::value() const {
 if(!active_)throw std::out_of_range("Integer range is exhausted");
 return current_;
}
void IntegerRange::advance() {
 if(!active_)throw std::out_of_range("Integer range is exhausted");
 const auto here=ordered(current_),end=ordered(stop_);
 const auto remaining=descending_ ? here-end : end-here;
 // Check exhaustion before adding: the successor need not fit the value type.
 if(stride_>remaining) {active_=false;return;}
 auto bits=current_.cast(Integer::Signedness::Unsigned,64).bits();
 bits=descending_ ? bits-stride_ : bits+stride_;
 current_=Integer::fromBits(Integer::Signedness::Unsigned,64,bits).cast(current_.signedness(),current_.width());
}
}
