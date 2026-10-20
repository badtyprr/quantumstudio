// GPL-2.0-or-later; see COPYING.
using System;
using System.Diagnostics;
using System.IO;
using System.Text;
using System.Threading.Tasks;

static class QasmImport {
 internal static byte[] ReadSource(string path) {return BoundedUtf8File.Read(path,262144,"OpenQASM source");}
 public static string Compile(string path,bool publishedU=false,bool classical=false) {
  byte[] source=ReadSource(path);
  return Run((publishedU ? "--published-u " : "")+(classical ? "--classical" : ""),source,262144);
 }
 // File import lets the compiler capture local dependencies and their original
 // bytes. Defaults to the file's directory; callers can explicitly select a
 // wider root when reopening a snapshot whose entry lives in a subdirectory.
 public static string CompileSource(string path,bool publishedU=false,bool classical=false,bool moduleHeaders=false,string selectedRoot=null) {
  string full=Path.GetFullPath(path);
  return Run("--source-file "+QuoteArgument(full)+(publishedU ? " --published-u" : "")+
   (classical ? " --classical" : "")+(moduleHeaders ? " --module-headers" : "")+
   (selectedRoot==null ? "" : " --source-root "+QuoteArgument(Path.GetFullPath(selectedRoot))),null,4194304);
 }
 public static string CheckSource(string snapshot,string selectedRoot) {
  if(String.IsNullOrWhiteSpace(selectedRoot))throw new ArgumentException("Select a source root directory.");
  if(snapshot==null)throw new ArgumentNullException("snapshot");
  byte[] bytes=new UTF8Encoding(false,true).GetBytes(snapshot);
  if(bytes.Length>4194304)throw new InvalidDataException("Source snapshot is too large.");
  return Run("--check-source --source-root "+QuoteArgument(Path.GetFullPath(selectedRoot)),bytes,4194304);
 }
 internal static string QuoteArgument(string value) {
  if(value==null || value.IndexOf('\0')>=0)throw new ArgumentException("Invalid compiler argument.");
  var result=new StringBuilder("\"");int slashes=0;
  foreach(char c in value) {
   if(c=='\\'){slashes++;continue;}
   if(c=='"')result.Append('\\',slashes*2+1);else result.Append('\\',slashes);
   result.Append(c);slashes=0;
  }
  result.Append('\\',slashes*2);return result.Append('"').ToString();
 }
 static string Run(string arguments,byte[] source,int maximumBytes) {
  string executable=Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"qasm-import","qasm-import.exe");
  var start=new ProcessStartInfo(executable) {UseShellExecute=false,CreateNoWindow=true,RedirectStandardInput=true,RedirectStandardOutput=true,RedirectStandardError=true,StandardOutputEncoding=Encoding.UTF8,StandardErrorEncoding=Encoding.UTF8};
  start.Arguments=arguments;
  using(var process=new Process {StartInfo=start}) {
   process.Start();
   try {
    var output=process.StandardOutput.ReadToEndAsync();var error=process.StandardError.ReadToEndAsync();
    // Send bytes explicitly so non-ASCII comments are independent of the Windows code page.
    var write=Task.Run(delegate {if(source!=null)process.StandardInput.BaseStream.Write(source,0,source.Length);process.StandardInput.Close();});
    if(!process.WaitForExit(30000))throw new InvalidDataException("OpenQASM compilation exceeded 30 seconds.");
    string result=output.Result, diagnostic=error.Result;
    if(process.ExitCode!=0)throw new InvalidDataException(String.IsNullOrWhiteSpace(diagnostic) ? "OpenQASM compilation failed." : diagnostic.Trim());
    write.Wait();
    if(Encoding.UTF8.GetByteCount(result)>maximumBytes)throw new InvalidDataException("Compiled circuit is too large.");
    return result;
   } finally {if(!process.HasExited)process.Kill();}
  }
 }
}
