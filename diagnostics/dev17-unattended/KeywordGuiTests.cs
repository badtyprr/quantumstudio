// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using System.Web.Script.Serialization;
class KeywordGuiTests {
 static string evidence;
 static Type app;static Assembly assembly;static int checks,clipboardRetries;
 static BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
 static object Field(string name) {return app.GetField(name,flags).GetValue(null);}
 static object Call(string name,params object[] args) {return app.GetMethod(name,flags).Invoke(null,args);}
 static void Require(bool condition,string message) {if(!condition)throw new Exception(message);checks++;}
 static async Task Calculate(string expression,string diagnostic=null) {
  File.AppendAllText(Path.Combine(evidence,"actions.log"),"CALCULATE: "+expression+Environment.NewLine);
  ((TextBox)Field("input")).Text=expression;var run=(Button)Field("run");run.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
  DateTime deadline=DateTime.UtcNow.AddSeconds(60);
  while(!run.IsEnabled && DateTime.UtcNow<deadline)await Task.Delay(20);
  Require(run.IsEnabled,"Calculation did not finish");
  string label=((TextBlock)Field("resultLabel")).Text;
  Require(diagnostic!=null ? label=="CHECK YOUR EXPRESSION" : label.EndsWith("RESULT"),expression+" => "+label+": "+((TextBox)Field("output")).Text);
  if(diagnostic!=null)Require(((TextBox)Field("output")).Text.Contains(diagnostic),"Wrong error diagnostic");
 }
 static void Capture(string path) {
  Window window=(Window)Field("window");window.UpdateLayout();
  var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(window);
  var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using(var file=File.Create(path))encoder.Save(file);
 }
 static async Task<string> Copy() {
  Clipboard.SetText("DEV17-sentinel-"+Guid.NewGuid().ToString("N"));
  for(int attempt=0;attempt<10;attempt++) {
   ((Button)((Window)Field("window")).FindName("Copy")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
   try {string copied=Clipboard.GetText();if(copied==(string)Field("copyText")){File.AppendAllText(Path.Combine(evidence,"actions.log"),"CLIPBOARD: "+copied+Environment.NewLine);return copied;}}
   catch(System.Runtime.InteropServices.COMException ex) {if(ex.ErrorCode!=unchecked((int)0x800401D0))throw;}
   clipboardRetries++;await Task.Delay(50);
  }
  throw new Exception("Clipboard did not expose the current copied result after ten attempts");
 }
 static string Normalize(string value) {return value.Replace(" ","").Replace("\r","").Replace("\n","").Replace("∕","/").Replace("−","-");}
 static async Task Matrix(string expression,string expected) {
  await Calculate(expression);string copied=await Copy();
  Require(Normalize(copied)==expected,"Wrong full exact matrix: "+expression+" => "+copied);
  await Calculate(copied);Require(Normalize(await Copy())==expected,"Matrix Copy/re-entry changed exact cells");
 }
 // Calculate launches a fresh worker. save creates a real KnownVariable before
 // function parses the inner quantum expression (a finite sum binder is not an assignment).
 // Only fixture-authored expressions without single quotes enter this wrapper.
 static string AssignedK(string expression,int value=0) {
  if(expression.Contains("'"))throw new ArgumentException("AssignedK requires a single-quote-free fixture expression");
  return "if(save("+value+",\"k\")="+value+",function('quantum: "+expression+"'),-1)";
 }
 static async Task NumericK(string rho,string mixture,string half) {
  int initial=checks;
  // Native oracle: quantum-named-subsystem-test.cc. Independently, summing
  // rho[2*a+b,2*a+d] over a gives [[3/4,1/4],[1/4,1/4]].
  foreach(string selector in new[]{"k","[k]","k,[2,2]"})
   await Matrix(AssignedK("ptrace("+rho+","+selector+")"),mixture);
  await Matrix(AssignedK("ptrace("+rho+",k)",1),half);

  // With k=0 and the quoted binder not=1, both factors of I4 are traced: 4.
  string compatibility=AssignedK("sum(ptrace(identity(4),[k,\"not\"]),1,1,\"not\")");
  await Calculate(compatibility);string scalar=await Copy();
  Require(Normalize(scalar)=="4","Assigned k / quoted not compatibility must be exactly 4");
  Capture(Path.Combine(evidence,"numeric-k-compatibility.png"));
  string session=Path.Combine(evidence,"numeric-k.qsession");object snapshot=Call("CaptureSession");
  assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
  var serializer=new JavaScriptSerializer();string saved=serializer.Serialize(snapshot);
  await Calculate(scalar);Require(Normalize(await Copy())=="4","Compatibility scalar Copy/re-entry changed");
  Call("OpenSession",session);Require(serializer.Serialize(Call("CaptureSession"))==saved,"Assigned-k expression/history changed on reopen");
  await Calculate(((TextBox)Field("input")).Text);Require(Normalize(await Copy())=="4","Reopened assigned-k compatibility changed");
  Capture(Path.Combine(evidence,"numeric-k-reopened.png"));

  // Deliberately put k second: literal k must differ from numeric index zero.
  // function's generic x/y/z rewriting recognizes the registered qsubsystems
  // spelling; the unregistered subsystems alias is not safe inside that wrapper.
  string mapping="qsubsystems("+rho+",[not,k],[2,2])";
  await Matrix(AssignedK("ptrace("+mapping+",k)"),half);
  await Calculate(AssignedK(mapping));string declaration=await Copy();
  string expected="qsubsystems(matrix(4,4,[1/2,0,0,0,0,0,0,0,0,0,1/4,1/4,0,0,1/4,1/4]),vector(\"not\",\"k\"),vector(2,2))";
  Require(Normalize(declaration).Replace("'","\"")==expected,"Assigned k changed ordered mapping metadata or matrix");
  await Calculate(declaration);Require(await Copy()==declaration,"Assigned-k declaration Copy/re-entry changed");
  session=Path.Combine(evidence,"numeric-k-mapping.qsession");snapshot=Call("CaptureSession");
  assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
  saved=serializer.Serialize(snapshot);
  await Matrix(AssignedK("ptrace(qsubsystems("+rho+",[k,not],[2,2]),k)"),mixture);
  Call("OpenSession",session);Require(serializer.Serialize(Call("CaptureSession"))==saved,"Assigned-k mapping/history changed on reopen");
  string reopened=((TextBox)Field("input")).Text;
  await Calculate(reopened);Require(await Copy()==declaration,"Reopened assigned-k mapping changed");
  Capture(Path.Combine(evidence,"numeric-k-mapping-reopened.png"));
  await Matrix("ptrace("+reopened+",k)",half);
  await Matrix("ptrace("+reopened+",not)",mixture);
  await Calculate(AssignedK("ptrace("+mapping+",0)"),"not numeric indices");
  Capture(Path.Combine(evidence,"numeric-k-mapped-index-rejected.png"));
  File.WriteAllText(Path.Combine(evidence,"numeric-k-result.txt"),"PASS: "+(checks-initial)+" assigned numeric-k GUI checks; clipboard retries="+clipboardRetries);
 }
 [STAThread] static int Main(string[] args) {
  string output=Path.GetFullPath(args[1]);Directory.CreateDirectory(output);evidence=output;
  assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));app=assembly.GetType("QuantumStudio");app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(Path.GetFullPath(args[0])));int code=1;
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   try {
    ((ComboBox)Field("mode")).SelectedIndex=0;((ComboBox)Field("evaluation")).SelectedIndex=0;
    const string rho="[1/2,0,0,0;0,0,0,0;0,0,1/4,1/4;0,0,1/4,1/4]";
    const string mixture="matrix(2,2,[3/4,1/4,1/4,1/4])",half="matrix(2,2,[1/2,0,0,1/2])";
    foreach(string keyword in new[]{"not","and","or","xor"}) {
     string value="subsystems("+rho+",["+keyword+",A],[2,2])";
     await Calculate(value); string declaration=await Copy();
     await Calculate(declaration); Require(await Copy()==declaration,"Keyword declaration re-entry changed mapping");
     string session=Path.Combine(output,keyword+".qsession"); object snapshot=Call("CaptureSession");
     assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
     var serializer=new JavaScriptSerializer(); string saved=serializer.Serialize(snapshot);
     await Matrix("ptrace(subsystems("+rho+",[A,"+keyword+"],[2,2]),"+keyword+")",half);
     Call("OpenSession",session); Require(serializer.Serialize(Call("CaptureSession"))==saved,"Keyword session mapping changed");
     await Calculate(((TextBox)Field("input")).Text); Require(await Copy()==declaration,"Reopened keyword mapping changed");
     foreach(string token in new[]{keyword,"\""+keyword+"\"","'"+keyword+"'"}) {
      foreach(string selector in new[]{token,"["+token+"]","vector("+token+")"})
       await Matrix("ptrace("+declaration+","+selector+")",mixture);
     }
     await Matrix(@"\operatorname{Tr}_{\mathsf{"+keyword+"}}("+declaration+")",mixture);
     Capture(Path.Combine(output,keyword+"-trace.png"));
    }
    await Matrix("ptrace(subsystems(density(|101>),[not,and,xor],[2,2,2]),[xor,not])","matrix(2,2,[1,0,0,0])");
    await NumericK(rho,mixture,half);
    File.WriteAllText(Path.Combine(output,"result.txt"),"PASS: "+checks+" DEV-17 supplemental keyword GUI checks; clipboard retries="+clipboardRetries);code=0;
   }catch(Exception ex){File.WriteAllText(Path.Combine(output,"result.txt"),ex.ToString());try{Capture(Path.Combine(output,"failure.png"));}catch(Exception captureError){File.WriteAllText(Path.Combine(output,"capture-error.txt"),captureError.ToString());}}
   finally{Application.Current.Shutdown();}
  }),DispatcherPriority.ApplicationIdle);
  app.GetMethod("Main",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{new string[0]});return code;
 }
}
