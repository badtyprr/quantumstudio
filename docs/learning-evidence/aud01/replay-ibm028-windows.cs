// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;


using System.Windows.Threading;
using System.Web.Script.Serialization;
class PhaseEstimationGuiReplay {
 static Type app;static Assembly assembly;static int checks,clipboardRetries;
 static BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
 static object Field(string name) {return app.GetField(name,flags).GetValue(null);}
 static object Call(string name,params object[] args) {return app.GetMethod(name,flags).Invoke(null,args);}
 static void Require(bool condition,string message) {if(!condition)throw new Exception(message);checks++;}
 static async Task Calculate(string expression) {
  ((TextBox)Field("input")).Text=expression;var run=(Button)Field("run");run.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
  DateTime deadline=DateTime.UtcNow.AddSeconds(20);
  while(!run.IsEnabled && DateTime.UtcNow<deadline)await Task.Delay(20);
  Require(run.IsEnabled,"Calculation did not finish");
  string label=((TextBlock)Field("resultLabel")).Text;
  Require(label=="EXACT RESULT" || label=="CHECK YOUR EXPRESSION" || label=="TIME ALLOWANCE REACHED" || label=="APPROXIMATE RESULT","Unexpected result label: "+label);
 }
 static async Task<string> Copy() {
  for(int attempt=0;attempt<10;attempt++) {
   try {
    string sentinel="scalar-product-test-"+Guid.NewGuid().ToString("N");Clipboard.SetText(sentinel);
    Require(Clipboard.GetText()==sentinel,"Clipboard sentinel was not installed");
    ((Button)((Window)Field("window")).FindName("Copy")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    string copied=Clipboard.GetText();
    if(((TextBlock)Field("status")).Text=="Result copied." && copied!=(string)sentinel && copied==(string)Field("copyText"))return copied;
   }catch(System.Runtime.InteropServices.COMException ex) {
    if(ex.ErrorCode!=unchecked((int)0x800401D0))throw;
   }
   clipboardRetries++;await Task.Delay(50);
  }
  throw new Exception("Clipboard did not expose a fresh copied result after ten attempts");
 }
 static DataObject PreserveClipboard() {
  var saved=new DataObject();var current=Clipboard.GetDataObject();if(current==null)return saved;
  string[] formats=current.GetFormats(false);if(formats.Length>32)throw new Exception("Clipboard format bound");
  foreach(string format in formats) {
   object value=current.GetData(format,false);
   if(value is string) {if(((string)value).Length>1048576)throw new Exception("Clipboard text bound");}
   else if(value is MemoryStream) {var stream=(MemoryStream)value;if(stream.Length>8388608)throw new Exception("Clipboard stream bound");value=new MemoryStream(stream.ToArray());}
   else if(value is byte[]) {if(((byte[])value).Length>8388608)throw new Exception("Clipboard byte bound");value=((byte[])value).Clone();}
   else throw new Exception("Clipboard format cannot be preserved safely");
   saved.SetData(format,value,false);
  }
  return saved;
 }
 [STAThread] static int Main(string[] args) {
  bool reenterText=args.Length==3 && args[2]=="--reenter-text";
  bool sessionsOnly=reenterText || (args.Length==3 && args[2]=="--sessions-only");
  if(args.Length!=2 && !sessionsOnly)return 2;
  string output=Path.GetFullPath(args[1]);if(!Directory.Exists(output))return 2;
  var serializer=new JavaScriptSerializer();var records=new System.Collections.Generic.List<object>();
  DataObject previousClipboard=null;bool clipboardCaptured=false,clipboardRestored=false;int code=1;
  assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));app=assembly.GetType("QuantumStudio");
  app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(Path.GetFullPath(args[0])));
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   try {
    if(!sessionsOnly){previousClipboard=PreserveClipboard();clipboardCaptured=true;}
    ((ComboBox)Field("evaluation")).SelectedIndex=0;
    ((ComboBox)Field("timeAllowance")).SelectedIndex=0;
    var entries=serializer.Deserialize<string[][]>(File.ReadAllText(Path.Combine(output,"inputs.json")));
    foreach(string[] entry in entries) {
     Type matrixType=assembly.GetType("MatrixDeclaration");
     bool declareV=entry[0]=="IBM028-2ff07f29-M123";
     Array declarations=Array.CreateInstance(matrixType,declareV ? 1 : 0);
     if(declareV) {
      object definition=Activator.CreateInstance(matrixType);
      foreach(var pair in new [] {new[]{"Name","V"},new[]{"Rows","4"},new[]{"Columns","4"},new[]{"Property","Unitary"}})
       matrixType.GetProperty(pair[0]).SetValue(definition,pair[1],null);
      declarations.SetValue(definition,0);
     }
     app.GetField("matrices",flags).SetValue(null,declarations);
     int requestedMode=Int32.Parse(entry[2]);((ComboBox)Field("mode")).SelectedIndex=requestedMode;
     await Calculate(entry[1]);
     string label=((TextBlock)Field("resultLabel")).Text;
     var row=new System.Collections.Generic.Dictionary<string,object>();
     row["id"]=entry[0];row["label"]=label;row["display"]=((TextBox)Field("output")).Text;
     if(label=="EXACT RESULT") {
      string copied=null;if(!sessionsOnly){copied=await Copy();row["copy"]=copied;}
      object snap=Call("CaptureSession");string saved=serializer.Serialize(snap);
      string path=Path.Combine(output,entry[0]+".qsession");
      assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{path,snap});
      ((TextBox)Field("input")).Text="7";
      ((ComboBox)Field("mode")).SelectedIndex=1;
      Call("OpenSession",path);
      string actual=serializer.Serialize(Call("CaptureSession"));bool same=(bool)Call("SameSessionSnapshot",saved,actual);if(!same){File.WriteAllText(Path.Combine(output,"before.json"),saved);File.WriteAllText(Path.Combine(output,"after.json"),actual);} Require(same,"Session mismatch for "+entry[0]);
      string restored=((TextBox)Field("input")).Text;
      Require(restored==entry[1] && ((ComboBox)Field("mode")).SelectedIndex==requestedMode,"Restored input/mode mismatch");
      await Calculate(restored);
      if(sessionsOnly) {
       row["restored_same"]=((TextBlock)Field("resultLabel")).Text==label && ((TextBox)Field("output")).Text==(string)row["display"];
       Require((bool)row["restored_same"],"Restored display mismatch for "+entry[0]);
       if(reenterText) {
        string text=(string)Field("copyText") ?? ((TextBox)Field("output")).Text;
        row["copy_text"]=text;await Calculate(text);
        row["reentry_label"]=((TextBlock)Field("resultLabel")).Text;
        row["reentry_text"]=(string)Field("copyText") ?? ((TextBox)Field("output")).Text;
       }
      } else {
      string restoredCopy=await Copy();
      row["restored_same"]=((TextBlock)Field("resultLabel")).Text==label && restoredCopy==copied;
      if(restoredCopy!=copied)row["restored_copy"]=restoredCopy;
      await Calculate(copied);
      string reentryLabel=((TextBlock)Field("resultLabel")).Text;
      row["reentry_label"]=reentryLabel;
      if(reentryLabel!="CHECK YOUR EXPRESSION")row["second_copy"]=await Copy();
      else row["reentry_diagnostic"]=((TextBox)Field("output")).Text;
      }
     }
     records.Add(row);
     File.WriteAllText(Path.Combine(output,"records.json"),serializer.Serialize(records));
    }
    code=0;
   }catch(Exception ex){File.WriteAllText(Path.Combine(output,"failure.txt"),ex.ToString());}
   finally{
    if(clipboardCaptured)try {if(previousClipboard.GetFormats(false).Length==0)Clipboard.Clear();else Clipboard.SetDataObject(previousClipboard,true);clipboardRestored=true;}catch(Exception ex){code=1;File.WriteAllText(Path.Combine(output,"clipboard-restore-failure.txt"),ex.ToString());}
    File.WriteAllText(Path.Combine(output,"result.json"),serializer.Serialize(new {passed=code==0,checks=checks,calls=records.Count,sessionsOnly=sessionsOnly,clipboardRetries=clipboardRetries,clipboardRestored=clipboardRestored}));
    Application.Current.Shutdown();
   }
  }),DispatcherPriority.ApplicationIdle);
  app.GetMethod("Main",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{new string[0]});return code;
 }
}
