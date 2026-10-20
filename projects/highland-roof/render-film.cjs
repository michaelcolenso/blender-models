// Resume-safe lossless capture of the native camera move, then encode BT.709 video.
const {chromium}=require('playwright');
const {spawn,execFileSync}=require('node:child_process');
const {once}=require('node:events');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),crypto=require('node:crypto');
const here=__dirname,root=path.resolve(here,'../..'),out=path.join(root,'deliverables/highland-roof');
const cache=path.join(root,'build/highland-geometry/film-frames');
const sky=path.join(root,'projects/highland-cinematic/assets/kloofendal_48d_partly_cloudy_puresky_4k.hdr');
const args=new Set(process.argv.slice(2));
const digest=files=>{const h=crypto.createHash('sha256');for(const p of files)h.update(fs.readFileSync(p));return h.digest('hex');};
const runtime={node:process.version,chromium:execFileSync(process.env.CHROMIUM_PATH||'/usr/bin/chromium',['--version']).toString().trim(),platform:process.platform,architecture:process.arch};
const signature=crypto.createHash('sha256').update(JSON.stringify(runtime)).update(digest([__filename,path.join(here,'viewer.html'),path.join(here,'viewer.js'),path.join(here,'package-lock.json'),path.join(out,'Highland-geometry-revised.glb'),path.join(out,'camera-path.json'),path.join(out,'revision-validation.json'),sky])).digest('hex');
const frameFile=f=>path.join(cache,`frame-${String(f).padStart(3,'0')}.png`);
(async()=>{
 fs.mkdirSync(cache,{recursive:true});fs.mkdirSync(path.join(out,'film-review'),{recursive:true});
 const manifest=path.join(cache,'manifest.json');
 if(fs.existsSync(manifest)&&JSON.parse(fs.readFileSync(manifest)).signature!==signature){throw Error('Capture inputs changed; move/remove build/highland-geometry/film-frames before recapturing.');}
 fs.writeFileSync(manifest,JSON.stringify({signature,frames:432,width:1920,height:1080,format:'lossless PNG'} ,null,2));
 if(!args.has('--encode-only')){
  const server=http.createServer((req,res)=>{
   const uri=new URL(req.url,'http://localhost').pathname;
   const routes={'/':path.join(here,'viewer.html'),'/sky.hdr':sky};
   const file=routes[uri]||path.resolve(uri.startsWith('/output/')?out:here,uri.replace(/^\/(output\/)?/,''));
   if(!(file===sky||file.startsWith(here+'/')||file.startsWith(out+'/'))){res.writeHead(403);return res.end();}
   if(!fs.existsSync(file)){res.writeHead(404);return res.end();}
   res.setHeader('Content-Type',file.endsWith('.js')?'text/javascript':file.endsWith('.html')?'text/html':file.endsWith('.json')?'application/json':'application/octet-stream');fs.createReadStream(file).pipe(res);
  });
  await new Promise(r=>server.listen(0,'127.0.0.1',r));
  const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader']});
  const errors=[];const page=await browser.newPage({viewport:{width:1920,height:1080},deviceScaleFactor:1});page.setDefaultTimeout(180000);page.on('pageerror',e=>errors.push(e.message));
  const started=Date.now();
  try{
   await page.goto(`http://127.0.0.1:${server.address().port}/`);await page.waitForFunction(()=>window.ready,{timeout:240000});
   const stats=await page.evaluate(()=>window.highland.stats());console.log('SCENE',JSON.stringify(stats));
   if(stats.frames!==432||stats.sourceMeshes<3000||stats.drawCalls>150||stats.msaaSamples!==4||stats.glError)throw Error('Unexpected scene inventory or AA capability');
   const frames=args.has('--review-only')?[0,72,144,216,288,360,431]:Array.from({length:432},(_,i)=>i);
   let captured=0;
   for(const f of frames){
    if(!fs.existsSync(frameFile(f))){
     const t=Date.now(),b=await page.evaluate(f=>window.highland.capture(f,'image/png'),f);
     fs.writeFileSync(frameFile(f),Buffer.from(b,'base64'));captured++;
     if(args.has('--review-only')||(f+1)%12===0)console.log(`Frame ${f+1}/432; ${((Date.now()-t)/1000).toFixed(1)}s; elapsed ${Math.round((Date.now()-started)/1000)}s`);
    }
    if([0,72,144,216,288,360,431].includes(f))fs.copyFileSync(frameFile(f),path.join(out,'film-review',path.basename(frameFile(f))));
   }
   if(errors.length)throw Error(errors.join('\n'));
   const finalStats=await page.evaluate(()=>window.highland.stats());if(finalStats.glError)throw Error('WebGL capture error '+finalStats.glError);
   const record={signature,runtime,stats,finalStats,errors,captured_this_run:captured,elapsed_seconds:(Date.now()-started)/1000,method:'Native Blender camera sampled for all 432 frames. Three.js PBR exterior, diffuse context/foliage LOD, static shadow map and street-light pool decals; Native 4x MSAA for rails/window frames over the depth-matched base, then full-frame FXAA. Cycles daylight is the detailed native material reference; film lighting is an approximation.'};
   fs.writeFileSync(path.join(out,args.has('--review-only')?'film-review.json':'film-capture.json'),JSON.stringify(record,null,2)+'\n');
   if(args.has('--aa-compare')){
    await page.goto(`http://127.0.0.1:${server.address().port}/?aa=off`);await page.waitForFunction(()=>window.ready,{timeout:240000});
    const b=await page.evaluate(()=>window.highland.capture(216,'image/png'));fs.writeFileSync(path.join(out,'film-review/frame-216-fxaa-only.png'),Buffer.from(b,'base64'));
    fs.writeFileSync(path.join(out,'aa-comparison.json'),JSON.stringify({baseline:await page.evaluate(()=>window.highland.stats()),revised:stats,frame:217},null,2)+'\n');
   }
  }finally{await browser.close();await new Promise(r=>server.close(r));}
 }
 if(args.has('--review-only'))return;
 for(let f=0;f<432;f++)if(!fs.existsSync(frameFile(f)))throw Error('Missing frame '+f);
 const dest=path.join(out,'Highland-dusk-geometry-revised-18s.mp4');
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-framerate','24','-i',path.join(cache,'frame-%03d.png'),'-frames:v','432','-an','-vf','scale=in_range=full:out_range=tv:out_color_matrix=bt709','-c:v','libx264','-threads','2','-preset','fast','-crf','18','-pix_fmt','yuv420p','-color_range','tv','-colorspace','bt709','-color_primaries','bt709','-color_trc','bt709','-movflags','+faststart',dest],{stdio:'inherit'});
 const [code]=await once(ff,'close');if(code!==0)throw Error('Encoding failed '+code);
 fs.writeFileSync(path.join(out,'film-encoding.json'),JSON.stringify({signature,frames:432,fps:24,duration_seconds:18,resolution:[1920,1080],bytes:fs.statSync(dest).size,source:'Lossless RGB PNG frame cache; full RGB to limited-range BT.709 conversion.'},null,2)+'\n');console.log('FILM COMPLETE',dest);
})().catch(e=>{console.error(e);process.exitCode=1;});
