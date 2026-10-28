// node projects/highland/products/repipe/render.cjs URL [output-dir] [--review-only]
const {chromium}=require('playwright'),{spawn}=require('node:child_process'),{once}=require('node:events'),fs=require('node:fs'),path=require('node:path');
const out=path.resolve(process.argv[3]||'build/highland-repipe');fs.mkdirSync(out,{recursive:true});
(async()=>{const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||'/usr/bin/chromium',headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});const page=await browser.newPage({viewport:{width:1280,height:900}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
try{await page.goto(process.argv[2]);await page.waitForFunction(()=>window.ready);const stage=page.locator('#stage');
const checks=[];const phases=await page.evaluate(()=>window.REPIPE_SPEC.phases);let start=0;
for(let i=0;i<phases.length;i++){const p=phases[i],t=start+p.seconds*.5;const state=await page.evaluate(t=>window.repipe.frame(t),t);checks.push({time:t,...state});await stage.screenshot({path:path.join(out,`phase-${i+1}.png`)});start+=p.seconds;}
const before=await page.evaluate(()=>window.repipe.frame(17.99));if(before.connected_pilot_ports!==0)throw Error('Pilot connected before test gate');
const end=await page.evaluate(()=>window.repipe.frame(31.99));if(end.connected_pilot_ports!==9||end.visible_routes!==37)throw Error('Incomplete route/tie sequence');
await page.locator('[data-phase="3"]').click();if(!((await page.locator('#title').innerText()).startsWith('04')))throw Error('Phase navigation failed');
await page.locator('#play').click();await page.waitForTimeout(250);await page.locator('#play').click();if(await page.evaluate(()=>+document.getElementById('scrub').value)<=14)throw Error('Playback did not advance');
await page.setViewportSize({width:390,height:844});await page.screenshot({path:path.join(out,'mobile-review.png'),fullPage:true});if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw Error('Mobile overflow');await page.setViewportSize({width:1280,height:900});
const validation={...await page.evaluate(()=>window.repipe.validation()),phase_checks:checks,before_cutover:before,end_state:end,browser_errors:errors,mobile_overflow:false};
if(!process.argv.includes('--review-only')){
const fps=24,total=32*fps;const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate',String(fps),'-vcodec','mjpeg','-i','pipe:0','-an','-c:v','libx264','-preset','medium','-crf','19','-pix_fmt','yuv420p','-movflags','+faststart',path.join(out,'Highland-repipe-strategy.mp4')],{stdio:['pipe','inherit','inherit']});const complete=once(ff,'close');
for(let f=0;f<total;f++){await page.evaluate(t=>window.repipe.frame(t),f/fps);const buf=await stage.screenshot({type:'jpeg',quality:92});if(!ff.stdin.write(buf))await once(ff.stdin,'drain');if((f+1)%96===0)console.log(`Captured ${f+1}/${total} frames`);}
ff.stdin.end();const [code]=await complete;if(code!==0)throw Error('Encoder failed: '+code);Object.assign(validation,{fps,frames:total,duration_seconds:32,resolution:[1280,720]});}
if(errors.length)throw Error(errors.join(';'));fs.writeFileSync(path.join(out,'validation.json'),JSON.stringify(validation,null,2)+'\n');console.log('Sequence checks passed.');
}finally{await browser.close();}})().catch(e=>{console.error(e);process.exit(1)});
