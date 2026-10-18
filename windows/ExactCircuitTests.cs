using System;
using System.IO;
using System.Text;
using System.Threading;

static class ExactCircuitTests {
 static int checks;
 static void Check(bool value) {++checks;if(!value)throw new Exception("Exact adapter check failed: "+checks);}
 static void Reject(Action action) {bool caught=false;try {action();}catch(ArgumentException){caught=true;}catch(InvalidDataException){caught=true;}Check(caught);}
 static ClassicalCircuit Circuit(string expression="H") {
  return ClassicalCircuit.From(new ClassicalCircuit.Document {Version=2,Qubits=1,Registers=new[]{new ClassicalCircuit.Register {Name="c",Size=1}},OutputBits=new[]{0},Steps=new[]{
   new ClassicalCircuit.Step {Kind="Gate",Expression=expression,Wires=new[]{0}},
   new ClassicalCircuit.Step {Kind="Measure",Wires=new[]{0},ClassicalBit=0}}});
 }
 static int Main(string[] args) {try {
  var loop=ClassicalCircuit.From(new ClassicalCircuit.Document{Version=7,LoopConditionBudget=0,Qubits=0,Registers=new ClassicalCircuit.Register[0],Variables=new ClassicalCircuit.Variable[0],OutputBits=new int[0],Steps=new[]{new ClassicalCircuit.Step{Kind="While",ClassicalValue=new ClassicalCircuit.ExpressionNode{Kind="Constant",Width=1,Value="0"},WhenTrue=new ClassicalCircuit.Step[0]}}});
  Check(Encoding.UTF8.GetString(ExactCircuit.Request(loop)).StartsWith("QEXACT6\n0\n0\n0\n0\n"));
  if(args.Length>0) {
   bool exhausted=false;try{ExactCircuit.Run(args[0],loop,CancellationToken.None).GetAwaiter().GetResult();}catch(InvalidOperationException e){exhausted=e.Message.Contains("loop condition budget");}Check(exhausted);
   var allowed=loop.Snapshot();allowed.LoopConditionBudget=1;
   Check(ExactCircuit.Run(args[0],ClassicalCircuit.From(allowed),CancellationToken.None).GetAwaiter().GetResult().probabilities[""]=="1");
  }
  var circuit=Circuit();
  Check(Encoding.UTF8.GetString(ExactCircuit.Request(circuit))=="QEXACT1\n1\n1\n1\n0\n2\n0\n1\n0\n1\nH1\n0\n0\n");
  string valid="{\"qubits\":1,\"classical_bits\":1,\"bits\":[0],\"probabilities\":{\"0\":\"1/3\",\"1\":\"2/3\"}}";
  Check(ExactCircuit.ReadResult(valid,circuit).probabilities["0"]=="1/3");
  Check(ExactCircuit.ReadResult(valid.Replace("1/3","cos(x/2)^2"),circuit).probabilities["0"]=="cos(x/2)^2");
  foreach(string bad in new[]{valid.Replace("\"qubits\":1","\"qubits\":2"),valid.Replace("\"classical_bits\":1","\"classical_bits\":2"),valid.Replace("[0]","[1]"),
   valid.Replace("[0]","[\"0\"]"),valid.Replace("\"1/3\"","0.3"),valid.Replace("\"1/3\"","null"),valid.Replace("\"1/3\"","\"\""),valid.Replace("\"1/3\"","\"x\\n\""),
   valid.Replace("\"0\":","\"2\":"),valid.Replace("\"0\":","\"00\":"),valid.Replace("\"qubits\":1,",""),valid.Replace("\"qubits\":1,","\"extra\":1,\"qubits\":1,")})Reject(()=>ExactCircuit.ReadResult(bad,circuit));
  var large=circuit.Snapshot();large.Qubits=11;Reject(()=>ExactCircuit.Request(ClassicalCircuit.From(large)));
  var conditional=circuit.Snapshot();conditional.Steps=new ClassicalCircuit.Step[257];
  for(int k=0;k<conditional.Steps.Length;k++)conditional.Steps[k]=new ClassicalCircuit.Step {Kind="Conditional",Expression="X",Wires=new[]{0},Mask="0",Value="0"};
  Reject(()=>ExactCircuit.Request(ClassicalCircuit.From(conditional)));
  if(args.Length>0) {
   var result=ExactCircuit.Run(args[0],circuit,CancellationToken.None).GetAwaiter().GetResult();Check(result.probabilities["0"]=="0.5" && result.probabilities["1"]=="0.5");
   result=ExactCircuit.Run(args[0],Circuit("Ry(x)"),CancellationToken.None).GetAwaiter().GetResult();Check(result.probabilities["0"].Contains("cos") && result.probabilities["1"].Contains("sin"));
   bool cancelled=false;using(var token=new CancellationTokenSource()){token.Cancel();try{ExactCircuit.Run(args[0],circuit,token.Token).GetAwaiter().GetResult();}catch(OperationCanceledException){cancelled=true;}}Check(cancelled);
   bool failed=false;try{ExactCircuit.Run(args[0],Circuit("2*I"),CancellationToken.None).GetAwaiter().GetResult();}catch(InvalidOperationException){failed=true;}Check(failed);
  }
  Console.WriteLine("PASS: "+checks+" exact circuit adapter checks.");return 0;
 }catch(Exception e){Console.Error.WriteLine(e);return 1;}}
}
