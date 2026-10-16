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
   composer.AddGate("X","1","");
   bool rejected=false;try {composer.SamplingGates();}catch(InvalidOperationException) {rejected=true;}Check(rejected);
   foreach(string name in new[]{"Reset","AD","M1-X"}) {
    composer.BellState(0);composer.AddGate(name,name=="M1-X" ? "0,1" : "0",name=="AD" ? "1/4" : "");
    rejected=false;try {composer.SamplingGates();}catch(InvalidOperationException) {rejected=true;}Check(rejected);
   }
   composer.Close();owner.Close();
   if(args.Length==1) {
    string worker=Path.GetFullPath(args[0]);gates=new List<NumericalSampling.Gate> {new NumericalSampling.Gate {Expression="H",Wires=new[]{0}},new NumericalSampling.Gate {Expression="CX",Wires=new[]{0,1}}};
    var result=NumericalSampling.Run(worker,2,10000,7,new[]{0,1},gates,CancellationToken.None).GetAwaiter().GetResult();
    Check(result.counts.Count==2 && result.counts.ContainsKey("00") && result.counts.ContainsKey("11"));
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
