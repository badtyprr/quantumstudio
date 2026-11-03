// GPL-2.0-or-later; see COPYING.
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Threading;

class SteaneTransversalGuiTests {
 static int checks;
 static void Require(bool value,string message) {if(!value)throw new Exception(message);checks++;}
 static object Call(object instance,string method,params object[] args) {
  return instance.GetType().GetMethod(method,BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic).Invoke(instance,args);
 }
 static string Canonical(object value) {
  var serializer=new JavaScriptSerializer {MaxJsonLength=8000000};
  var fields=value as Dictionary<string,object>;
  if(fields!=null) {
   var keys=new List<string>(fields.Keys);keys.Sort(StringComparer.Ordinal);var parts=new List<string>();
   foreach(string key in keys)parts.Add(serializer.Serialize(key)+":"+Canonical(fields[key]));
   return "{"+String.Join(",",parts)+"}";
  }
  var array=value as object[];
  if(array!=null) {var parts=new List<string>();foreach(object item in array)parts.Add(Canonical(item));return "["+String.Join(",",parts)+"]";}
  return serializer.Serialize(value);
 }
 static string Snapshot(object composer) {
  return Canonical(new JavaScriptSerializer {MaxJsonLength=8000000}.DeserializeObject((string)Call(composer,"Snapshot")));
 }
 static void VerifyRoundtrip(Assembly assembly,Window composer,string source,string report) {
  string before=Snapshot(composer);
  string envelope=(string)assembly.GetType("QasmImport").GetMethod("CompileSource").Invoke(null,new object[]{source,false,false,false,null});
  Call(composer,"ImportSource",envelope,false);string imported=Snapshot(composer),expression=(string)Call(composer,"Expression");
  Require((bool)Call(composer,"Undo") && Snapshot(composer)==before,"Undo changed circuit data");
  Require((bool)Call(composer,"Redo") && Snapshot(composer)==imported,"Redo changed source/circuit data");
  Call(composer,"SaveCircuit",report+".qcircuit");
  Require((bool)Call(composer,"AddGate","X","0",""),"Could not edit imported circuit");
  Require((bool)Call(composer,"Undo") && Snapshot(composer)==imported,"Edit undo changed source/circuit data");
  Call(composer,"OpenCircuit",report+".qcircuit");
  Require(Snapshot(composer)==imported && (string)Call(composer,"Expression")==expression,"Save/reopen changed source or expression");
  File.WriteAllText(report+".qasm",(string)Call(composer,"OpenQasm"),new UTF8Encoding(false));
  Call(composer,"FitWires");Call(composer,"CaptureSource",report+".png");
  composer.Width=composer.MinWidth;composer.Height=composer.MinHeight;composer.UpdateLayout();
  Call(composer,"FitWires");Call(composer,"CaptureSource",report+".minimum.png");
 }
 [STAThread] static int Main(string[] args) {
  // Compiler discovery uses the application's base directory. Host the driver
  // against the real package without copying or changing its payload files.
  if(args.Length==3) {
   AppDomain domain=AppDomain.CreateDomain("Steane packaged GUI",null,new AppDomainSetup {ApplicationBase=Path.GetDirectoryName(Path.GetFullPath(args[0]))});
   try {return domain.ExecuteAssembly(Assembly.GetExecutingAssembly().Location,new[]{args[0],args[1],args[2],"hosted"});}
   finally {AppDomain.Unload(domain);}
  }
  string appPath=Path.GetFullPath(args[0]),fixtures=Path.GetFullPath(args[1]),output=Path.GetFullPath(args[2]);
  Directory.CreateDirectory(output);int code=1;
  Assembly assembly=Assembly.LoadFrom(appPath);Type app=assembly.GetType("QuantumStudio");
  BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
  app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(appPath));
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   Window composer=null,sampling=null;
   try {
    Window main=(Window)app.GetField("window",flags).GetValue(null);
    Type composerType=assembly.GetType("CircuitComposer"),samplingType=assembly.GetType("SamplingWindow");
    foreach(string name in new[]{"column-0","column-1","column-2","column-3","coherent-echo"}) {
     string report=Path.Combine(output,name);
     composer=(Window)Activator.CreateInstance(composerType,new object[]{main,new Action<string>(delegate(string value){})});
     composer.Show();
     File.WriteAllText(report+".before.json",(string)composerType.GetMethod("Snapshot",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(composer,null));
     // Compare JSON structurally: serializer property order is not circuit
     // identity. Preserve array order, values and all source metadata.
     VerifyRoundtrip(assembly,composer,Path.Combine(fixtures,name+".qasm"),report);
     Require(File.Exists(report+".qcircuit") && File.Exists(report+".qasm"),"Missing saved/exported circuit");
     object gates=composerType.GetMethod("SamplingGates").Invoke(composer,null);
     sampling=(Window)Activator.CreateInstance(samplingType,new object[]{composer,14,gates});sampling.Show();
     // This hook raises the actual Run samples button, waits for its worker,
     // checks displayed rows/control cleanup and captures the shown result.
     Task task=(Task)samplingType.GetMethod("VerifySampling").Invoke(sampling,new object[]{report+".samples.png",false,(ulong)674062,null,null});
     await task;
     object result=task.GetType().GetProperty("Result").GetValue(task,null);
     string json=new JavaScriptSerializer().Serialize(result);File.WriteAllText(report+".samples.json",json);
     var parsed=new JavaScriptSerializer().Deserialize<Dictionary<string,object>>(json);
     var counts=(Dictionary<string,object>)parsed["counts"];
     var support=new HashSet<string>();
     if(name=="coherent-echo")support.Add(new string('0',14));
     else {
      int input=name[name.Length-1]-'0',a=input>>1,b=input&1;
      foreach(int u in new[]{0,30,45,51,75,85,102,120})foreach(int v in new[]{0,30,45,51,75,85,102,120})
       support.Add(Convert.ToString(((u^(127*a))<<7)|(v^(127*(a^b))),2).PadLeft(14,'0'));
     }
     Require(support.SetEquals(counts.Keys),"GUI outcome support differs from independent CSS cosets");
     int total=0;foreach(object count in counts.Values)total+=Convert.ToInt32(count);
     Require(total==10000,"GUI lost samples");
     sampling.Close();sampling=null;composer.Close();composer=null;
    }
    File.WriteAllText(Path.Combine(output,"result.txt"),"PASS: "+checks+" Steane GUI assertions; five imported/saved/exported circuits and actual sampling-button results");code=0;
   }catch(Exception error){
    File.WriteAllText(Path.Combine(output,"result.txt"),error.ToString());
    if(composer!=null) {
     Type type=composer.GetType();var serializer=new JavaScriptSerializer();
     foreach(string field in new[]{"snapshot","past","future"})File.WriteAllText(Path.Combine(output,"failure-"+field+".json"),serializer.Serialize(type.GetField(field,BindingFlags.NonPublic|BindingFlags.Instance).GetValue(composer)));
     File.WriteAllText(Path.Combine(output,"failure-current.json"),(string)type.GetMethod("Snapshot",BindingFlags.NonPublic|BindingFlags.Instance).Invoke(composer,null));
    }
   }
   finally {if(sampling!=null)sampling.Close();if(composer!=null)composer.Close();Application.Current.Shutdown();}
  }),DispatcherPriority.ApplicationIdle);
  app.GetMethod("Main",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{new string[0]});return code;
 }
}
