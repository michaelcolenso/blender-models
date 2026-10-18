// node render.cjs [--review-only]
const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const {once}=require('node:events');
const http=require('node:http');
const fs=require('node:fs'),path=require('node:path');
const out=path.resolve(__dirname,'../../build/highland-drone');fs.mkdirSync(out,{recursive:true});
const html=path.join(out,'Highland-drone-tour.html');
const fps=24,duration=26,steps=[0,3.2,5.7,6.5,8.8,10.5,12,12.5,13.2,14.3,15.3,15.7,16.4,17.8,18.5,18.9,19.7,22,25,26];
const only=process.argv.includes('--review-only');
(async()=>{
 const server=http.createServer((req,res)=>{res.setHeader('Content-Type','text/html; charset=utf-8');res.end(fs.readFileSync(html))});
 await new Promise(resolve=>server.listen(0,'127.0.0.1',resolve));
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:720,height:1280},deviceScaleFactor:1});const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(`http://127.0.0.1:${server.address().port}/`);await page.waitForFunction(()=>window.ready,{timeout:120000});
  const stats=await page.evaluate(()=>window.drone.stats());
  if(stats.entry!=='east-R1-08'||stats.exterior_meshes<1100||stats.interior_objects<50||stats.area_lights<10||stats.ribbons!==2||stats.foliage<30)throw Error('Incomplete building/corridor scene: '+JSON.stringify(stats));
  const checkpoints=[];
  for(const t of steps){
   const state=await page.evaluate(t=>window.drone.frame(t),t);checkpoints.push(state);
   await page.screenshot({path:path.join(out,`review-${String(t).replace('.','_')}.png`)});
  }
  // Verify that the camera crosses the broad R1 lobby glazed opening at its
  // documented location and then remains within the modeled public hall.
  const portal=checkpoints.find(x=>x.t===6.5),end=checkpoints.at(-1);
  if(!(portal.xyz_ft[0]<123&&portal.xyz_ft[0]>115&&Math.abs(portal.xyz_ft[1]-111)<1))throw Error('Camera missed lobby glazing');
  if(!(end.xyz_ft[0]>73&&end.xyz_ft[0]<79&&end.xyz_ft[1]>56&&end.xyz_ft[1]<65&&end.xyz_ft[2]>26&&end.xyz_ft[2]<27))throw Error('Camera missed R2 corridor end');
  const lift=checkpoints.find(x=>x.t===17.8);if(!(lift.car_elevation_ft-checkpoints.find(x=>x.t===15.3).car_elevation_ft>10&&lift.cutaway))throw Error('Elevator cutaway did not reach R2');
  if(checkpoints.find(x=>x.t===5.7).entry_open<.7)throw Error('Entry did not open on proximity');
  if(checkpoints.find(x=>x.t===16.4).xray<.9||checkpoints.find(x=>x.t===22).xray>.1)throw Error('Glass/brass cutaway timing failed');
  if(checkpoints.find(x=>x.t===14.3).elevator_open<.8)throw Error('Elevator door did not open');
  await page.setViewportSize({width:390,height:844});await page.evaluate(()=>window.drone.frame(10.5));
  await page.screenshot({path:path.join(out,'mobile-review.png')});
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth);
  if(overflow)throw Error('Mobile viewer overflow');
  await page.locator('#play').click();await page.waitForTimeout(220);await page.locator('#play').click();
  if(!(await page.evaluate(()=>+document.querySelector('#scrub').value>10.5)))throw Error('Playback did not advance');
  await page.setViewportSize({width:720,height:1280});
  const result={source_entry:stats.entry,exterior_meshes:stats.exterior_meshes,interior_objects:stats.interior_objects,checkpoints,mobile_overflow:false,browser_errors:errors};
  if(!only){
   // The video is recorded deterministically from the same mobile viewer.
   await page.addStyleTag({content:'#play,#scrub,#time{display:none}.controls{height:2px}.top h1{font-size:30px}.bottom{padding-bottom:54px}'});
   const dest=path.join(out,'Highland-corridor-drone-silent.mp4');
   const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-vcodec','mjpeg','-i','pipe:0','-an','-c:v','libx264','-preset','veryfast','-crf','20','-pix_fmt','yuv420p','-movflags','+faststart',dest],{stdio:['pipe','inherit','inherit']});
   const complete=once(ff,'close');
   for(let f=0;f<duration*fps;f++){
    const t=f/fps;await page.evaluate(t=>window.drone.frame(t),t);
    const buf=await page.screenshot({type:'jpeg',quality:89});
    if(!ff.stdin.write(buf))await once(ff.stdin,'drain');
    if((f+1)%72===0)console.log(`Captured ${f+1}/${duration*fps} frames`);
   }
   ff.stdin.end();const [code]=await complete;if(code!==0)throw Error('ffmpeg returned '+code);
   Object.assign(result,{fps,frames:duration*fps,duration_seconds:duration,resolution:[720,1280],video_bytes:fs.statSync(dest).size});
  }
  if(errors.length)throw Error(errors.join(';'));
  fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify(result,null,2)+'\n');
  console.log(`Flight review passed. Exterior meshes: ${stats.exterior_meshes}; interior objects: ${stats.interior_objects}.`);
 }finally{await browser.close();server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
