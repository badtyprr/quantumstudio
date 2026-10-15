// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;
using System.Web.Script.Serialization;

public class SessionEntry {
 public string Expression {get;set;}
 public string Result {get;set;}
 public int Mode {get;set;}
 public int Evaluation {get;set;}
}
public class CalculationSession {
 public int Version {get;set;}
 public string Expression {get;set;}
 public int Mode {get;set;}
 public int Evaluation {get;set;}
 public SessionEntry[] History {get;set;}
}
static class SessionStore {
 const int MaximumBytes=8*1024*1024;
 static JavaScriptSerializer Serializer() {return new JavaScriptSerializer {MaxJsonLength=MaximumBytes,RecursionLimit=16};}
 static void ValidateExpression(string expression,int mode,int evaluation) {
  if(expression==null || Encoding.UTF8.GetByteCount(expression)>32000 || mode<0 || mode>1 || evaluation<0 || evaluation>1)
   throw new InvalidDataException("Session expressions must be at most 32 KB and use valid notation and evaluation modes.");
 }
 public static void Validate(CalculationSession session) {
  if(session==null || session.Version!=1 || session.History==null || session.History.Length>50)
   throw new InvalidDataException("Expected a version 1 calculation session with at most 50 history entries.");
  ValidateExpression(session.Expression,session.Mode,session.Evaluation);
  foreach(var entry in session.History) {
   if(entry==null || entry.Result==null || entry.Result.Length>32768)throw new InvalidDataException("Invalid saved history result.");
   ValidateExpression(entry.Expression,entry.Mode,entry.Evaluation);
   if(String.IsNullOrWhiteSpace(entry.Expression))throw new InvalidDataException("History expressions cannot be empty.");
  }
 }
 public static CalculationSession Load(string path) {
  if(new FileInfo(path).Length>MaximumBytes)throw new InvalidDataException("Session files must be at most 8 MB.");
  string text=File.ReadAllText(path,new UTF8Encoding(false,true));
  if(Encoding.UTF8.GetByteCount(text)>MaximumBytes)throw new InvalidDataException("Session files must be at most 8 MB.");
  var session=Serializer().Deserialize<CalculationSession>(text);Validate(session);return session;
 }
 public static void Save(string path,CalculationSession session) {
  Validate(session);string text=Serializer().Serialize(session);
  if(Encoding.UTF8.GetByteCount(text)>MaximumBytes)throw new InvalidDataException("Session files must be at most 8 MB.");
  string temporary=path+"."+Guid.NewGuid().ToString("N")+".tmp";
  try {
   File.WriteAllText(temporary,text,new UTF8Encoding(false));
   for(int attempt=0;;attempt++) {
    try {if(File.Exists(path))File.Replace(temporary,path,null);else File.Move(temporary,path);break;}
    catch(IOException ex) {
     int code=ex.HResult & 0xffff;
     if((code!=32 && code!=33 && code!=1175) || attempt>=5)throw;
     System.Threading.Thread.Sleep(200);
    }
   }
  } finally {if(File.Exists(temporary))File.Delete(temporary);}
 }
}
