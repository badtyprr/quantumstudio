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
class RegisterWidthGuiTests {
 public class Fixture { public string name,expression,descriptor,comparison,reference,dimension;public string[][] substitutions;public string[] display_contains,copy_contains,copy_excludes; }
 public class Negative {public string expression,diagnostic;}
 public class Plan { public Fixture[] fixtures;public Negative[] negative_cases; }

 static Type app;static Assembly assembly;static int checks,clipboardRetries;
 static BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
 static object Field(string name) {return app.GetField(name,flags).GetValue(null);}
 static object Call(string name,params object[] args) {return app.GetMethod(name,flags).Invoke(null,args);}
 static void Require(bool condition,string message) {if(!condition)throw new Exception(message);checks++;}
 static async Task Calculate(string expression,string diagnostic=null) {
  ((TextBox)Field("input")).Text=expression;var run=(Button)Field("run");run.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
  DateTime deadline=DateTime.UtcNow.AddSeconds(20);
  while(!run.IsEnabled && DateTime.UtcNow<deadline)await Task.Delay(20);
  Require(run.IsEnabled,"Calculation did not finish");
  string label=((TextBlock)Field("resultLabel")).Text;
  Require(diagnostic!=null ? label=="CHECK YOUR EXPRESSION" : label=="EXACT RESULT",expression+" => "+label+": "+((TextBox)Field("output")).Text);
  if(diagnostic!=null)Require(((TextBox)Field("output")).Text.Contains(diagnostic),"Wrong error diagnostic");
 }
 static void Capture(string path) {
  Window window=(Window)Field("window");window.UpdateLayout();
  var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(window);
  var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using(var file=File.Create(path))encoder.Save(file);
 }
 static async Task<string> Copy() {
  for(int attempt=0;attempt<10;attempt++) {
   try {
    string sentinel="register-width-test-"+Guid.NewGuid().ToString("N");Clipboard.SetText(sentinel);
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
  if(args.Length!=2 || Environment.GetEnvironmentVariable("GITHUB_ACTIONS")!="true" || Environment.GetEnvironmentVariable("RUNNER_ENVIRONMENT")!="github-hosted")return 2;
  string output=Path.GetFullPath(args[1]);if(!Directory.Exists(output))return 2;
  var serializer=new JavaScriptSerializer();var records=new System.Collections.Generic.List<object>();
  DataObject previousClipboard=null;bool clipboardCaptured=false,clipboardRestored=false;int code=1;
  assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));app=assembly.GetType("QuantumStudio");
  app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(Path.GetFullPath(args[0])));
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   try {
    previousClipboard=PreserveClipboard();clipboardCaptured=true;
    ((ComboBox)Field("evaluation")).SelectedIndex=0;
    ((ComboBox)Field("timeAllowance")).SelectedIndex=0;
    var plan=serializer.Deserialize<Plan>(File.ReadAllText(Path.Combine(output,"fixtures.json")));
    Require(plan.fixtures.Length==9,"Unexpected fixture count");
    Func<string,int,Task<string>> evaluate=async delegate(string expression,int selectedMode) {
     ((ComboBox)Field("mode")).SelectedIndex=selectedMode;
     var record=new System.Collections.Generic.Dictionary<string,object>();
     record["expression"]=expression;record["mode"]=selectedMode;record["state"]="started";records.Add(record);
     File.WriteAllText(Path.Combine(output,"records.json"),serializer.Serialize(records));
     try {
      await Calculate(expression);string copied=await Copy();record["copy"]=copied;record["state"]="calculated";
      return copied;
     }catch(Exception ex){record["state"]="failed";record["error"]=ex.ToString();throw;}
     finally {
      record["display"]=((TextBox)Field("output")).Text;record["label"]=((TextBlock)Field("resultLabel")).Text;record["status"]=((TextBlock)Field("status")).Text;
      File.WriteAllText(Path.Combine(output,"records.json"),serializer.Serialize(records));
     }
    };
    Action<Fixture,string> checkDeferred=delegate(Fixture fixture,string copied) {
     string shown=((TextBox)Field("output")).Text;
     if(fixture.descriptor!=null) {
      Require(copied.Contains(fixture.descriptor),"Deferred descriptor missing: "+fixture.name);
      Require(((FrameworkElement)Field("matrixView")).Visibility==Visibility.Collapsed && ((FrameworkElement)Field("output")).Visibility==Visibility.Visible,"Deferred value materialized a matrix");
      foreach(string internalName in new[]{"qbits","qbasis","qtensorseries","qregistersum","qequalchain","qcomputationalket","qadjacent","qscalarproductsum"})Require(!shown.Contains(internalName),"Internal name in display: "+internalName);
     }
     if(fixture.display_contains!=null)foreach(string token in fixture.display_contains)Require(shown.Contains(token),"Expected display content missing: "+token);
     if(fixture.copy_contains!=null)foreach(string token in fixture.copy_contains)Require(copied.Contains(token),"Expected Copy structure missing: "+token);
     if(fixture.copy_excludes!=null)foreach(string token in fixture.copy_excludes)Require(!copied.Contains(token),"Unexpected Copy structure: "+token);
    };
    foreach(var fixture in plan.fixtures) {
     int fixtureStart=records.Count;
     Require(System.Text.RegularExpressions.Regex.IsMatch(fixture.name,@"^[a-z0-9-]+$"),"Invalid fixture name");
     string first=await evaluate(fixture.expression,0);
     checkDeferred(fixture,first);string firstDisplay=((TextBox)Field("output")).Text;
     Capture(Path.Combine(output,fixture.name+"-initial.png"));
     string ordinary=await evaluate(first,1);checkDeferred(fixture,ordinary);
     Require(((TextBox)Field("output")).Text==firstDisplay,"Display changed on first Copy");
     string stable=await evaluate(ordinary,1);checkDeferred(fixture,stable);
     Require(((TextBox)Field("output")).Text==firstDisplay,"Display changed on stable Copy");
     Require(stable==ordinary,"Ordinary Copy unstable: "+fixture.name);
     object snapshot=Call("CaptureSession");string saved=serializer.Serialize(snapshot);
     string session=Path.Combine(output,fixture.name+".qsession");
     assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
     File.WriteAllText(Path.Combine(output,fixture.name+"-saved.json"),saved);
     Require(await evaluate("1",1)=="1","Intervening calculation failed");
     Call("OpenSession",session);string restored=serializer.Serialize(Call("CaptureSession"));
     File.WriteAllText(Path.Combine(output,fixture.name+"-restored.json"),restored);
     Require(saved==restored,"Session changed expression, mode or history: "+fixture.name);
     Require(((TextBox)Field("input")).Text==ordinary && ((ComboBox)Field("mode")).SelectedIndex==1,"Session restored wrong input/mode");
     string reopened=await evaluate(((TextBox)Field("input")).Text,1);
     Require(reopened==stable,"Restored calculation changed");checkDeferred(fixture,reopened);
     Require(((TextBox)Field("output")).Text==firstDisplay,"Restored display changed");
     Capture(Path.Combine(output,fixture.name+"-restored.png"));
     string bound=reopened;
     if(fixture.substitutions!=null)foreach(var pair in fixture.substitutions) {
      Require(pair.Length==2,"Malformed substitution");bound="qreplace(("+bound+"),"+pair[0]+","+pair[1]+")";
     }
     string comparison,expected;
     if(fixture.comparison=="deferred-width") {
      Require(reopened.Contains(fixture.dimension),"Deferred dimension lost");
      for(int j=fixtureStart;j<records.Count;j++)((System.Collections.Generic.Dictionary<string,object>)records[j])["state"]="passed";
      File.WriteAllText(Path.Combine(output,"records.json"),serializer.Serialize(records));continue;
     }
     if(fixture.comparison=="exact-scalar") {comparison=bound;expected=fixture.reference;}
     else if(fixture.comparison=="bitvalue") {comparison="qbitvalue("+bound+")";expected=fixture.reference;}
     else if(fixture.comparison=="vector-equality") {comparison="(("+bound+")==("+fixture.reference+"))";expected="1";}
     else {
      string delta="qsub(("+bound+"),("+fixture.reference+"))";
      Require(fixture.comparison=="ket-norm" || fixture.comparison=="frobenius","Unknown reference comparison");
      comparison=fixture.comparison=="ket-norm" ? "qnorm("+delta+")" : "qtrace(qmul(qdag("+delta+"),"+delta+"))";expected="0";
     }
     Require(await evaluate(comparison,1)==expected,"Finite reference mismatch: "+fixture.name);
     Require(((TextBox)Field("output")).Text==expected && ((FrameworkElement)Field("output")).Visibility==Visibility.Visible,"Displayed finite result differs from exact reference");
     Capture(Path.Combine(output,fixture.name+"-reference.png"));
     for(int j=fixtureStart;j<records.Count;j++)((System.Collections.Generic.Dictionary<string,object>)records[j])["state"]="passed";
     File.WriteAllText(Path.Combine(output,"records.json"),serializer.Serialize(records));
    }
    Require(records.Count==53,"Unexpected successful calculation count");
    Require(plan.negative_cases.Length==2,"Unexpected negative fixture count");
    foreach(var negative in plan.negative_cases) {
     var record=new System.Collections.Generic.Dictionary<string,object>();record["expression"]=negative.expression;record["mode"]=0;record["state"]="started";record["expected_diagnostic"]=negative.diagnostic;records.Add(record);
     File.WriteAllText(Path.Combine(output,"records.json"),serializer.Serialize(records));
     try {
      ((ComboBox)Field("mode")).SelectedIndex=0;await Calculate(negative.expression,negative.diagnostic);
      Require(Field("copyText")==null,"Failed calculation retained stale Copy text");record["state"]="passed";
     }catch(Exception ex){record["state"]="failed";record["error"]=ex.ToString();throw;}
     finally {
      record["display"]=((TextBox)Field("output")).Text;record["label"]=((TextBlock)Field("resultLabel")).Text;record["status"]=((TextBlock)Field("status")).Text;record["copy"]=Field("copyText");
      File.WriteAllText(Path.Combine(output,"records.json"),serializer.Serialize(records));
     }
    }
    Require(records.Count==55,"Unexpected total calculation count");
    File.WriteAllText(Path.Combine(output,"final-session.json"),serializer.Serialize(Call("CaptureSession")));
    code=0;
   }catch(Exception ex){File.WriteAllText(Path.Combine(output,"failure.txt"),ex.ToString());}
   finally{
    if(clipboardCaptured)try {if(previousClipboard.GetFormats(false).Length==0)Clipboard.Clear();else Clipboard.SetDataObject(previousClipboard,true);clipboardRestored=true;}catch(Exception ex){code=1;File.WriteAllText(Path.Combine(output,"clipboard-restore-failure.txt"),ex.ToString());}
    File.WriteAllText(Path.Combine(output,"result.json"),serializer.Serialize(new {passed=code==0,checks=checks,calls=records.Count,clipboardRetries=clipboardRetries,clipboardRestored=clipboardRestored}));
    Application.Current.Shutdown();
   }
  }),DispatcherPriority.ApplicationIdle);
  app.GetMethod("Main",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{new string[0]});return code;
 }
}
