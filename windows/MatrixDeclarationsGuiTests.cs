// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Collections;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Input;
using System.Windows.Media;
using System.Windows.Media.Imaging;
using System.Windows.Threading;
using System.Web.Script.Serialization;
class MatrixDeclarationsGuiTests {
 static BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
 static Type app;
 static object Field(string name) {return app.GetField(name,flags).GetValue(null);}
 static object Call(string name,params object[] args) {return app.GetMethod(name,flags).Invoke(null,args);}
 static void Click(Window editor,string name) {((Button)editor.FindName(name)).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));}
 static void Require(bool value,string message) {if(!value)throw new Exception(message);}
 [STAThread] static int Main(string[] args) {
  var assembly=Assembly.LoadFrom(args[0]);app=assembly.GetType("QuantumStudio");
  app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(args[0]));int code=1;
  string directory=Path.Combine(Path.GetTempPath(),"QuantumStudio-matrix-gui-"+Guid.NewGuid().ToString("N"));Directory.CreateDirectory(directory);
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   Window window=null,editor=null;
   try {
    window=(Window)Field("window");var input=(TextBox)Field("input");var mode=(ComboBox)Field("mode");
    editor=(Window)Call("MatrixEditor");editor.Show();Click(editor,"Add");
    var initialDraft=(IList)((DataGrid)editor.FindName("Definitions")).ItemsSource;
    Require((string)initialDraft[0].GetType().GetProperty("Name").GetValue(initialDraft[0],null)=="M_1","Default name is not an unambiguous indexed symbol");
    Click(editor,"Cancel");
    Require(((Array)Field("matrices")).Length==0,"Cancel published draft dimensions");
    editor=(Window)Call("MatrixEditor");editor.Show();Click(editor,"AddPair");
    var draft=(IList)((DataGrid)editor.FindName("Definitions")).ItemsSource;
    var name=draft[0].GetType().GetProperty("Name");name.SetValue(draft[0],"A\n",null);Click(editor,"Apply");
    Require(editor.IsVisible && ((Array)Field("matrices")).Length==0,"Invalid editor input was published");
    name.SetValue(draft[0],"A",null);Click(editor,"Apply");
    Require(!editor.IsVisible && ((Array)Field("matrices")).Length==2,"Apply lost declarations");
    input.Text="Tr(2*A+3*B)-2*Tr(A)-3*Tr(B)";mode.SelectedIndex=0;
    if(args.Length>2) {
     await (Task)Call("Calculate",new object[]{null});
     Require(((TextBox)Field("output")).Text=="0","Declared trace identity did not simplify");
     Require(input.Text.StartsWith("Tr("),"Calculation replaced natural input with implementation syntax");
     var declared=(Array)Field("matrices");var rows=declared.GetValue(0).GetType().GetProperty("Rows");
     rows.SetValue(declared.GetValue(0),"0",null);input.Text="1+1";mode.SelectedIndex=1;
     await (Task)Call("Calculate",new object[]{null});Require(((TextBox)Field("output")).Text=="2","Ordinary calculator used quantum assumptions");
     mode.SelectedIndex=0;await (Task)Call("Calculate",new object[]{null});
     Require(Field("copyText")==null,"Invalid dimensions retained a copyable result");
     rows.SetValue(declared.GetValue(0),"n",null);input.Text="Tr(2*A+3*B)-2*Tr(A)-3*Tr(B)";
     await (Task)Call("Calculate",new object[]{null});Require(((TextBox)Field("output")).Text=="0","Could not recover from invalid dimensions");
    }
    var serializer=new JavaScriptSerializer();string snapshot=serializer.Serialize(Call("CaptureSession"));
    string path=Path.Combine(directory,"matrices.qsession");File.WriteAllText(path,snapshot);Call("OpenSession",path);
    Require(serializer.Serialize(Call("CaptureSession"))==snapshot,"Session capture/restore changed assumptions");
    var matrices=(Array)Field("matrices");matrices.GetValue(0).GetType().GetProperty("Rows").SetValue(matrices.GetValue(0),"3",null);
    if(args.Length>2) {
     var history=(ListBox)Field("history");var item=(ListBoxItem)history.Items[0];
     item.RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,0,MouseButton.Left) {RoutedEvent=Control.MouseDoubleClickEvent});
     Require(serializer.Serialize(Call("CaptureSession"))==snapshot,"History did not restore its independent dimensions");
    }
    Call("OpenSession",path);string before=serializer.Serialize(Call("CaptureSession"));
    File.WriteAllText(path,snapshot.Replace("\"Rows\":\"n\"","\"Rows\":\"A\""));
    bool rejected=false;try {Call("OpenSession",path);}catch(TargetInvocationException){rejected=true;}
    Require(rejected && serializer.Serialize(Call("CaptureSession"))==before,"Invalid session mutated workspace");
    editor=(Window)Call("MatrixEditor");editor.Show();editor.UpdateLayout();
    var image=new RenderTargetBitmap((int)editor.ActualWidth,(int)editor.ActualHeight,96,96,PixelFormats.Pbgra32);image.Render(editor);
    var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(image));using(var stream=File.Create(args[1]))encoder.Save(stream);
    Click(editor,"Cancel");
    File.WriteAllText(path,"{\"Version\":1,\"Expression\":\"1\",\"Mode\":0,\"Evaluation\":0,\"History\":[]}");Call("OpenSession",path);
    Require(((Array)Field("matrices")).Length==0,"Legacy session retained unrelated matrix assumptions");
    Console.WriteLine("PASS: matrix editor draft isolation, validation, session preservation"+(args.Length>2 ? ", trace calculation and history restoration" : ""));code=0;
   }catch(Exception ex){Console.Error.WriteLine(ex);}
   finally {if(editor!=null && editor.IsVisible)editor.Close();if(window!=null)window.Close();else Application.Current.Shutdown();}
  }));
  assembly.EntryPoint.Invoke(null,new object[]{new string[0]});Directory.Delete(directory,true);return code;
 }
}
