#include "QuantumNumericalState.h"
#include <cmath>
#include <limits>

namespace QuantumNumerics {
namespace {
void checkCancellation(const Cancellation &cancelled) {
 if(cancelled && cancelled()) throw Cancelled();
}
}
StateVector::StateVector(unsigned qubits, std::size_t byteBudget,
                         const Cancellation &cancelled) : qubits_(qubits) {
 if(qubits > 25 || qubits >= std::numeric_limits<std::size_t>::digits)
  throw std::invalid_argument("Numerical states support 0 to 25 qubits");
 const std::size_t count = std::size_t(1) << qubits;
 if(count > byteBudget / sizeof(Complex))
  throw std::length_error("Numerical state exceeds its memory budget");
 checkCancellation(cancelled);
 amplitudes_.resize(count);
 checkCancellation(cancelled);
 amplitudes_[0] = 1;
}
void StateVector::requireValid() const {
 if(!valid_) throw std::logic_error("Cancelled numerical state cannot be reused");
}
Complex StateVector::amplitude(std::size_t index) const {
 requireValid();return amplitudes_.at(index);
}
double StateVector::normSquared() const {
 requireValid();long double sum = 0;
 for(const auto &a : amplitudes_) sum += std::norm(a);
 return double(sum);
}
void StateVector::apply(const std::vector<Complex> &unitary,
                         const std::vector<unsigned> &wires,
                         const Cancellation &cancelled) {
 requireValid();
 if(wires.empty() || wires.size() > 3)
  throw std::invalid_argument("Local unitary needs one to three wires");
 const std::size_t dimension = std::size_t(1) << wires.size();
 if(unitary.size() != dimension * dimension)
  throw std::invalid_argument("Local unitary dimensions do not match its wires");
 std::size_t mask = 0, bits[3];
 for(std::size_t j = 0; j < wires.size(); ++j) {
  if(wires[j] >= qubits_) throw std::out_of_range("Numerical gate wire is outside the register");
  bits[j] = std::size_t(1) << (qubits_ - 1 - wires[j]);
  if(mask & bits[j]) throw std::invalid_argument("Numerical gate wires must be distinct");
  mask |= bits[j];
 }
 for(const auto &a : unitary)
  if(!std::isfinite(a.real()) || !std::isfinite(a.imag()))
   throw std::invalid_argument("Local unitary entries must be finite");
 for(std::size_t a = 0; a < dimension; ++a) for(std::size_t b = 0; b < dimension; ++b) {
  Complex inner = 0;
  for(std::size_t r = 0; r < dimension; ++r)
   inner += std::conj(unitary[r*dimension+a]) * unitary[r*dimension+b];
  if(!std::isfinite(std::abs(inner)) || std::abs(inner - Complex(a == b ? 1 : 0)) > 1e-12)
   throw std::invalid_argument("Local matrix is not unitary within numerical tolerance");
 }
 checkCancellation(cancelled);
 std::size_t offsets[8] = {};
 for(std::size_t k = 0; k < dimension; ++k)
  for(std::size_t j = 0; j < wires.size(); ++j)
   if(k & (std::size_t(1) << (wires.size()-1-j))) offsets[k] |= bits[j];
 try {
  for(std::size_t base = 0; base < amplitudes_.size(); ++base) {
   if((base & 4095) == 0) checkCancellation(cancelled);
   if(base & mask) continue;
   Complex input[8];
   for(std::size_t k = 0; k < dimension; ++k) input[k] = amplitudes_[base | offsets[k]];
   for(std::size_t row = 0; row < dimension; ++row) {
    Complex value = 0;
    for(std::size_t col = 0; col < dimension; ++col) value += unitary[row*dimension+col] * input[col];
    amplitudes_[base | offsets[row]] = value;
   }
  }
 } catch(...) { valid_ = false; throw; }
}
}
