// Usage: node render_video.cjs http://127.0.0.1:PORT/Highland-plumbing-3D.html [output-dir]
// Requires Playwright, Chromium and FFmpeg. Capture is deterministic at 24 fps.
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const {once}=require('node:events');
const fs=require('node:fs');
const path=require('node:path');
const out=path.resolve(process.argv[3]||'build/highland-water');fs.mkdirSync(out,{recursive:true});
const fps=24;
const shots=[
 {seconds:10,title:'Unit 107 · Primary bathroom',subtitle:'Five fixtures · nine water-supply connections',target:[-7,1,-5.5],position:[.5,8.5,3.3],start:-.24,end:.3},
 {seconds:8,title:'Behind the fixtures',subtitle:'Representative shutoffs and flexible faucet supplies',target:[-7.3,.85,-4.4],position:[-2,3.2,0],start:-.18,end:.18},
 {seconds:6,title:'The bathroom within Unit 107',subtitle:'Domestic-water distribution · P4.01',target:[0,1,2.18],position:[16,21,25],start:.08,end:-.16}
];
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1280,height:720},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
 await page.goto(process.argv[2]);await page.waitForFunction(()=>window.ready);
 await page.addStyleTag({content:`header,aside,.topbar,.footer,.hint{display:none!important}.layout{display:block;height:720px;min-height:0}.stage{height:720px}#film{position:absolute;inset:0;pointer-events:none;font-family:Arial,sans-serif}#film .head{position:absolute;top:0;left:0;right:0;padding:25px 36px 50px;background:linear-gradient(#0b1822,transparent)}#film h2{font-size:28px;font-weight:500;margin:10px 0}#film p{font-size:15px;margin:0}#film .foot{position:absolute;bottom:0;left:0;right:0;padding:35px 36px 22px;background:linear-gradient(transparent,#0b1822 45%);font-size:12px;line-height:1.7;color:#b8cbd5}#film .legend{font-size:14px;margin-bottom:7px;max-width:none;display:block}#progress{position:absolute;bottom:0;left:0;height:3px;background:#91c8d4}`});
 await page.evaluate(()=>{const d=document.createElement('div');d.id='film';d.innerHTML='<div class="head"><div class="eyebrow">HIGHLAND / INSIDE THE PLUMBING</div><h2 id="film-title"></h2><p id="film-subtitle"></p></div><div class="foot"><div class="legend"><span style="color:#379eff">● Cold</span> &nbsp; <span style="color:#ff694a">● Hot</span> &nbsp; <span style="color:#41dda2">● Return</span> &nbsp; <span style="color:#b78aff">● Mixed</span> &nbsp; <span style="color:#c6aa65">● Fittings</span></div>Drawing-based domestic-water study · Heights, local offsets and hardware assumed.<br>Pipe diameters shown at 1.5× nominal. Drainage and vent piping are not included.</div><div id="progress"></div>';document.querySelector('.stage').append(d);});
 // Let ResizeObserver finish before placing the first camera.
 await page.waitForTimeout(250);
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-vcodec','mjpeg','-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,'Unit-107-plumbing-animation.mp4')],{stdio:['pipe','inherit','inherit']});
 const complete=once(ff,'close');let frame=0;const total=shots.reduce((n,s)=>n+s.seconds*fps,0);
 for(let j=0;j<shots.length;j++){
  const s=shots[j],count=s.seconds*fps;
  for(let i=0;i<count;i++,frame++){
   const t=i/(count-1),ease=t*t*(3-2*t);
   await page.evaluate(({s,angle,progress})=>{document.getElementById('film-title').textContent=s.title;document.getElementById('film-subtitle').textContent=s.subtitle;document.getElementById('progress').style.width=progress+'%';window.videoFrame({...s,angle});},{s,angle:s.start+(s.end-s.start)*ease,progress:100*frame/(total-1)});
   const buf=await page.screenshot({type:'jpeg',quality:92});
   if(i===Math.floor(count/2))fs.writeFileSync(path.join(out,`video-shot-${j+1}.jpg`),buf);
   if(!ff.stdin.write(buf))await once(ff.stdin,'drain');
  }
  console.log(`Shot ${j+1}/${shots.length} captured (${frame}/${total} frames)`);
 }
 ff.stdin.end();const [code]=await complete;if(code!==0)throw Error('FFmpeg failed: '+code);
 if(errors.length)throw Error(errors.join(';'));
 fs.writeFileSync(path.join(out,'video-validation.json'),JSON.stringify({fps,frames:frame,duration_seconds:frame/fps,resolution:[1280,720],browser_errors:errors,shots:shots.map(s=>({title:s.title,seconds:s.seconds}))},null,2));
 console.log('Video complete.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
