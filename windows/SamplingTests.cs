using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Windows;

class SamplingTests {
 static int checks;
 static void Check(bool value) {checks++;if(!value)throw new Exception("Sampling check "+checks+" failed.");}
 static void Reject(Action action) {try {action();}catch(ArgumentException) {checks++;return;}catch(InvalidDataException) {checks++;return;}throw new Exception("Expected invalid sampling data.");}
 [STAThread] static int Main(string[] args) {
  try {
   var gates=new List<NumericalSampling.Gate> {new NumericalSampling.Gate {Expression="H⊗H",Wires=new[]{1,0}}};
   string request=Encoding.UTF8.GetString(NumericalSampling.Request(2,100,UInt64.MaxValue,new[]{1,0},gates));
   Check(request=="QSAMPLE1\n2\n100\n18446744073709551615\n2\n1\n0\n1\n2\n1\n0\n5\nH⊗H");
   var original=Thread.CurrentThread.CurrentCulture;Thread.CurrentThread.CurrentCulture=new CultureInfo("ar-SA");
   try {Check(Encoding.UTF8.GetString(NumericalSampling.Request(2,100,UInt64.MaxValue,new[]{1,0},gates))==request);}finally {Thread.CurrentThread.CurrentCulture=original;}
   foreach(int count in new[]{-1,26})Reject(()=>NumericalSampling.Request(count,100,0,new int[0],gates));
   foreach(int shots in new[]{0,-1,100001})Reject(()=>NumericalSampling.Request(2,shots,0,new[]{0},gates));
   foreach(int[] wires in new[]{new[]{0,0},new[]{2},new[]{-1},null})Reject(()=>NumericalSampling.Request(2,100,0,wires,gates));
   foreach(string expression in new[]{"",null,"X\0",new string('H',4097)})Reject(()=>NumericalSampling.Request(2,100,0,new[]{0},new[]{new NumericalSampling.Gate {Expression=expression,Wires=new[]{0}}}));
   string valid="{\"qubits\":2,\"shots\":100,\"seed\":\"7\",\"wires\":[1,0],\"counts\":{\"00\":40,\"11\":60}}";
   Check(NumericalSampling.ReadResult(valid,2,100,7,new[]{1,0}).counts["00"]==40);
   foreach(string bad in new[]{valid.Replace("60","59"),valid.Replace("60","-1"),valid.Replace("11\"","xx\""),valid.Replace("[1,0]","[0,1]"),valid.Replace("\"7\"","\"8\""),"null",valid.Replace("00\"","0\"")})Reject(()=>NumericalSampling.ReadResult(bad,2,100,7,new[]{1,0}));
   var owner=new Window {ShowInTaskbar=false,ShowActivated=false,Opacity=0};owner.Show();var composer=new CircuitComposer(owner,value=>{});composer.BellState(0);
   var captured=composer.SamplingGates();Check(captured.Count==2 && captured[0].Expression=="H" && captured[1].Expression=="CNOT");
   captured[0].Wires[0]=1;Check(composer.SamplingGates()[0].Wires[0]==0);
   composer.AddGate("Measure","0","");Check(composer.SamplingGates().Count==2);
   composer.AddGate("X","1","");Check(composer.SamplingGates().Count==4);
   Check(NumericalSampling.IsDynamic(composer.SamplingGates()));
   foreach(string name in new[]{"Reset","M1-X"}) {
    composer.BellState(0);composer.AddGate(name,name=="M1-X" ? "0,1" : "0","");
    var dynamic=composer.SamplingGates();Check(dynamic.Count==(name=="Reset" ? 3 : 4));
    Check(Encoding.UTF8.GetString(NumericalSampling.Request(2,100,7,new[]{0,1},dynamic)).StartsWith("QSAMPLE2\n"));
   }
   string[] noiseNames={"AD","GAD","PD","PAD","Depol","Thermal"};
   string[] noiseParameters={"1","1,0","1","1,0,0","1","1,1,0,0"};
   string[] noiseExpressions={"amplitude_damping(1)","amplitude_damping(1,0)","phase_damping(1)","phase_amplitude_damping(1,0,0)","depolarizing(1)","thermal_relaxation(1,1,0,0)"};
   var noisyCircuits=new List<List<NumericalSampling.Gate>>();
   for(int k=0;k<noiseNames.Length;k++) {
    composer.BellState(0);composer.AddGate(noiseNames[k],"0",noiseParameters[k]);
    var circuit=composer.SamplingGates();Check(circuit.Count==3 && circuit[2].Kind==NumericalSampling.Operation.Channel && circuit[2].Expression==noiseExpressions[k]);
    Check(composer.Expression().Contains(noiseExpressions[k]));
    composer.AddGate("Measure","0","");Check(composer.SamplingGates().Count==4);
    noisyCircuits.Add(circuit);
   }
   var reset=new[]{new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Reset,Wires=new[]{0}}};
   Check(Encoding.UTF8.GetString(NumericalSampling.Request(1,100,7,new[]{0},reset))=="QSAMPLE2\n1\n100\n7\n1\n1\n0\n2\n2\n0\n1\n0\n0\n");
   foreach(var invalid in new[]{
    new NumericalSampling.Gate {Kind=(NumericalSampling.Operation)7,Wires=new[]{0}},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{0,1}},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Reset,Wires=new[]{2}},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Conditional,Wires=new[]{0},Expression="X",Mask=4,Value=4},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Conditional,Wires=new[]{0},Expression="X",Mask=1,Value=2}})
    Reject(()=>NumericalSampling.Request(2,100,7,new[]{0},new[]{invalid}));
   var limit=new List<NumericalSampling.Gate>();for(int k=0;k<4096;k++)limit.Add(reset[0]);
   Reject(()=>NumericalSampling.Request(1,100,7,new[]{0},limit));
   limit.RemoveAt(0);Check(NumericalSampling.Request(1,100,7,new[]{0},limit).Length>0);
   string dynamicJson=valid.Replace("{\"qubits\"","{\"classical_bits\":2,\"qubits\"");
   Check(NumericalSampling.ReadResult(dynamicJson,2,100,7,new[]{1,0},true).classical_bits==2);
   Reject(()=>NumericalSampling.ReadResult(valid,2,100,7,new[]{1,0},true));
   Reject(()=>NumericalSampling.ReadResult(dynamicJson,2,100,7,new[]{1,0}));
   var flip=new NumericalSampling.Readout {Bits=new[]{0},Expression="[0,1;1,0]"};
   var empty=new NumericalSampling.Gate[0];
   Check(Encoding.UTF8.GetString(NumericalSampling.Request(1,100,7,new[]{0},empty,new[]{flip}))=="QSAMPLE2\n1\n100\n7\n1\n1\n0\n2\n1\n0\n0\n5\n1\n0\n9\n[0,1;1,0]");
   Check(Encoding.UTF8.GetString(NumericalSampling.Request(1,100,7,new[]{0},empty,new NumericalSampling.Readout[0])).StartsWith("QSAMPLE1\n"));
   foreach(var error in new[]{null,new NumericalSampling.Readout(),new NumericalSampling.Readout {Bits=new int[0],Expression="1"},new NumericalSampling.Readout {Bits=new[]{0,0},Expression=flip.Expression},new NumericalSampling.Readout {Bits=new[]{1},Expression=flip.Expression},new NumericalSampling.Readout {Bits=new[]{0},Expression=""}})
    Reject(()=>NumericalSampling.Request(2,100,7,new[]{0},empty,new[]{error}));
   var overLimit=new List<NumericalSampling.Readout>();for(int k=0;k<4096;k++)overLimit.Add(flip);
   Reject(()=>NumericalSampling.Request(1,100,7,new[]{0},empty,overLimit));
   overLimit.RemoveAt(0);Check(NumericalSampling.Request(1,100,7,new[]{0},empty,overLimit).Length>0);
   Reject(()=>NumericalSampling.Request(0,100,7,new int[0],empty,new[]{flip}));
   var readoutEditor=new SamplingReadout();Check(readoutEditor.Capture(2).Length==0);
   readoutEditor.SetAssignment("1,0"," [0,1,0,0;0,1,0,0;0,0,1,0;0,0,0,1] ");
   var capturedReadout=readoutEditor.Capture(2);
   Check(capturedReadout.Length==1 && capturedReadout[0].Bits[0]==1 && capturedReadout[0].Bits[1]==0 && !capturedReadout[0].Expression.StartsWith(" "));
   readoutEditor.SetAssignment("0","[0,1;1,0]");Check(capturedReadout[0].Bits.Length==2);
   foreach(string invalidBits in new[]{"","0,0","-1","2","0,","0,1,2,3,4,5,6,7,8"}) {readoutEditor.SetAssignment(invalidBits,"I");Reject(()=>readoutEditor.Capture(2));}
   readoutEditor.SetAssignment("0",new string('H',4097));Reject(()=>readoutEditor.Capture(2));
   readoutEditor.SetAssignment("0","");Reject(()=>readoutEditor.Capture(2));
   var exportResult=NumericalSampling.ReadResult(valid,2,100,7,new[]{1,0});
   string exported=SamplingExport.Json(exportResult,capturedReadout);
   var exportFields=new System.Web.Script.Serialization.JavaScriptSerializer().Deserialize<Dictionary<string,object>>(exported);
   Check((string)exportFields["schema"]=="QuantumStudio.sampling.v1" && exportFields.ContainsKey("final_readout") && exportFields.ContainsKey("assignment_orientation"));
   Check(SamplingExport.Csv(exportResult,capturedReadout).StartsWith("bits,count,frequency,shots,seed,run_final_readout\r\n00,40,0.4,100,7,"));
   Check(SamplingExport.Csv(exportResult,capturedReadout).EndsWith("11,60,0.6,100,7,\r\n"));
   composer.Close();owner.Close();
   // Saved classical records have their own size, destinations and output order.
   var saved=new List<NumericalSampling.Gate> {
    new NumericalSampling.Gate {Expression="X",Wires=new[]{0}},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{0},ClassicalBit=63},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Reset,Wires=new[]{0}},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Conditional,Expression="X",Wires=new[]{1},Mask=1UL<<63,Value=1UL<<63},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{1},ClassicalBit=3}};
   var measureOnly=new[]{new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{0},ClassicalBit=3}};
   Check(Encoding.UTF8.GetString(NumericalSampling.RequestClassical(1,4,10,7,new[]{3},measureOnly))=="QSAMPLE2\n1\n10\n7\n4\n1\n3\n1\n1\n0\n3\n");
   foreach(int bits in new[]{-1,65})Reject(()=>NumericalSampling.RequestClassical(1,bits,10,7,new int[0],measureOnly));
   foreach(int[] bits in new[]{new[]{4},new[]{-1},new[]{3,3},null})Reject(()=>NumericalSampling.RequestClassical(1,4,10,7,bits,measureOnly));
   foreach(int? bit in new int?[]{null,-1,4})Reject(()=>NumericalSampling.RequestClassical(1,4,10,7,new[]{3},new[]{new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{0},ClassicalBit=bit}}));
   Reject(()=>NumericalSampling.Request(1,10,7,new[]{0},measureOnly));
   Reject(()=>NumericalSampling.RequestClassical(1,4,10,7,new[]{3},new[]{new NumericalSampling.Gate {Expression="X",Wires=new[]{0},ClassicalBit=0}}));
   Reject(()=>NumericalSampling.RequestClassical(2,63,10,7,new[]{3},saved));
   Check(NumericalSampling.RequestClassical(2,64,10,7,new[]{63,3},saved).Length>0);
   var noOperations=new NumericalSampling.Gate[0];
   Check(Encoding.UTF8.GetString(NumericalSampling.RequestClassical(0,0,10,7,new int[0],noOperations))=="QSAMPLE2\n0\n10\n7\n0\n0\n0\n");
   string savedJson="{\"qubits\":1,\"classical_bits\":4,\"shots\":10,\"seed\":\"7\",\"wires\":[3],\"counts\":{\"1\":10}}";
   Check(NumericalSampling.ReadClassicalResult(savedJson,1,4,10,7,new[]{3}).counts["1"]==10);
   Reject(()=>NumericalSampling.ReadClassicalResult(savedJson,1,3,10,7,new[]{3}));
   Reject(()=>NumericalSampling.ReadResult(savedJson,1,10,7,new[]{3},true));
   var emptyBody=new NumericalSampling.Gate[0];
   var branch=new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,Mask=1,Value=1,WhenTrue=new[]{
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Reset,Wires=new[]{0}},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{0},ClassicalBit=0},
    new NumericalSampling.Gate {Expression="X",Wires=new[]{1}},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{1},ClassicalBit=1}},WhenFalse=emptyBody};
   var branchProgram=new[]{new NumericalSampling.Gate {Expression="X",Wires=new[]{0}},new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{0},ClassicalBit=0},branch};
   Check(NumericalSampling.RequestClassical(2,2,100,7,new[]{0,1},branchProgram).Length>0);
   Reject(()=>NumericalSampling.Request(2,100,7,new[]{0,1},branchProgram));
   foreach(var invalid in new[]{
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,WhenTrue=emptyBody},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,WhenTrue=emptyBody,WhenFalse=emptyBody,Mask=4},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,WhenTrue=emptyBody,WhenFalse=emptyBody,Value=1},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,WhenTrue=emptyBody,WhenFalse=emptyBody,Expression="X"},
    new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,WhenTrue=emptyBody,WhenFalse=new NumericalSampling.Gate[]{null}},
    new NumericalSampling.Gate {Expression="X",Wires=new[]{0},WhenTrue=emptyBody}})
    Reject(()=>NumericalSampling.RequestClassical(2,2,100,7,new[]{0},new[]{invalid}));
   NumericalSampling.Gate[] nested=emptyBody;
   for(int k=0;k<32;k++)nested=new[]{new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,WhenTrue=nested,WhenFalse=emptyBody}};
   Check(NumericalSampling.RequestClassical(0,0,1,7,new int[0],nested).Length>0);
   Reject(()=>NumericalSampling.RequestClassical(0,0,1,7,new int[0],new[]{new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,WhenTrue=nested,WhenFalse=emptyBody}}));
   var cycle=new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,WhenFalse=emptyBody};cycle.WhenTrue=new[]{cycle};
   Reject(()=>NumericalSampling.RequestClassical(0,0,1,7,new int[0],new[]{cycle}));
   var wideBody=new List<NumericalSampling.Gate>();for(int k=0;k<4095;k++)wideBody.Add(new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Reset,Wires=new[]{0}});
   var wideBranch=new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Branch,WhenTrue=wideBody,WhenFalse=emptyBody};
   Check(NumericalSampling.RequestClassical(1,1,1,7,new[]{0},new[]{wideBranch}).Length>0);
   wideBody.Add(wideBody[0]);Reject(()=>NumericalSampling.RequestClassical(1,1,1,7,new[]{0},new[]{wideBranch}));
   if(args.Length==1) {
    string worker=Path.GetFullPath(args[0]);gates=new List<NumericalSampling.Gate> {new NumericalSampling.Gate {Expression="H",Wires=new[]{0}},new NumericalSampling.Gate {Expression="CX",Wires=new[]{0,1}}};
    var branchResult=NumericalSampling.RunClassical(worker,2,2,100,7,new[]{0,1},branchProgram,CancellationToken.None).GetAwaiter().GetResult();
    Check(branchResult.counts.Count==1 && branchResult.counts["01"]==100);
    var branchPending=NumericalSampling.RunClassical(worker,2,2,100,7,new[]{0,1},branchProgram,CancellationToken.None);
    branch.WhenTrue=emptyBody;
    Check(branchPending.GetAwaiter().GetResult().counts["01"]==100);
    var savedResult=NumericalSampling.RunClassical(worker,2,64,100,7,new[]{63,3,0},saved,CancellationToken.None).GetAwaiter().GetResult();
    Check(savedResult.counts.Count==1 && savedResult.counts["110"]==100);
    savedResult=NumericalSampling.RunClassical(worker,1,1,100,7,new[]{0},new[]{new NumericalSampling.Gate {Expression="X",Wires=new[]{0}}},CancellationToken.None).GetAwaiter().GetResult();
    Check(savedResult.counts.Count==1 && savedResult.counts["0"]==100);
    savedResult=NumericalSampling.RunClassical(worker,0,64,100,7,new[]{63,0},new[]{new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Readout,Expression="[0,1;1,0]",Wires=new[]{63}}},CancellationToken.None).GetAwaiter().GetResult();
    Check(savedResult.counts.Count==1 && savedResult.counts["10"]==100);
    savedResult=NumericalSampling.RunClassical(worker,0,0,100,7,new int[0],noOperations,CancellationToken.None).GetAwaiter().GetResult();
    Check(savedResult.counts.Count==1 && savedResult.counts[""]==100);
    var result=NumericalSampling.Run(worker,2,10000,7,new[]{0,1},gates,CancellationToken.None).GetAwaiter().GetResult();
    Check(result.counts.Count==2 && result.counts.ContainsKey("00") && result.counts.ContainsKey("11"));
    var readoutResult=NumericalSampling.Run(worker,2,1000,7,new[]{0,1},gates,CancellationToken.None,new[]{flip}).GetAwaiter().GetResult();
    Check(readoutResult.classical_bits==2 && readoutResult.counts.Count==2 && readoutResult.counts.ContainsKey("01") && readoutResult.counts.ContainsKey("10"));
    var correlated=new NumericalSampling.Readout {Bits=new[]{1,0},Expression="[0,1,0,0;0,1,0,0;0,0,1,0;0,0,0,1]"};
    readoutResult=NumericalSampling.Run(worker,2,100,7,new[]{0,1},empty,CancellationToken.None,new[]{correlated}).GetAwaiter().GetResult();
    Check(readoutResult.counts.Count==1 && readoutResult.counts["10"]==100);
    readoutResult=NumericalSampling.Run(worker,1,100,7,new[]{0},empty,CancellationToken.None,new[]{flip,flip}).GetAwaiter().GetResult();
    Check(readoutResult.counts.Count==1 && readoutResult.counts["0"]==100);
    var snapshot=NumericalSampling.Run(worker,1,100,7,new[]{0},empty,CancellationToken.None,new[]{flip});
    flip.Expression="[1,0;0,1]";readoutResult=snapshot.GetAwaiter().GetResult();
    Check(readoutResult.counts.Count==1 && readoutResult.counts["1"]==100);
    var dynamicCircuit=new List<NumericalSampling.Gate> {
     new NumericalSampling.Gate {Expression="H",Wires=new[]{0}},
     new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Measure,Wires=new[]{0}},
     new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Reset,Wires=new[]{0}},
     new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Conditional,Mask=1,Value=1,Expression="X",Wires=new[]{1}}};
    var dynamicResult=NumericalSampling.Run(worker,2,10000,7,new[]{0,1},dynamicCircuit,CancellationToken.None).GetAwaiter().GetResult();
    Check(dynamicResult.classical_bits==2 && dynamicResult.counts.Count==2 && dynamicResult.counts.ContainsKey("00") && dynamicResult.counts.ContainsKey("01"));
    Check(Math.Abs(dynamicResult.counts["01"]-5000)<250);
    for(int k=0;k<noiseExpressions.Length;k++) {
     var operations=new List<NumericalSampling.Gate> {new NumericalSampling.Gate {Expression="X",Wires=new[]{0}},new NumericalSampling.Gate {Kind=NumericalSampling.Operation.Channel,Expression=noiseExpressions[k],Wires=new[]{0}}};
     var noisy=NumericalSampling.Run(worker,1,10000,7,new[]{0},operations,CancellationToken.None).GetAwaiter().GetResult();
     if(k==4)Check(noisy.counts.Count==2 && Math.Abs(noisy.counts["0"]-5000)<300);
     else Check(noisy.counts.Count==1 && noisy.counts.ContainsKey(k==2 || k==5 ? "1" : "0"));
    }
    using(var cancellation=new CancellationTokenSource()) {
     var many=new List<NumericalSampling.Gate>();for(int k=0;k<100;k++)many.Add(new NumericalSampling.Gate {Expression="H",Wires=new[]{k%25}});
     var pending=NumericalSampling.Run(worker,25,10000,7,new[]{0},many,cancellation.Token);cancellation.CancelAfter(300);
     bool cancelled=false;try {pending.GetAwaiter().GetResult();}catch(OperationCanceledException) {cancelled=true;}Check(cancelled);
    }
    Check(NumericalSampling.Run(worker,2,100,7,new[]{0,1},gates,CancellationToken.None).GetAwaiter().GetResult().shots==100);
   }
   Console.WriteLine("PASS: "+checks+" sampling request, result and circuit checks.");return 0;
  }catch(Exception error) {Console.Error.WriteLine(error);return 1;}
 }
}
