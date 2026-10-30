// GPL-2.0-or-later; see COPYING.
#include "QuantumWireSelection.h"
#include <stdexcept>

namespace QuantumClassical {
WireSelection::WireSelection(const std::vector<Target> &targets,const std::string &source):WireSelection(targets,source,3) {}
WireSelection WireSelection::references(const std::vector<Target> &targets,const std::string &source) {return WireSelection(targets,source,25);}
WireSelection::WireSelection(const std::vector<Target> &targets,const std::string &source,unsigned limit):targets_(targets),source_(source) {
 if(targets_.empty() || targets_.size()>limit)throw std::invalid_argument(limit==3 ? "Dynamic operations need one to three wire selectors" : "Quantum reference checks need one to 25 wire selectors");
 unsigned nodes=0;for(const auto &target:targets_) {nodes+=target.index.count();if(limit==25 && nodes>512)throw std::length_error("Wire selections exceed 512 expression nodes");}
 if(source_.size()>512 || source_.find('\0')!=std::string::npos)throw std::invalid_argument("Wire source context exceeds its bounds");
 for(const auto &target:targets_)if(target.wires.empty() || target.wires.size()>25)
  throw std::invalid_argument("Wire selector needs a register of one to 25 wires");
}
std::string WireSelection::diagnostic(const std::string &message) const {return source_.empty() ? message : source_+": "+message;}
void WireSelection::validate(unsigned qubits,unsigned bits,const IntegerStorage &storage) const {
 for(const auto &target:targets_) {
  for(unsigned wire:target.wires)if(wire>=qubits)throw std::out_of_range(diagnostic("Wire alias is outside the quantum register"));
  target.index.validate(bits,storage);
 }
}
std::vector<unsigned> WireSelection::evaluate(std::uint64_t record,unsigned bits,const IntegerStorage &storage) const {
 std::vector<unsigned> result;
 for(const auto &target:targets_) {
  const auto index=[&] {
   try {return target.index.evaluate(record,bits,storage).value();}
   catch(const std::exception &error){throw std::domain_error(diagnostic(std::string("Wire index: ")+error.what()));}
  }();
  if(index.negative() || index.bits()>=target.wires.size())throw std::out_of_range(diagnostic("Wire index is outside its register (negative indices are unsupported)"));
  const unsigned wire=target.wires[static_cast<std::size_t>(index.bits())];
  for(unsigned previous:result)if(previous==wire)throw std::invalid_argument(diagnostic("Runtime quantum wires must be distinct"));
  result.push_back(wire);
 }
 return result;
}
}
