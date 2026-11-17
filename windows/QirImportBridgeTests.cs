// GPL-2.0-or-later; see COPYING.
using System;
using System.Text;
using System.Web.Script.Serialization;
static class QirImportBridgeTests {
 static int Main() { try {
  Console.InputEncoding=new UTF8Encoding(false,true); Console.OutputEncoding=new UTF8Encoding(false,true);
  var original=ClassicalCircuit.Load(Console.In.ReadToEnd());
  var saved=original.Serialize(); var circuit=ClassicalCircuit.Load(saved);
  if(circuit.Serialize()!=saved)throw new Exception("QIR import save/load is not canonical.");
  var sampled=NumericalSampling.RequestClassical(circuit.Qubits,circuit.ClassicalBits,10000,731,circuit.OutputBits,circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget,circuit.NumericTypes,circuit.ArrayAllocations);
  var exact=NumericalSampling.RequestExact(circuit.Qubits,circuit.ClassicalBits,circuit.OutputBits,circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget,circuit.NumericTypes,circuit.ArrayAllocations);
  Console.Write(new JavaScriptSerializer().Serialize(new {sampled=Convert.ToBase64String(sampled),exact=Convert.ToBase64String(exact)})); return 0;
 } catch(Exception error) { Console.Error.WriteLine(error); return 1; } }
}
