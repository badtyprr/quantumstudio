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
class BasisDeclarationsGuiTests {
 static BindingFlags flags=BindingFlags.Static|BindingFlags.NonPublic;
 static Type app;
 static object Field(string name) {return app.GetField(name,flags).GetValue(null);}
 static object Call(string name,params object[] args) {return app.GetMethod(name,flags).Invoke(null,args);}
 static void Click(Window editor,string name) {((Button)editor.FindName(name)).RaiseEvent(new RoutedEventArgs(Button.ClickEvent));}
 static void Set(object item,string name,string value) {item.GetType().GetProperty(name).SetValue(item,value,null);}
 static string Get(object item,string name) {return (string)item.GetType().GetProperty(name).GetValue(item,null);}
 static void Require(bool value,string message) {if(!value)throw new Exception(message);}
 static void Capture(Window window,string path) {
  window.UpdateLayout();var image=new RenderTargetBitmap((int)window.ActualWidth,(int)window.ActualHeight,96,96,PixelFormats.Pbgra32);image.Render(window);
  var encoder=new PngBitmapEncoder();encoder.Frames.Add(BitmapFrame.Create(image));using(var stream=File.Create(path))encoder.Save(stream);
 }
 [STAThread] static int Main(string[] args) {
  app=Assembly.LoadFrom(args[0]).GetType("QuantumStudio");app.GetField("root",flags).SetValue(null,Path.GetDirectoryName(args[0]));int code=1;
  string path=Path.Combine(Path.GetTempPath(),"QuantumStudio-basis-gui-"+Guid.NewGuid().ToString("N")+".qsession");
  Dispatcher.CurrentDispatcher.BeginInvoke(new Action(async delegate {
   Window editor=null;
   try {
    editor=(Window)Call("BasisEditor");editor.Show();Click(editor,"Add");Click(editor,"Cancel");Require(((Array)Field("bases")).Length==0,"Cancel published a basis");
    editor=(Window)Call("BasisEditor");editor.Show();Click(editor,"Add");Click(editor,"AddFamily");
    var grid=(DataGrid)editor.FindName("Definitions");var draft=(IList)grid.ItemsSource;
    Set(draft[0],"Name","Colors");Set(draft[0],"Labels","red, red");Click(editor,"Apply");Require(editor.IsVisible && ((Array)Field("bases")).Length==0,"Duplicate labels applied");
    Set(draft[0],"Labels","red, blue");Set(draft[1],"Name","B");Set(draft[1],"Family","b");Click(editor,"Apply");Require(!editor.IsVisible && ((Array)Field("bases")).Length==2,"Valid bases not applied");
    var input=(TextBox)Field("input");input.Text="<b(j)|b(k)>";
    if(args.Length>2) {
     await (Task)Call("Calculate",new object[]{null});Require(((string)Field("copyText")).Contains("qorthodelta"),"Indexed calculation lost its domain");
     input.Text="<red|blue>";await (Task)Call("Calculate",new object[]{null});Require(((TextBox)Field("output")).Text=="0","Multiple declarations hid the finite basis");
     input.Text="sum(|b(j)><b(j)|,0,n-1,j)";await (Task)Call("Calculate",new object[]{null});Require((string)Field("copyText")=="qorthoidentity(n)","Completeness failed in the workspace");
    }
    var serializer=new JavaScriptSerializer();string snapshot=serializer.Serialize(Call("CaptureSession"));File.WriteAllText(path,snapshot);Call("OpenSession",path);
    Require(serializer.Serialize(Call("CaptureSession"))==snapshot,"Session changed basis declarations");
    Set(((Array)Field("bases")).GetValue(1),"Dimension","3");
    if(args.Length>2) {var history=(ListBox)Field("history");((ListBoxItem)history.Items[0]).RaiseEvent(new MouseButtonEventArgs(Mouse.PrimaryDevice,0,MouseButton.Left) {RoutedEvent=Control.MouseDoubleClickEvent});Require(Get(((Array)Field("bases")).GetValue(1),"Dimension")=="n","History did not restore basis dimension");}
    Call("OpenSession",path);editor=(Window)Call("BasisEditor");editor.Show();Capture(editor,args[1]);editor.Width=editor.MinWidth;editor.Height=editor.MinHeight;Capture(editor,args[1]+".minimum.png");
    grid=(DataGrid)editor.FindName("Definitions");grid.SelectedIndex=0;Click(editor,"Remove");Click(editor,"Cancel");Require(((Array)Field("bases")).Length==2,"Canceled deletion changed workspace");
    editor=(Window)Call("BasisEditor");editor.Show();grid=(DataGrid)editor.FindName("Definitions");grid.SelectedIndex=0;Click(editor,"Remove");Click(editor,"Apply");Require(((Array)Field("bases")).Length==1,"Remove did not apply");
    File.WriteAllText(path,"{\"Version\":1,\"Expression\":\"1\",\"History\":[]}");Call("OpenSession",path);Require(((Array)Field("bases")).Length==0,"Legacy session retained bases");
    Console.WriteLine("PASS: basis editor validation, draft isolation, removal, session preservation"+(args.Length>2 ? ", calculations and history restoration" : ""));code=0;
   }catch(Exception ex){Console.Error.WriteLine(ex);File.WriteAllText(args[1]+".error.txt",ex.ToString());}
   finally {if(editor!=null)editor.Close();if(File.Exists(path))File.Delete(path);Application.Current.Shutdown();}
  }),DispatcherPriority.ApplicationIdle);
  Call("Main",new object[]{new string[0]});return code;
 }
}
