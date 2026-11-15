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
class HadamardTensorGuiTests {
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
    string sentinel="hadamard-tensor-test-"+Guid.NewGuid().ToString("N");Clipboard.SetText(sentinel);
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
  if(args.Length!=2)return 2;
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
    string fragment=File.ReadAllText(Path.Combine(output,"fragment.txt"));
    var expected=serializer.Deserialize<System.Collections.Generic.Dictionary<string,string>>(File.ReadAllText(Path.Combine(output,"expected.json")));
    Func<string,int,Task<string>> evaluate=async delegate(string expression,int selectedMode) {
     ((ComboBox)Field("mode")).SelectedIndex=selectedMode;
     var record=new System.Collections.Generic.Dictionary<string,object>();
     record["expression"]=expression;record["mode"]=selectedMode;record["state"]="started";records.Add(record);
     File.WriteAllText(Path.Combine(output,"records.json"),serializer.Serialize(records));
     try {
      await Calculate(expression);string copied=await Copy();record["copy"]=copied;record["state"]="passed";
      if(copied=="1")Require(((TextBox)Field("output")).Text==copied,"Displayed scalar differs from copied exact result");
      if(copied==expected["two_qubit_copy"])Require(((TextBox)Field("output")).Text==expected["two_qubit_display"],"Displayed two-qubit vector changed");
      if(copied==expected["one_qubit_copy"])Require(((TextBox)Field("output")).Text==expected["one_qubit_display"],"Displayed one-qubit vector changed");
      return copied;
     }catch(Exception ex){record["state"]="failed";record["error"]=ex.ToString();throw;}
     finally {
      record["display"]=((TextBox)Field("output")).Text;record["label"]=((TextBlock)Field("resultLabel")).Text;record["status"]=((TextBlock)Field("status")).Text;
      File.WriteAllText(Path.Combine(output,"records.json"),serializer.Serialize(records));
     }
    };
    string first=await evaluate(fragment,0);Require(first==expected["symbolic_first"],"Original tensor family changed");Capture(Path.Combine(output,"original.png"));
    string ordinary=await evaluate(first,1);Require(ordinary==expected["symbolic_stable"],"Ordinary Copy normalization changed");
    string stable=await evaluate(ordinary,1);Require(stable==ordinary,"Normalized ordinary Copy was not stable");Capture(Path.Combine(output,"ordinary-copy.png"));
    object snapshot=Call("CaptureSession");string saved=serializer.Serialize(snapshot);
    string session=Path.Combine(output,"hadamard-tensor.qsession");
    assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
    File.WriteAllText(Path.Combine(output,"saved-session.json"),saved);
    Require(await evaluate("1",1)=="1","Intervening expression failed");
    Call("OpenSession",session);string restored=serializer.Serialize(Call("CaptureSession"));
    File.WriteAllText(Path.Combine(output,"restored-session.json"),restored);Require(restored==saved,"Session restore changed input, modes or history");
    string reopened=((TextBox)Field("input")).Text;Require(reopened==stable,"Session restored wrong actual copy");
    Require(((ComboBox)Field("mode")).SelectedIndex==1,"Session lost ordinary mode");
    string afterOpen=await evaluate(reopened,1);Require(afterOpen==stable,"Reopened tensor family changed");Capture(Path.Combine(output,"reopened.png"));
    string bound=await evaluate("replace(replace(replace("+afterOpen+",n,2),x_0,1),x_1,0)",0);
    Require(bound==expected["two_qubit_copy"],"Two-qubit signs, coefficients or ordering changed");Capture(Path.Combine(output,"bound-two.png"));
    Require(await evaluate(bound,1)==bound,"Two-qubit numeric Copy re-entry changed");Capture(Path.Combine(output,"numeric-copy.png"));
    string singleton=await evaluate("replace(replace("+afterOpen+",n,1),x_0,1)",0);
    Require(singleton==expected["one_qubit_copy"],"One-qubit family did not collapse to one factor");
    Require(await evaluate(singleton,1)==singleton,"One-qubit numeric Copy re-entry changed");Capture(Path.Combine(output,"one-qubit.png"));
    Require(records.Count==9,"Unexpected calculation count");
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
