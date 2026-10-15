// GPL-2.0-or-later; see COPYING.
using System;
using System.IO;
using System.Text;

static class BoundedUtf8File {
 public static byte[] Read(string path,int maximum,string description) {
  using(var file=new FileStream(path,FileMode.Open,FileAccess.Read,FileShare.Read)) {
   if(file.Length>maximum)throw new InvalidDataException(description+" exceeds its file size limit.");
   using(var buffer=new MemoryStream()) {
    byte[] chunk=new byte[8192];int count;
    while((count=file.Read(chunk,0,Math.Min(chunk.Length,maximum+1-(int)buffer.Length)))>0) {
     buffer.Write(chunk,0,count);
     if(buffer.Length>maximum)throw new InvalidDataException(description+" exceeds its file size limit.");
    }
    byte[] source=buffer.ToArray();
    int offset=source.Length>=3 && source[0]==0xef && source[1]==0xbb && source[2]==0xbf ? 3 : 0;
    // Validate before consuming the document; never silently replace malformed input.
    var utf8=new UTF8Encoding(false,true);
    string text=utf8.GetString(source,offset,source.Length-offset);
    return utf8.GetBytes(text);
   }
  }
 }
}
