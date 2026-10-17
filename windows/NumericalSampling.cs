// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using System.Web.Script.Serialization;

static class NumericalSampling {
 public enum Operation { Gate, Measure, Reset, Conditional, Channel, Readout }
 public sealed class Gate {public string Expression;public int[] Wires;public Operation Kind;public ulong Mask,Value;public int? ClassicalBit {get;set;}}
 public sealed class Readout {public string Expression;public int[] Bits;}
 public static bool IsDynamic(IList<Gate> gates) {foreach(var gate in gates)if(gate!=null && gate.Kind!=Operation.Gate)return true;return false;}
 public sealed class Result {
  public int? classical_bits {get;set;} public int qubits {get;set;} public int shots {get;set;} public string seed {get;set;} public int[] wires {get;set;} public Dictionary<string,int> counts {get;set;}
 }
 public static byte[] Request(int qubits,int shots,ulong seed,int[] measured,IList<Gate> gates,IList<Readout> readout=null) {
  return Serialize(qubits,shots,seed,measured,gates,readout,null);
 }
 // Explicit classical outputs preserve saved records: no final measurements are added.
 public static byte[] RequestClassical(int qubits,int classicalBits,int shots,ulong seed,int[] outputBits,IList<Gate> gates) {
  return Serialize(qubits,shots,seed,outputBits,gates,null,classicalBits);
 }
 static byte[] Serialize(int qubits,int shots,ulong seed,int[] measured,IList<Gate> gates,IList<Readout> readout,int? classicalBits) {
  if(classicalBits.HasValue && (classicalBits.Value<0 || classicalBits.Value>64))throw new ArgumentException("Use 0–64 classical bits.");
  int bits=classicalBits ?? qubits;
  if(qubits<0 || qubits>25 || shots<1 || shots>100000 || gates==null || gates.Count>4096 || measured==null || (readout!=null && readout.Count>4096))
   throw new ArgumentException("Use 0–25 qubits, 1–100,000 shots and at most 4096 gates.");
  bool dynamic=classicalBits.HasValue || IsDynamic(gates) || (readout!=null && readout.Count>0);
  var text=new StringBuilder(dynamic ? "QSAMPLE2\n" : "QSAMPLE1\n");
  Action<ulong> number=value=>text.Append(value.ToString(CultureInfo.InvariantCulture)).Append('\n');
  number((ulong)qubits);number((ulong)shots);number(seed);if(dynamic)number((ulong)bits);
  Action<int[],int,int> wires=delegate(int[] values,int maximum,int registerSize) {
   if(values==null || values.Length>maximum)throw new ArgumentException("Invalid sampling wire list.");
   var seen=new HashSet<int>();number((ulong)values.Length);
   foreach(int wire in values) {
    if(wire<0 || wire>=registerSize || !seen.Add(wire))throw new ArgumentException("Sampling wires must be distinct and inside the register.");
    number((ulong)wire);
   }
  };
  wires(measured,bits,bits);
  int stepCount=gates.Count+(dynamic && !classicalBits.HasValue ? measured.Length : 0)+(readout==null ? 0 : readout.Count);
  if(stepCount>4096)throw new ArgumentException("Sampling needs at most 4096 operations including final measurements.");
  number((ulong)stepCount);
  // Final assignment errors must follow final measurements, or those
  // measurements would overwrite the noisy records before returning counts.
  var operations=new List<Gate>(gates);
  if(dynamic && !classicalBits.HasValue)foreach(int wire in measured)operations.Add(new Gate {Kind=Operation.Measure,Wires=new[]{wire}});
  if(readout!=null)foreach(var error in readout) {
   if(error==null || error.Bits==null)throw new ArgumentException("Invalid readout assignment.");
   foreach(int bit in error.Bits)if(Array.IndexOf(measured,bit)<0)throw new ArgumentException("Final readout targets must be measured bits.");
   operations.Add(new Gate {Kind=Operation.Readout,Wires=error.Bits,Expression=error.Expression});
  }
  foreach(var gate in operations) {
   if(gate==null || !Enum.IsDefined(typeof(Operation),gate.Kind))throw new ArgumentException("Invalid sampling operation.");
   if(gate.ClassicalBit.HasValue && (!classicalBits.HasValue || gate.Kind!=Operation.Measure))throw new ArgumentException("A classical destination requires an explicit classical-output measurement.");
   if(dynamic)number((ulong)gate.Kind);
   if(gate.Kind==Operation.Measure || gate.Kind==Operation.Reset) {
    if(gate.Wires==null || gate.Wires.Length!=1 || gate.Wires[0]<0 || gate.Wires[0]>=qubits)
     throw new ArgumentException("Measurement and reset need one wire inside the register.");
    number((ulong)gate.Wires[0]);
    if(gate.Kind==Operation.Measure) {
     int destination=classicalBits.HasValue ? (gate.ClassicalBit ?? -1) : gate.Wires[0];
     if(destination<0 || destination>=bits)throw new ArgumentException("Measurement needs a destination inside the classical register.");
     number((ulong)destination);
    }
    continue;
   }
   if(gate.Kind==Operation.Conditional) {
    ulong allowed=bits==64 ? UInt64.MaxValue : (1UL<<bits)-1;
    if((gate.Mask & ~allowed)!=0 || (gate.Value & ~gate.Mask)!=0)throw new ArgumentException("Invalid classical condition.");
    number(gate.Mask);number(gate.Value);
   }
   if(gate.Wires==null || gate.Wires.Length==0 || String.IsNullOrWhiteSpace(gate.Expression) || gate.Expression.IndexOf('\0')>=0)
    throw new ArgumentException("Each sampling gate needs a matrix expression and target wires.");
   wires(gate.Wires,gate.Kind==Operation.Readout ? 8 : 3,gate.Kind==Operation.Readout ? bits : qubits);
   int length=Encoding.UTF8.GetByteCount(gate.Expression);
   if(length>4096)throw new ArgumentException("A sampling gate expression exceeds 4096 UTF-8 bytes.");
   number((ulong)length);text.Append(gate.Expression);
   if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");
  }
  byte[] bytes=new UTF8Encoding(false,true).GetBytes(text.ToString());
  if(bytes.Length>1100000)throw new ArgumentException("Sampling request is too large.");
  return bytes;
 }
 public static Result ReadResult(string json,int qubits,int shots,ulong seed,int[] measured,bool dynamic=false) {
  return ValidateResult(json,qubits,shots,seed,measured,dynamic ? (int?)qubits : null);
 }
 public static Result ReadClassicalResult(string json,int qubits,int classicalBits,int shots,ulong seed,int[] outputBits) {
  if(classicalBits<0 || classicalBits>64)throw new ArgumentException("Use 0–64 classical bits.");
  return ValidateResult(json,qubits,shots,seed,outputBits,classicalBits);
 }
 static Result ValidateResult(string json,int qubits,int shots,ulong seed,int[] measured,int? classicalBits) {
  var result=new JavaScriptSerializer {MaxJsonLength=8000000,RecursionLimit=12}.Deserialize<Result>(json);
  if(result==null || result.qubits!=qubits || result.shots!=shots || result.seed!=seed.ToString(CultureInfo.InvariantCulture) ||
     result.wires==null || result.wires.Length!=measured.Length || result.counts==null || result.counts.Count>shots)
   throw new InvalidDataException("The sampler returned an inconsistent response.");
  if(result.classical_bits!=classicalBits)
   throw new InvalidDataException("The sampler returned the wrong classical register.");
  for(int k=0;k<measured.Length;k++)if(result.wires[k]!=measured[k])throw new InvalidDataException("The sampler changed the measurement order.");
  long total=0;
  foreach(var item in result.counts) {
   if(item.Key.Length!=measured.Length || item.Value<=0 || item.Value>shots)throw new InvalidDataException("Invalid sample count.");
   foreach(char bit in item.Key)if(bit!='0' && bit!='1')throw new InvalidDataException("Invalid sampled bit string.");
   total+=item.Value;
  }
  if(total!=shots)throw new InvalidDataException("Sample counts do not sum to the requested shots.");
  return result;
 }
 public static Task<Result> Run(string worker,int qubits,int shots,ulong seed,int[] measured,IList<Gate> gates,CancellationToken cancellation,IList<Readout> readout=null) {
  // Serialize before handing work to another thread, so editor changes cannot alter a run.
  byte[] request=Request(qubits,shots,seed,measured,gates,readout);
  bool dynamic=IsDynamic(gates) || (readout!=null && readout.Count>0);
  int[] order=(int[])measured.Clone();
  return RunSerialized(worker,qubits,shots,seed,order,request,cancellation,dynamic ? (int?)qubits : null);
 }
 public static Task<Result> RunClassical(string worker,int qubits,int classicalBits,int shots,ulong seed,int[] outputBits,IList<Gate> gates,CancellationToken cancellation) {
  byte[] request=RequestClassical(qubits,classicalBits,shots,seed,outputBits,gates);
  return RunSerialized(worker,qubits,shots,seed,(int[])outputBits.Clone(),request,cancellation,classicalBits);
 }
 static Task<Result> RunSerialized(string worker,int qubits,int shots,ulong seed,int[] order,byte[] request,CancellationToken cancellation,int? classicalBits) {
  return Task.Run(async delegate {
   cancellation.ThrowIfCancellationRequested();
   using(var process=new Process()) {
    process.StartInfo=new ProcessStartInfo(worker,"--sample") {UseShellExecute=false,CreateNoWindow=true,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8,WorkingDirectory=Path.GetDirectoryName(worker)};
    process.StartInfo.EnvironmentVariables["QALCULATE_DEFINITIONS_DIR"]=Path.Combine(Path.GetDirectoryName(worker),"data");
    // Closing the last WPF window can end the process before a thread-pool
    // continuation runs. Stop the child synchronously when cancellation fires.
    // Serialize startup with cancellation so closing during Start cannot orphan it.
    var lifetime=new object();bool started=false;
    using(cancellation.Register(delegate {
     lock(lifetime) {
      if(!started)return;
      try {if(!process.HasExited)process.Kill();}
      catch(InvalidOperationException) {} // The child may have exited concurrently.
      catch(System.ComponentModel.Win32Exception) {} // Cleanup below repeats the check.
     }
    })) {
    lock(lifetime) {cancellation.ThrowIfCancellationRequested();process.Start();started=true;}
    var clock=Stopwatch.StartNew();
    try {
     var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();
     await process.StandardInput.BaseStream.WriteAsync(request,0,request.Length,cancellation);process.StandardInput.Close();
     while(!process.WaitForExit(50)) {
      cancellation.ThrowIfCancellationRequested();
      if(clock.Elapsed.TotalMinutes>=5)throw new TimeoutException("Sampling exceeded five minutes. Reduce the circuit or shot count.");
     }
     cancellation.ThrowIfCancellationRequested();
     string stdout=await output,stderr=await error;
     if(process.ExitCode!=0)throw new InvalidOperationException(String.IsNullOrWhiteSpace(stderr) ? "Sampling failed." : stderr.Trim());
     return ValidateResult(stdout,qubits,shots,seed,order,classicalBits);
    } catch {cancellation.ThrowIfCancellationRequested();throw;}
    finally {lock(lifetime) {if(!process.HasExited)process.Kill();}process.WaitForExit();}
    }
   }
  });
 }
}
