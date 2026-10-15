// GPL-2.0-or-later; see COPYING.
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading.Tasks;

static class QasmImport {
 internal static byte[] ReadSource(string path) {return BoundedUtf8File.Read(path,262144,"OpenQASM source");}
 public static string Compile(string path,bool publishedU=false) {
  byte[] source=ReadSource(path);
  string executable=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"qasm-import","qasm-import.exe");
  var start=new ProcessStartInfo(executable) {UseShellExecute=false,CreateNoWindow=true,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8};
  if(publishedU)start.Arguments="--published-u";
  using(var process=new Process {StartInfo=start}) {
   process.Start();
   try {
    var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();
    // Send bytes explicitly so non-ASCII comments are independent of the Windows code page.
    var write=Task.Run(delegate {process.StandardInput.BaseStream.Write(source,0,source.Length);process.StandardInput.Close();});
    if(!process.WaitForExit(30000))throw new InvalidDataException("OpenQASM compilation exceeded 30 seconds.");
    string result=output.Result, diagnostic=error.Result;
    if(process.ExitCode!=0)throw new InvalidDataException(String.IsNullOrWhiteSpace(diagnostic) ? "OpenQASM compilation failed." : diagnostic.Trim());
    write.Wait();
    if(result.Length>262144)throw new InvalidDataException("Compiled circuit is too large.");
    return result;
   } finally {if(!process.HasExited)process.Kill();}
  }
 }
}
