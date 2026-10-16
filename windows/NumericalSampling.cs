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
 public sealed class Gate {public string Expression;public int[] Wires;}
 public sealed class Result {
  public int qubits {get;set;} public int shots {get;set;} public string seed {get;set;} public int[] wires {get;set;} public Dictionary<string,int> counts {get;set;}
 }
 public static byte[] Request(int qubits,int shots,ulong seed,int[] measured,IList<Gate> gates) {
  if(qubits<0 || qubits>25 || shots<1 || shots>100000 || gates==null || gates.Count>4096)
   throw new ArgumentException("Use 0–25 qubits, 1–100,000 shots and at most 4096 gates.");
  var text=new StringBuilder("QSAMPLE1\n");
  Action<ulong> number=value=>text.Append(value.ToString(CultureInfo.InvariantCulture)).Append('\n');
  number((ulong)qubits);number((ulong)shots);number(seed);
  Action<int[],int> wires=delegate(int[] values,int maximum) {
   if(values==null || values.Length>maximum)throw new ArgumentException("Invalid sampling wire list.");
   var seen=new HashSet<int>();number((ulong)values.Length);
   foreach(int wire in values) {
    if(wire<0 || wire>=qubits || !seen.Add(wire))throw new ArgumentException("Sampling wires must be distinct and inside the register.");
    number((ulong)wire);
   }
  };
  wires(measured,qubits);number((ulong)gates.Count);
  foreach(var gate in gates) {
   if(gate==null || gate.Wires==null || gate.Wires.Length==0 || String.IsNullOrWhiteSpace(gate.Expression) || gate.Expression.IndexOf('\0')>=0)
    throw new ArgumentException("Each sampling gate needs a matrix expression and target wires.");
   wires(gate.Wires,3);
   int length=Encoding.UTF8.GetByteCount(gate.Expression);
   if(length>4096)throw new ArgumentException("A sampling gate expression exceeds 4096 UTF-8 bytes.");
   number((ulong)length);text.Append(gate.Expression);
   if(text.Length>1100000)throw new ArgumentException("Sampling request is too large.");
  }
  byte[] bytes=new UTF8Encoding(false,true).GetBytes(text.ToString());
  if(bytes.Length>1100000)throw new ArgumentException("Sampling request is too large.");
  return bytes;
 }
 public static Result ReadResult(string json,int qubits,int shots,ulong seed,int[] measured) {
  var result=new JavaScriptSerializer {MaxJsonLength=8000000,RecursionLimit=12}.Deserialize<Result>(json);
  if(result==null || result.qubits!=qubits || result.shots!=shots || result.seed!=seed.ToString(CultureInfo.InvariantCulture) ||
     result.wires==null || result.wires.Length!=measured.Length || result.counts==null || result.counts.Count>shots)
   throw new InvalidDataException("The sampler returned an inconsistent response.");
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
 public static Task<Result> Run(string worker,int qubits,int shots,ulong seed,int[] measured,IList<Gate> gates,CancellationToken cancellation) {
  // Serialize before handing work to another thread, so editor changes cannot alter a run.
  byte[] request=Request(qubits,shots,seed,measured,gates);
  int[] order=(int[])measured.Clone();
  return Task.Run(async delegate {
   cancellation.ThrowIfCancellationRequested();
   using(var process=new Process()) {
    process.StartInfo=new ProcessStartInfo(worker,"--sample") {UseShellExecute=false,CreateNoWindow=true,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8,WorkingDirectory=Path.GetDirectoryName(worker)};
    process.StartInfo.EnvironmentVariables["QALCULATE_DEFINITIONS_DIR"]=Path.Combine(Path.GetDirectoryName(worker),"data");
    process.Start();var clock=Stopwatch.StartNew();
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
     return ReadResult(stdout,qubits,shots,seed,order);
    } finally {if(!process.HasExited) {process.Kill();process.WaitForExit();}}
   }
  });
 }
}
