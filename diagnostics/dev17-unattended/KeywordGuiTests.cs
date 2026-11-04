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
  Clipboard.SetText("DEV17-sentinel-"+Guid.NewGuid().ToString("N"));
  for(int attempt=0;attempt<10;attempt++) {
   ((Button)((Window)Field("window")).FindName("Copy")).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));
   try {string copied=Clipboard.GetText();if(copied==(string)Field("copyText"))return copied;}
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
 [STAThread] static int Main(string[] args) {
  string output=Path.GetFullPath(args[1]);Directory.CreateDirectory(output);
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
    File.WriteAllText(Path.Combine(output,"result.txt"),"PASS: "+checks+" DEV-17 supplemental keyword GUI checks; clipboard retries="+clipboardRetries);code=0;
   }catch(Exception ex){File.WriteAllText(Path.Combine(output,"result.txt"),ex.ToString());}
   finally{Application.Current.Shutdown();}
  }),DispatcherPriority.ApplicationIdle);
  app.GetMethod("Main",BindingFlags.Public|BindingFlags.NonPublic|BindingFlags.Static).Invoke(null,new object[]{new string[0]});return code;
 }
}
