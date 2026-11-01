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
class DomainGuiTests {
 static Type app;static Assembly assembly;static int checks;
 static BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
 static object Field(string name) {return app.GetField(name,flags).GetValue(null);}
 static object Call(string name,params object[] args) {return app.GetMethod(name,flags).Invoke(null,args);}
 static void Require(bool condition,string message) {if(!condition)throw new Exception(message);checks++;}
 static async Task Calculate(string expression,bool error=false) {
  ((TextBox)Field("input")).Text=expression;var run=(Button)Field("run");run.RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
  DateTime deadline=DateTime.UtcNow.AddSeconds(60);
  while(!run.IsEnabled && DateTime.UtcNow<deadline)await Task.Delay(20);
  Require(run.IsEnabled,"Calculation did not finish");
  string label=((TextBlock)Field("resultLabel")).Text;
  Require(error ? label=="CHECK YOUR EXPRESSION" : label.EndsWith("RESULT"),expression+" => "+label+": "+((TextBox)Field("output")).Text);
 }
 static void Capture(string path) {
  Window window=(Window)Field("window");window.UpdateLayout();
  var bitmap=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);bitmap.Render(window);
  var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(bitmap));using(var file=File.Create(path))encoder.Save(file);
 }
 static string Copy() {
  ((Button)((Window)Field("window")).FindName("Copy")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
  return Clipboard.GetText();
 }
 [STAThread] static int Main(string[] args) {
  string output=Path.GetFullPath(args[1]);Directory.CreateDirectory(output);
  assembly=Assembly.LoadFrom(Path.GetFullPath(args[0]));app=assembly.GetType("QuantumStudio");app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(Path.GetFullPath(args[0])));int code=1;
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   try {
    ((ComboBox)Field("mode")).SelectedIndex=0;((ComboBox)Field("evaluation")).SelectedIndex=0;
    await Calculate("cardinality(vector(x,y))");string equality=Copy();
    Require(equality.Contains("qsumset"),"Unknown cardinality was collapsed");Capture(Path.Combine(output,"equality.png"));
    await Calculate("replace("+equality+",y,x)");Require(((TextBox)Field("output")).Text=="1","Copied cardinality did not resolve");
    await Calculate("cartesian(vector(0,1),vector(2,3,4))");string pairs=Copy();Require(pairs.Contains("qtuple"),"Copy lost typed tuples");Capture(Path.Combine(output,"cartesian.png"));
    await Calculate("member(tuple(1,4),"+pairs+")");Require(((TextBox)Field("output")).Text=="1","Copied Cartesian product lost membership");
    await Calculate("cardinality(cartesianpower(vector(),0))");Require(((TextBox)Field("output")).Text=="1","Empty tuple was lost");
    await Calculate(@"cardinality(\{k\in\{0,1\}:k=x\})");string filter=Copy();Require(filter.Contains("qsetfilter"),"Unknown predicate was lost");Capture(Path.Combine(output,"filter.png"));
    await Calculate("replace("+filter+",x,0)");Require(((TextBox)Field("output")).Text=="1","Copied filter did not resolve");
    await Calculate("setimage(k^2,Σ,k)");string image=Copy();Require(!((TextBox)Field("output")).Text.Contains("qboundindex"),"Internal binder exposed in display");
    string session=Path.Combine(output,"domains.qsession");object snapshot=Call("CaptureSession");
    assembly.GetType("SessionStore").GetMethod("Save").Invoke(null,new object[]{session,snapshot});
    var serializer=new JavaScriptSerializer();string expected=serializer.Serialize(snapshot);
    ((TextBox)Field("input")).Text="1";Call("OpenSession",session);Require(serializer.Serialize(Call("CaptureSession"))==expected,"Save/open changed domain expression or history");
    await Calculate("cardinality(replace("+image+",Σ,vector(0,1,2)))");Require(((TextBox)Field("output")).Text=="3","Copied image did not resolve");
    await Calculate("cartesianpower(Σ,-1)",true);Capture(Path.Combine(output,"invalid.png"));
    await Calculate(@"cardinality(\{0,1\}^n)");Require(Copy().Contains("qbitstrings"),"Symbolic width condition was discarded");
    Window window=(Window)Field("window");window.Width=window.MinWidth;window.Height=window.MinHeight;Capture(Path.Combine(output,"minimum.png"));
    File.WriteAllText(Path.Combine(output,"result.txt"),"PASS: "+checks+" domain GUI checks");code=0;
   }catch(Exception ex){File.WriteAllText(Path.Combine(output,"result.txt"),ex.ToString());}
   finally{Application.Current.Shutdown();}
  }),DispatcherPriority.ApplicationIdle);
  app.GetMethod("Main",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{new string[0]});return code;
 }
}
