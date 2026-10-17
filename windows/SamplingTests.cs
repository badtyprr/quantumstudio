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
    new NumericalSampling.Gate {Kind=(NumericalSampling.Operation)5,Wires=new[]{0}},
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
   composer.Close();owner.Close();
   if(args.Length==1) {
    string worker=Path.GetFullPath(args[0]);gates=new List<NumericalSampling.Gate> {new NumericalSampling.Gate {Expression="H",Wires=new[]{0}},new NumericalSampling.Gate {Expression="CX",Wires=new[]{0,1}}};
    var result=NumericalSampling.Run(worker,2,10000,7,new[]{0,1},gates,CancellationToken.None).GetAwaiter().GetResult();
    Check(result.counts.Count==2 && result.counts.ContainsKey("00") && result.counts.ContainsKey("11"));
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
