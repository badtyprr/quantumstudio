// GPL-2.0-or-later; see COPYING.
using System;
using System.Text;
using System.Web.Script.Serialization;
static class RuntimeAngleImportTests {
 static int Main() {try {
  Console.InputEncoding=new UTF8Encoding(false,true);Console.OutputEncoding=new UTF8Encoding(false,true);
  var original=ClassicalCircuit.Load(Console.In.ReadToEnd());
  var saved=original.Serialize();var loaded=ClassicalCircuit.Load(saved);
  if(loaded.Serialize()!=saved)throw new Exception("Runtime angle save/load is not canonical.");
  var sampled=NumericalSampling.RequestClassical(loaded.Qubits,loaded.ClassicalBits,10000,731,loaded.OutputBits,loaded.SamplingGates(),loaded.VariableTypes,loaded.LoopConditionBudget,loaded.NumericTypes);
  var exact=NumericalSampling.RequestExact(loaded.Qubits,loaded.ClassicalBits,loaded.OutputBits,loaded.SamplingGates(),loaded.VariableTypes,loaded.LoopConditionBudget,loaded.NumericTypes);
  Console.Write(new JavaScriptSerializer().Serialize(new {sampled=Convert.ToBase64String(sampled),exact=Convert.ToBase64String(exact),source=ClassicalProgramQasm.Export(loaded)}));return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
