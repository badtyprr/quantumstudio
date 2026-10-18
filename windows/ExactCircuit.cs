// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

static class ExactCircuit {
 public sealed class Result {
  public int qubits {get;set;}
  public int classical_bits {get;set;}
  public int[] bits {get;set;}
  public Dictionary<string,string> probabilities {get;set;}
 }
 public static byte[] Request(ClassicalCircuit circuit) {
  if(circuit==null)throw new ArgumentNullException("circuit");
  return NumericalSampling.RequestExact(circuit.Qubits,circuit.ClassicalBits,circuit.OutputBits,circuit.SamplingGates(),circuit.VariableTypes,circuit.LoopConditionBudget);
 }
 public static Result ReadResult(string json,ClassicalCircuit circuit) {
  var serializer=new JavaScriptSerializer {MaxJsonLength=8000000,RecursionLimit=12};
  var root=serializer.DeserializeObject(json) as Dictionary<string,object>;
  if(root==null || root.Count!=4 || !root.ContainsKey("qubits") || !root.ContainsKey("classical_bits") || !root.ContainsKey("bits") || !root.ContainsKey("probabilities") ||
     !(root["qubits"] is int) || !(root["classical_bits"] is int))throw new InvalidDataException("Invalid exact circuit response fields.");
  var bits=root["bits"] as object[];var probabilities=root["probabilities"] as Dictionary<string,object>;
  if(bits==null || probabilities==null)throw new InvalidDataException("Invalid exact circuit response types.");
  foreach(object bit in bits)if(!(bit is int))throw new InvalidDataException("Invalid exact output bit.");
  foreach(var entry in probabilities)if(!(entry.Value is string))throw new InvalidDataException("Exact probabilities must be text.");
  var result=serializer.ConvertToType<Result>(root);var expected=circuit.OutputBits;
  if(result.qubits!=circuit.Qubits || result.classical_bits!=circuit.ClassicalBits || result.bits.Length!=expected.Length || result.probabilities.Count==0 || result.probabilities.Count>1048576)
   throw new InvalidDataException("The exact evaluator returned an inconsistent response.");
  for(int k=0;k<expected.Length;++k)if(result.bits[k]!=expected[k])throw new InvalidDataException("The exact evaluator changed the output order.");
  foreach(var item in result.probabilities) {
   if(item.Key.Length!=expected.Length || String.IsNullOrWhiteSpace(item.Value) || item.Value.Length>1000000)throw new InvalidDataException("Invalid exact probability entry.");
   foreach(char bit in item.Key)if(bit!='0' && bit!='1')throw new InvalidDataException("Invalid exact output label.");
   foreach(char c in item.Value)if(Char.IsControl(c))throw new InvalidDataException("Invalid exact probability text.");
  }
  return result;
 }
 public static Task<Result> Run(string worker,ClassicalCircuit circuit,CancellationToken cancellation) {
  // ClassicalCircuit is immutable; serialize synchronously before the process starts.
  var request=Request(circuit);
  return NumericalSampling.RunRequest(worker,"--exact-circuit",request,cancellation,json=>ReadResult(json,circuit));
 }
}
