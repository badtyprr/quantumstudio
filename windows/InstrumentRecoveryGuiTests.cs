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
class InstrumentRecoveryGuiTests {
 static Type app;static Assembly assembly;static int checks;
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
 [STAThread] static int Main(string[] args) {
  string output=Path.GetFullPath(args[1]);Directory.CreateDirectory(output);
  assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));app=assembly.GetType("QuantumStudio");app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(Path.GetFullPath(args[0])));int code=1;
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   try {
    var mode=(ComboBox)Field("mode");mode.SelectedIndex=0;((ComboBox)Field("evaluation")).SelectedIndex=0;
    var serializer=new JavaScriptSerializer();serializer.MaxJsonLength=20000000;
    var rows=serializer.Deserialize<System.Collections.Generic.List<System.Collections.Generic.Dictionary<string,object>>>(File.ReadAllText(args[2]));
    Window window=(Window)Field("window");
    var selected=new System.Collections.Generic.HashSet<string>(new string[]{"zz-conditional-1","zz-conditional--1","coherent-controlled-recovery","damping-unconditional-channel"});
    var observed=new System.Collections.Generic.List<object>();
    foreach(var row in rows) {
     string name=(string)row["name"];if(!selected.Contains(name))continue;
     Require((bool)row["passed"],"Fixture is not independently validated: "+name);
     var expected=serializer.Deserialize<System.Collections.Generic.Dictionary<string,object>>((string)row["stdout"]);
     await Calculate((string)row["expression"]);
     ((Button)window.FindName("Copy")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
     string copied=Clipboard.GetText();Require(copied==(string)expected["copy_text"],"Full copied result differs from independent matrix witness: "+name);
     observed.Add(new {name=name,expression=row["expression"],copy_text=copied});
     Capture(Path.Combine(output,name+".png"));
     await Calculate(copied);Require((string)Field("copyText")==copied,"Copy re-entry changed full result: "+name);
    }
    Require(observed.Count==selected.Count,"Missing GUI fixtures");
    string session=Path.Combine(output,"instrument-recovery.qsession");object snapshot=Call("CaptureSession");
    assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
    string expectedSession=serializer.Serialize(snapshot);
    ((TextBox)Field("input")).Text="1";Call("OpenSession",session);Require(serializer.Serialize(Call("CaptureSession"))==expectedSession,"Session round-trip changed instrument history");
    await Calculate("poststate(instrument(vector(0),vector(vector([1,0;0,0]))),|0>,0)",true);
    await Calculate("1");Require(((TextBox)Field("output")).Text=="1","GUI did not recover after rejected instrument");
    window.Width=window.MinWidth;window.Height=window.MinHeight;Capture(Path.Combine(output,"minimum.png"));
    File.WriteAllText(Path.Combine(output,"observed.json"),serializer.Serialize(observed));
    File.WriteAllText(Path.Combine(output,"result.txt"),"PASS: "+checks+" instrument recovery GUI checks");code=0;
   }catch(Exception ex) {File.WriteAllText(Path.Combine(output,"result.txt"),ex.ToString());Console.Error.WriteLine(ex);}
   finally {Application.Current.Shutdown();}
  }),DispatcherPriority.ApplicationIdle);
  Call("Main",new object[]{new string[0]});return code;
 }
}
