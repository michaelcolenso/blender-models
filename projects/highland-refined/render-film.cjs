const {chromium}=require('playwright');
const {spawn}=require('node:child_process');const {once}=require('node:events');const fs=require('node:fs'),path=require('node:path'),http=require('node:http');
const here=__dirname,root=path.resolve(here,'../..'),out=path.join(root,'deliverables/highland-refined');
const reviewOnly=process.argv.includes('--review-only');
(async()=>{
 const server=http.createServer((req,res)=>{
  const routes={'/':path.join(here,'viewer.html'),'/sky.hdr':path.join(root,'projects/highland-cinematic/assets/kloofendal_48d_partly_cloudy_puresky_4k.hdr')};
  let file=routes[req.url]||path.join(req.url.startsWith('/output/')?out:here,req.url.replace(/^\/(output\/)?/,''));
  if(!file.startsWith(here)&&!file.startsWith(out)&&!file.endsWith('_4k.hdr')){res.writeHead(403);return res.end();}
  try{res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':file.endsWith('.json')?'application/json':'application/octet-stream');fs.createReadStream(file).on('error',()=>{res.statusCode=404;res.end();}).pipe(res);}catch{res.writeHead(404);res.end();}
 });
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const browser=await chromium.launch({executablePath:'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader']});
 const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(`http://127.0.0.1:${server.address().port}/`);await page.waitForFunction(()=>window.ready,{timeout:180000});
  const stats=await page.evaluate(()=>window.highland.stats());console.log('SCENE',JSON.stringify(stats));
  if(stats.frames!==432||stats.sourceMeshes<3000||stats.drawCalls>150)throw Error('Unexpected scene inventory');
  fs.mkdirSync(path.join(out,'film-review'),{recursive:true});
  for(const f of [0,72,144,216,288,360,431]){const t=Date.now();const b=await page.evaluate(f=>window.highland.capture(f,'image/png'),f);fs.writeFileSync(path.join(out,'film-review',`frame-${String(f).padStart(3,'0')}.png`),Buffer.from(b,'base64'));console.log('Review frame',f,Math.round((Date.now()-t)/100)/10+'s');}
  if(reviewOnly){fs.writeFileSync(path.join(out,'film-review.json'),JSON.stringify({stats,errors},null,2));return;}
  const dest=path.join(out,'Highland-dusk-approach-and-rise-18s.mp4');
  const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate','24','-vcodec','mjpeg','-i','pipe:0','-an','-vf','scale=in_range=full:out_range=tv:in_color_matrix=bt601:out_color_matrix=bt709','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',dest],{stdio:['pipe','inherit','inherit']});const complete=once(ff,'close');
  const started=Date.now();
  for(let f=0;f<432;f++){
   const data=await page.evaluate(f=>window.highland.capture(f),f);const buf=Buffer.from(data,'base64');if(!ff.stdin.write(buf))await once(ff.stdin,'drain');
   if((f+1)%24===0)console.log(`Frames ${f+1}/432; elapsed ${Math.round((Date.now()-started)/1000)}s`);
  }
  ff.stdin.end();const [code]=await complete;if(code!==0)throw Error('Encoding failed: '+code);if(errors.length)throw Error(errors.join('\n'));
  fs.writeFileSync(path.join(out,'film-validation.json'),JSON.stringify({stats,errors,frames:432,fps:24,duration_seconds:18,resolution:[1920,1080],bytes:fs.statSync(dest).size,capture_seconds:(Date.now()-started)/1000,method:'Continuous native Blender camera, rendered with Three.js PBR building materials, diffuse context/foliage, and static street-light pool decals. Foliage uses a documented animation LOD; architecture is not decimated. The Cycles daylight still is the detailed material reference.'},null,2));
  console.log('FILM COMPLETE',dest);
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);process.exitCode=1});
