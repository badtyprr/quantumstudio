// GPL-2.0-or-later; see COPYING. Hosted development acceptance, not a release.
using System;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Security.Cryptography;
using System.Threading.Tasks;
using System.Web.Script.Serialization;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;

class ComplementGuiTests {
 static string evidence,sessionHash;
 static Type app;
 static Assembly assembly;
 static int checks,clipboardReads,clipboardRetries,sessionChecks;
 static readonly List<string> completed=new List<string>();
 static readonly JavaScriptSerializer json=new JavaScriptSerializer();
 static readonly BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
 static object Field(string name) {return app.GetField(name,flags).GetValue(null);}
 static object Call(string name,params object[] arguments) {return app.GetMethod(name,flags).Invoke(null,arguments);}
 static void Require(bool value,string message) {if(!value)throw new Exception(message);checks++;}
 static void Log(object value) {File.AppendAllText(Path.Combine(evidence,"actions.jsonl"),json.Serialize(value)+Environment.NewLine);}
 static string Normalize(string value) {return value.Replace(" ","").Replace("\r","").Replace("\n","").Replace("\u2215","/").Replace("\u2212","-");}
 static string Hash(string path) {using(var hash=SHA256.Create())using(var file=File.OpenRead(path))return BitConverter.ToString(hash.ComputeHash(file)).Replace("-","").ToLowerInvariant();}
 static void Complete(string id) {Require(!completed.Contains(id),"Duplicate case "+id);completed.Add(id);Log(new {completed_case=id});}
 static void Capture(string name) {
  var window=(Window)Field("window");window.UpdateLayout();
  var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(window);
  var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));
  using(var file=File.Create(Path.Combine(evidence,name+".png")))encoder.Save(file);
 }
 static async Task Calculate(string expression,string diagnostic=null) {
  Log(new {action="Calculate",input=expression,expected_diagnostic=diagnostic});
  ((TextBox)Field("input")).Text=expression;
  var run=(Button)Field("run");Require(run.IsEnabled,"Calculate was busy before input");
  run.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
  DateTime deadline=DateTime.UtcNow.AddSeconds(60);
  while(!run.IsEnabled && DateTime.UtcNow<deadline)await Task.Delay(20);
  Require(run.IsEnabled,"Calculation did not finish");
  string label=((TextBlock)Field("resultLabel")).Text;
  string output=((TextBox)Field("output")).Text;
  Log(new {action="Result",input=expression,label=label,output=output});
  Require(diagnostic==null ? label.EndsWith("RESULT") : label=="CHECK YOUR EXPRESSION",expression+" => "+label+": "+output);
  if(diagnostic!=null) {
   Require(output.Contains(diagnostic),"Wrong rejection: "+output);
   Require(Field("copyText")==null,"Rejected expression retained stale value");
  }
 }
 static async Task<string> Copy() {
  string sentinel="DEV05-sentinel-"+Guid.NewGuid().ToString("N");Clipboard.SetText(sentinel);
  for(int attempt=0;attempt<10;attempt++) {
   ((Button)((Window)Field("window")).FindName("Copy")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
   try {
    string text=Clipboard.GetText();
    if(!String.IsNullOrEmpty(text) && text!=sentinel && text==(string)Field("copyText")) {
     clipboardReads++;Log(new {action="NativeClipboardRead",text=text});return text;
    }
   } catch(System.Runtime.InteropServices.COMException ex) {if(ex.ErrorCode!=unchecked((int)0x800401D0))throw;}
   clipboardRetries++;await Task.Delay(50);
  }
  throw new Exception("Actual Copy did not expose this result through the native Clipboard");
 }
 static async Task PasteAndCalculate(string copied) {
  var input=(TextBox)Field("input");input.Clear();input.Paste();
  Require(input.Text==copied,"Native Clipboard paste changed input");
  Log(new {action="PasteIntoInput",text=input.Text});await Calculate(input.Text);
 }
 static async Task Value(string id,string expression,string expected,string capture=null) {
  await Calculate(expression);string copied=await Copy();
  Require(Normalize(copied)==expected,"Wrong exact value: "+expression+" => "+copied);
  if(capture!=null)Capture(capture);
  await PasteAndCalculate(copied);
  Require(Normalize(await Copy())==expected,"Copy/paste/recalculation changed "+id);
  Complete(id);
 }
 static async Task Reject(string id,string expression,string message,string capture=null) {
  await Calculate(expression,message);if(capture!=null)Capture(capture);Complete(id);
 }
 static async Task Run() {
  ((ComboBox)Field("mode")).SelectedIndex=0;((ComboBox)Field("evaluation")).SelectedIndex=0;
  // Independent expectations: NOT 0=1, NOT 1=0; X and XOR1 are controls.
  // The established one-row bra serialization is a vector, not a 1x2 matrix.
  await Value("tex-zero",@"\vert \neg 0\rangle","matrix(2,1,[0,1])","concrete");
  await Value("bra-one","<\u00ac1|","vector(1,0)","bra");
  await Value("plain-bra-control","<0|","vector(1,0)");
  await Value("x-control","X|0>","matrix(2,1,[0,1])");
  await Value("xor-control","|0 \u2295 1>","matrix(2,1,[0,1])");
  const string original="|\u00acb>";
  // Preserve both the affine complement and its original two-state domain.
  const string guarded="qbasis(qsub(1,'b'),2)";
  await Calculate(original);string deferred=await Copy();
  Require(Normalize(deferred)==guarded,"Deferred complement lost its exact two-state guard");
  Capture("deferred");await PasteAndCalculate(deferred);
  Require(Normalize(await Copy())==guarded,"Deferred guard changed on Clipboard re-entry");Complete("deferred-copy");
  await Value("deferred-b0","replace("+deferred+",b,0)","matrix(2,1,[0,1])");
  await Value("deferred-b1","replace("+deferred+",b,1)","matrix(2,1,[1,0])");

  await Calculate(original);Require(Normalize(await Copy())==guarded,"Original expression no longer deferred");
  string session=Path.Combine(evidence,"complement.qsession");object snapshot=Call("CaptureSession");
  string saved=json.Serialize(snapshot);
  // Real application serializer and open path; intentionally no file-dialog claim.
  assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
  sessionHash=Hash(session);Log(new {action="SessionStore.Save",path=session,sha256=sessionHash,native_file_dialog=false});
  await Calculate("42");Require(json.Serialize(Call("CaptureSession"))!=saved,"Session mutation control failed");
  Call("OpenSession",session);
  Require(json.Serialize(Call("CaptureSession"))==saved,"Original expression/history changed on session reopen");
  Require(((TextBox)Field("input")).Text==original,"Reopened input differs from original deferred expression");
  await Calculate(((TextBox)Field("input")).Text);string reopened=await Copy();
  Require(Normalize(reopened)==guarded,"Reopened result lost its guard");
  Require(Hash(session)==sessionHash,"Session bytes changed during reopen/recalculation");
  sessionChecks++;Capture("reopened");Complete("session-reopen");
  await Value("reopened-b0","replace("+reopened+",b,0)","matrix(2,1,[0,1])");
  await Value("reopened-b1","replace("+reopened+",b,1)","matrix(2,1,[1,0])");
  const string domain="basis(index,dimension)";
  await Reject("invalid-two","replace("+reopened+",b,2)",domain,"invalid-domain");
  await Reject("invalid-negative","replace("+reopened+",b,-1)",domain);
  await Reject("invalid-fraction","replace("+reopened+",b,1/2)",domain);
  await Value("opaque-notable","|notable>","qketstate(\"notable\")","opaque");
  await Value("opaque-not0","|not0>","qketstate(\"not0\")");
  await Reject("reject-multiletter","|\u00acnotable>","A complemented basis bit requires","invalid-syntax");
  Require(completed.Count==17,"Incomplete finite GUI contract");
 }
 [STAThread] static int Main(string[] args) {
  int code=1;string failure=null;
  if(args.Length!=2)throw new ArgumentException("Application and fresh evidence directory required");
  evidence=Path.GetFullPath(args[1]);
  if(Directory.Exists(evidence))throw new IOException("Fresh driver evidence required");
  Directory.CreateDirectory(evidence);
  try {
   assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));app=assembly.GetType("QuantumStudio");
   app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(Path.GetFullPath(args[0])));
   Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
    try {await Run();code=0;}
    catch(Exception ex) {failure=ex.ToString();try{Capture("failure");}catch(Exception capture){Log(new {capture_error=capture.ToString()});}}
    finally {Application.Current.Shutdown();}
   }),DispatcherPriority.ApplicationIdle);
   app.GetMethod("Main",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{new string[0]});
  } catch(Exception ex) {failure=ex.ToString();code=1;}
  File.WriteAllText(Path.Combine(evidence,"result.json"),json.Serialize(new {
   passed=code==0,checks=checks,cases=completed,actual_clipboard_reads=clipboardReads,clipboard_retries=clipboardRetries,
   actual_session_checks=sessionChecks,session_sha256=sessionHash,native_file_dialogs=false,
   session_route="CaptureSession/SessionStore.Save/OpenSession plus actual GUI recalculation",failure=failure}));
  return code;
 }
}
