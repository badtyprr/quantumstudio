const fs=require('fs'),path=require('path'),crypto=require('crypto');
const sharp=require('C:/Users/Simeon/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules/sharp');
const source='F:/src/libqalculate/cleanup-audit/coordinator-20261104/ibm025-svg-acquisition-20261105';
const out=__dirname;
const hash=b=>crypto.createHash('sha256').update(b).digest('hex');
(async()=>{
 const manifestRaw=fs.readFileSync(path.join(source,'manifest.json'));
 if(hash(manifestRaw)!=='6377ceb37b0e164ac2c89905360ca3946bcbd00e9e6ae2cec0314b98cd9e8ad7')throw Error('Manifest mismatch');
 const manifest=JSON.parse(manifestRaw),records=[];
 if(manifest.dispositions.length!==8||manifest.source_sha256!=='ec06bb65c2b394c9d5053a3dcbcf9407972a8fdca1fed4f0de8c357e91a72df7'||manifest.revision!=='a500b17f8b1f156a6bba42ab11f90f3104cad6d4')throw Error('Wrong source identity');
 for(const entry of manifest.dispositions){
  const name=path.basename(entry.repository_path),input=path.join(source,'assets',name),raw=fs.readFileSync(input);
  const svg=raw.toString('utf8');
  if(/<!DOCTYPE|<!ENTITY|<\s*(?:\w+:)?(?:script|foreignObject)\b|\bon\w+\s*=|@import/i.test(svg))throw Error('Active SVG content refused '+name);
  for(const match of svg.matchAll(/(?:href|src)\s*=\s*["']([^"']*)["']/gi))if(!match[1].startsWith('#'))throw Error('Nonlocal SVG resource refused '+name);
  for(const match of svg.matchAll(/url\(\s*["']?([^\s)"']+)/gi))if(!match[1].startsWith('#'))throw Error('Nonlocal CSS resource refused '+name);
  const blob=crypto.createHash('sha1').update(Buffer.concat([Buffer.from('blob '+raw.length+'\0'),raw])).digest('hex');
  if(hash(raw)!==entry.sha256||raw.length!==entry.bytes||blob!==entry.git_blob)throw Error('Original mismatch '+name);
  const output=path.join(out,name.replace(/\.svg$/,'.png'));
  const info=await sharp(raw,{density:180}).flatten({background:'#ffffff'}).png().toFile(output);
  if(hash(fs.readFileSync(input))!==entry.sha256)throw Error('Source changed');
  records.push({input,source_sha256:entry.sha256,git_blob:blob,original_bytes:raw.length,output,output_sha256:hash(fs.readFileSync(output)),width:info.width,height:info.height});
 }
 fs.writeFileSync(path.join(out,'render-manifest.json'),JSON.stringify({scope:'Unchanged original8SVG rasterization only; not interpretation or calculator execution',acquisition_manifest_sha256:hash(manifestRaw),source_notebook_sha256:manifest.source_sha256,revision:manifest.revision,renderer:'sharp '+sharp.versions.sharp,renderer_versions:sharp.versions,argv:process.argv,resource_policy:'Reject script/foreignObject/event handlers/DOCTYPE/ENTITY/CSSimports and all nonfragment href/src/url resources before rendering SVG buffers; no SVG scripting engine invoked',method:'180dpi white background, no SVG alterations',script_sha256:hash(fs.readFileSync(__filename)),records},null,2)+'\n');
 console.log(JSON.stringify(records.map(r=>({name:path.basename(r.output),width:r.width,height:r.height}))));
})().catch(e=>{console.error(e);process.exit(1)});
