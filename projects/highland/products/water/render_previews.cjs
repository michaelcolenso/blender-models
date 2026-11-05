// Usage: node render_previews.cjs http://127.0.0.1:PORT/Highland-plumbing-3D.html [output-dir]
// Screenshots the packaged viewer at 1440 x 1000 for the deliverable README previews.
const {chromium}=require('playwright');
const path=require('node:path');
const out=path.resolve(process.argv[3]||'build/highland-water');
// The viewer opens on Unit 107 with the bathroom camera; each shot clicks one of its view buttons.
const shots=[['bath','Unit-107-bathroom-preview.png'],['connections','Unit-107-connections-preview.png'],['reset','Unit-107-preview.png']];
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_PATH||undefined,headless:true,args:['--no-sandbox','--enable-unsafe-swiftshader']});
 const page=await browser.newPage({viewport:{width:1440,height:1000},deviceScaleFactor:1});
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 try{
  await page.goto(process.argv[2]);await page.waitForFunction(()=>window.ready);
  for(const [button,file] of shots){
   await page.click('#'+button);await page.waitForTimeout(1500);
   await page.screenshot({path:path.join(out,file)});console.log('Saved',file);
  }
  if(errors.length)throw Error(errors.join(';'));
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exit(1)});
