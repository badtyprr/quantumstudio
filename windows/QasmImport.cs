// GPL-2.0-or-later; see COPYING.
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading.Tasks;

static class QasmImport {
 internal static byte[] ReadSource(string path) {
  const int maximum=262144;
  using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)) {
   if(file.Length>maximum)throw new InvalidDataException("OpenQASM files must be at most 256 KB.");
   using(var buffer=new MemoryStream()) {
    byte[] chunk=new byte[8192];int count;
    while((count=file.Read(chunk,0,Math.Min(chunk.Length,maximum+1-(int)buffer.Length)))>0) {
     buffer.Write(chunk,0,count);
     if(buffer.Length>maximum)throw new InvalidDataException("OpenQASM files must be at most 256 KB.");
    }
    byte[] source=buffer.ToArray();
    int offset=source.Length>=3 && source[0]==0xef && source[1]==0xbb && source[2]==0xbf ? 3 : 0;
    // Validate before starting the compiler; never silently replace malformed input.
    var utf8=new UTF8Encoding(false,true);
    string text=utf8.GetString(source,offset,source.Length-offset);
    return utf8.GetBytes(text);
   }
  }
 }
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
