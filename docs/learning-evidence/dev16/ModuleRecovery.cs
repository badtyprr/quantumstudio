using System;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Controls;

class ModuleRecovery {
    static readonly BindingFlags members=BindingFlags.Instance|BindingFlags.Public|BindingFlags.NonPublic;
    static Assembly app;
    static object Get(object obj,string name) {
        var t=obj.GetType(); var f=t.GetField(name,members);
        return f!=null ? f.GetValue(obj) : t.GetProperty(name,members).GetValue(obj,null);
    }
    static object Call(object obj,string name,params object[] args) {
        var m=obj.GetType().GetMethods(members).Single(x=>x.Name==name && x.GetParameters().Length==args.Length);
        return m.Invoke(obj,args);
    }
    static void Require(bool result,string msg) {if(!result)throw new Exception(msg);}
    static async Task Test(Window owner,string entry,string dependency,bool classical,string output) {
        byte[] original=File.ReadAllBytes(dependency);
        var editor=(Window)Activator.CreateInstance(app.GetType(classical?"ClassicalProgramWindow":"CircuitComposer",true),
            classical ? new object[]{owner} : new object[]{owner,(Action<string>)(s=>{})});
        Window dialog=null;
        try {
            if(classical)editor.GetType().GetField("verifying",members).SetValue(editor,true);
            editor.Show();
            var compile=app.GetType("QasmImport",true).GetMethod("CompileSource",BindingFlags.Static|BindingFlags.Public);
            string envelope=(string)compile.Invoke(null,new object[]{entry,false,classical,true,null});
            object model=classical ? Get(editor,"history") : editor;
            Action<string> import=s=>Call(model,"ImportSource",s,false);
            import(envelope);
            Func<string> snapshot=()=>(string)Call(model,classical?"Serialize":"Snapshot");
            string before=snapshot();
            dialog=(Window)Activator.CreateInstance(app.GetType("SourceFilesWindow",true),new object[]{editor,Get(model,classical?"Source":"sourceDocument"),import});
            dialog.Show();
            ((TextBox)Get(dialog,"root")).Text=Path.GetDirectoryName(entry);
            Func<bool,Task> run=value=>(Task)Call(dialog,"Run",value);
            Func<string> message=()=>((TextBlock)Get(dialog,"result")).Text;
            await run(false);
            Require(message().StartsWith("All source files match") && snapshot()==before,"unchanged: "+message());
            File.Delete(dependency);
            await run(false);
            Require(message().Contains("missing") && snapshot()==before,"missing: "+message());
            await run(true);
            Require(message().StartsWith("Could not reimport") && snapshot()==before,"missing reimport: "+message());
            File.WriteAllText(dependency,"invalid module syntax!");await run(true);
            Require(message().StartsWith("Could not reimport") && snapshot()==before,"malformed reimport: "+message());
            string text=System.Text.Encoding.UTF8.GetString(original);
            string updated=text.Replace("s = 7;","s = 1;").Replace("s = 6;","s = 3;");
            Require(text!=updated,"fixture must change");
            File.WriteAllText(dependency,updated,new System.Text.UTF8Encoding(false));
            await run(false);
            Require(message().Contains("changed") && snapshot()==before,"changed: "+message());
            await run(true);
            Require((bool)Get(dialog,"Imported") && snapshot()!=before,"repaired reimport: "+message());
            File.WriteAllText(output+".reimported.json",snapshot());
            Call(model,"Undo");
            Require(snapshot()==before,"undo after real reimport");
            File.WriteAllText(output+".restored.json",before);
        } finally {
            File.WriteAllBytes(dependency,original);
            if(dialog!=null)dialog.Close();
            editor.Close();
        }
    }
    [STAThread] static int Main(string[] args) {
        app=Assembly.LoadFrom(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"QuantumStudio.exe"));
        var host=new Application();
        var owner=new Window{Width=340,Height=200,ShowInTaskbar=false};
        int code=1;
        owner.Loaded+=async delegate {
            try {await Test(owner,args[0],args[1],args[2]=="classical",args[3]);code=0;}
            catch(Exception ex){File.WriteAllText(args[3]+".error.txt",ex.ToString());}
            finally {host.Shutdown();}
        };
        host.Run(owner);return code;
    }
}
