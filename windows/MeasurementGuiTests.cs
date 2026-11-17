// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using System.Web.Script.Serialization;
class MeasurementGuiTests {
 static Type app;static Assembly assembly;static int checks,clipboardRetries;
 static BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
 static object Field(string name) {return app.GetField(name,flags).GetValue(null);}
 static object Call(string name,params object[] args) {return app.GetMethod(name,flags).Invoke(null,args);}
 static void Require(bool condition,string message) {if(!condition)throw new Exception(message);checks++;}
 static async Task Calculate(string expression,bool error=false) {
  ((TextBox)Field("input")).Text=expression;var run=(Button)Field("run");run.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
  DateTime deadline=DateTime.UtcNow.AddSeconds(60);
  while(!run.IsEnabled && DateTime.UtcNow<deadline)await Task.Delay(20);
  Require(run.IsEnabled,"Calculate did not finish");
  string label=((TextBlock)Field("resultLabel")).Text;
  Require(error ? label=="CHECK YOUR EXPRESSION" : label.EndsWith("RESULT"),expression+" => "+label+": "+((TextBox)Field("output")).Text);
 }
 static void Capture(string path) {
  Window window=(Window)Field("window");window.UpdateLayout();
  var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(window);
  var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using(var file=File.Create(path))encoder.Save(file);
 }
 static async Task<string> CopyWithRetry(Action copy,Func<string> read,string expected) {
  for(int attempt=0;attempt<10;attempt++) {
   copy();
   try {
    string text=read();if(text==expected)return text;
   }catch(System.Runtime.InteropServices.COMException ex) {
    if(ex.ErrorCode!=unchecked((int)0x800401D0))throw;
   }
   clipboardRetries++;await Task.Delay(50);
  }
  throw new Exception("Clipboard did not expose the current copied result after ten attempts");
 }
 static async Task CheckClipboardRetry() {
  int copies=0,reads=0;clipboardRetries=0;
  string value=await CopyWithRetry(()=>copies++,()=>{
   reads++;if(reads==1)throw new System.Runtime.InteropServices.COMException("busy",unchecked((int)0x800401D0));
   return reads==2 ? "stale" : "current";
  },"current");
  Require(value=="current" && copies==3 && reads==3 && clipboardRetries==2,"Transient clipboard recovery changed attempts or text");
  foreach(bool busy in new[]{false,true}) {
   copies=0;bool rejected=false;
   try {await CopyWithRetry(()=>copies++,()=>{if(busy)throw new System.Runtime.InteropServices.COMException("busy",unchecked((int)0x800401D0));return "stale";},"current");}
   catch(Exception ex) {rejected=ex.Message=="Clipboard did not expose the current copied result after ten attempts";}
   Require(rejected && copies==10,"Persistent clipboard failure was hidden or unbounded");
  }
  copies=0;bool propagated=false;
  try {await CopyWithRetry(()=>copies++,()=>{throw new System.Runtime.InteropServices.COMException("other",unchecked((int)0x80004005));},"current");}
  catch(System.Runtime.InteropServices.COMException ex) {propagated=ex.ErrorCode==unchecked((int)0x80004005);}
  Require(propagated && copies==1,"Unrelated clipboard error was retried");
 }
 [STAThread] static int Main(string[] args) {
  if(args.Length==1 && args[0]=="--clipboard-retry-test") {
   try {CheckClipboardRetry().GetAwaiter().GetResult();Console.WriteLine("PASS: "+checks+" clipboard retry contract checks");return 0;}
   catch(Exception ex){Console.Error.WriteLine(ex);return 1;}
  }
  string output=Path.GetFullPath(args[1]);Directory.CreateDirectory(output);
  assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));app=assembly.GetType("QuantumStudio");app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(Path.GetFullPath(args[0])));int code=1;
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   try {
    var mode=(ComboBox)Field("mode");mode.SelectedIndex=0;((ComboBox)Field("evaluation")).SelectedIndex=0;
    string povm="povm(vector(\"red\",\"blue\"),vector([2,1;1,1]/3,[1,-1;-1,2]/3))";
    await Calculate("probabilities("+povm+",|+>)==vector(5/6,1/6)");Require(((TextBox)Field("output")).Text=="1","Wrong lesson probabilities");
    await Calculate(povm);Window window=(Window)Field("window");
    string copied=await CopyWithRetry(()=>((Button)window.FindName("Copy")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent)),()=>Clipboard.GetText(),(string)Field("copyText"));
    Require(copied.Contains("qpovm") && copied.Contains("red") && copied.Contains("blue"),"Copy lost labeled POVM");
    await Calculate("probabilities("+copied+",|+>)==vector(5/6,1/6)");Require(((TextBox)Field("output")).Text=="1","Copied POVM changed probabilities");
    string symbolic="measurementvalid(povm(vector(0,1),vector([x,0;0,1],[1-x,0;0,0])))";
    await Calculate(symbolic);Require(((string)Field("copyText")).Contains("qmeasurementvalid"),"Unknown validity was discarded");
    Capture(Path.Combine(output,"symbolic.png"));
    string session=Path.Combine(output,"measurement.qsession");object snapshot=Call("CaptureSession");
    assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
    var serializer=new JavaScriptSerializer();string expected=serializer.Serialize(snapshot);
    ((TextBox)Field("input")).Text="1";Call("OpenSession",session);Require(serializer.Serialize(Call("CaptureSession"))==expected,"Save/open changed measurement history or expression");
    await Calculate("replace("+symbolic+",x,2)",true);Capture(Path.Combine(output,"invalid.png"));
    await Calculate("poststate(instrument(vector(0,1),vector(vector([1,0;0,0]),vector([0,0;0,1]))),|+>,1)");
    Require(((Grid)Field("matrixCells")).Children.Count==4,"Poststate matrix not displayed");Capture(Path.Combine(output,"poststate.png"));
    await Calculate("naimark("+povm+",2)");Require(((Grid)Field("matrixCells")).Children.Count==16,"Naimark unitary matrix not displayed");Capture(Path.Combine(output,"naimark.png"));
    window.Width=window.MinWidth;window.Height=window.MinHeight;Capture(Path.Combine(output,"minimum.png"));
    File.WriteAllText(Path.Combine(output,"result.txt"),"PASS: "+checks+" measurement GUI checks; clipboard retries: "+clipboardRetries);code=0;
   }catch(Exception ex) {File.WriteAllText(Path.Combine(output,"result.txt"),ex.ToString());Console.Error.WriteLine(ex);}
   finally {Application.Current.Shutdown();}
  }),DispatcherPriority.ApplicationIdle);
  Call("Main",new object[]{new string[0]});return code;
 }
}
