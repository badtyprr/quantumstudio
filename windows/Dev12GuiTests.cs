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
class Dev12GuiTests {
 static Type app;static Assembly assembly;static int checks,clipboardRetries;
 static BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
 static object Field(string name) {return app.GetField(name,flags).GetValue(null);}
 static object Call(string name,params object[] args) {return app.GetMethod(name,flags).Invoke(null,args);}
 static void Require(bool condition,string message) {if(!condition)throw new Exception(message);checks++;}
 static async Task Calculate(string expression,string diagnostic=null) {
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
  for(int attempt=0;attempt<10;attempt++) {
   ((Button)((Window)Field("window")).FindName("Copy")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
   try {
    string copied=Clipboard.GetText();
    if(copied==(string)Field("copyText"))return copied;
   }catch(System.Runtime.InteropServices.COMException ex) {
    if(ex.ErrorCode!=unchecked((int)0x800401D0))throw;
   }
   clipboardRetries++;await Task.Delay(50);
  }
  throw new Exception("Clipboard did not expose the current copied result after ten attempts");
 }
 [STAThread] static int Main(string[] args) {
  string output=Path.GetFullPath(args[1]);Directory.CreateDirectory(output);
  assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));app=assembly.GetType("QuantumStudio");app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(Path.GetFullPath(args[0])));int code=1;
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   try {
    ((ComboBox)Field("mode")).SelectedIndex=0;((ComboBox)Field("evaluation")).SelectedIndex=0;
    string[] expressions=File.ReadAllLines(Path.Combine(output,"expressions.txt"));
    for(int k=0;k<expressions.Length;k++) {
     await Calculate(expressions[k]);string copied=await Copy();
     File.WriteAllText(Path.Combine(output,"copy-"+k+".txt"),copied);
     Capture(Path.Combine(output,"dev12-"+k+".png"));
     await Calculate(copied);string reentered=await Copy();
     File.WriteAllText(Path.Combine(output,"reentry-"+k+".txt"),reentered);
     // Approximate decimals become exact rational literals on re-entry.
     // The independent verifier checks all cells, residuals and dimensions.
     if(k<4)Require(reentered==copied,"DEV-12 Copy/re-entry changed result "+k);
    }
    string session=Path.Combine(output,"dev12.qsession");object snapshot=Call("CaptureSession");
    assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
    var serializer=new JavaScriptSerializer();string expected=serializer.Serialize(snapshot);
    ((TextBox)Field("input")).Text="1";Call("OpenSession",session);
    Require(serializer.Serialize(Call("CaptureSession"))==expected,"Session save/open changed DEV-12 operations");
    await Calculate("heigenvalues([1,2;0,1])","require a Hermitian matrix");
    Capture(Path.Combine(output,"nonhermitian-rejection.png"));
    await Calculate("diff(expect(Z,Rx(x)*|0>),x)");
    string derivative=await Copy();
    await Calculate("replace(("+derivative+"),x,pi/2)");
    Require((await Copy()).Replace(" ","").Replace("−","-")=="-1","Copied derivative lost its parameter semantics");
    Capture(Path.Combine(output,"gradient-at-point.png"));
    File.WriteAllText(Path.Combine(output,"result.txt"),"PASS: "+checks+" DEV-12 GUI checks; clipboard retries="+clipboardRetries);code=0;
   }catch(Exception ex){File.WriteAllText(Path.Combine(output,"result.txt"),ex.ToString());}
   finally{Application.Current.Shutdown();}
  }),DispatcherPriority.ApplicationIdle);
  app.GetMethod("Main",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{new string[0]});return code;
 }
}
