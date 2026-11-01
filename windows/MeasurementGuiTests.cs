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
    string povm="povm(vector(\"red\",\"blue\"),vector([2,1;1,1]/3,[1,-1;-1,2]/3))";
    await Calculate("probabilities("+povm+",|+>)==vector(5/6,1/6)");Require(((TextBox)Field("output")).Text=="1","Wrong lesson probabilities");
    await Calculate(povm);Window window=(Window)Field("window");((Button)window.FindName("Copy")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
    string copied=Clipboard.GetText();Require(copied.Contains("qpovm") && copied.Contains("red") && copied.Contains("blue"),"Copy lost labeled POVM");
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
    File.WriteAllText(Path.Combine(output,"result.txt"),"PASS: "+checks+" measurement GUI checks");code=0;
   }catch(Exception ex) {File.WriteAllText(Path.Combine(output,"result.txt"),ex.ToString());Console.Error.WriteLine(ex);}
   finally {Application.Current.Shutdown();}
  }),DispatcherPriority.ApplicationIdle);
  Call("Main",new object[]{new string[0]});return code;
 }
}
