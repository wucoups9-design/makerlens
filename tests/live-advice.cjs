// Optional integration check: sends only a synthetic diagram to the configured provider.
const {chromium}=require('playwright'),assert=require('node:assert/strict');
(async()=>{
const browser=await chromium.launch({headless:true,channel:'chrome'});
try{const p=await browser.newPage();await p.goto(process.env.MAKERLENS_BASE_URL||'http://127.0.0.1:8766/');await p.locator('#projectSelect').waitFor();
const image=await p.evaluate(()=>{const c=document.createElement('canvas');c.width=500;c.height=400;const x=c.getContext('2d');x.fillStyle='white';x.fillRect(0,0,500,400);x.strokeStyle='black';x.lineWidth=2;x.strokeRect(140,100,220,100);x.beginPath();x.moveTo(250,50);x.lineTo(250,290);x.stroke();x.font='18px sans-serif';x.fillStyle='black';x.fillText('Synthetic classroom test diagram',30,340);x.fillText('Dimensions and material unknown',30,365);return c.toDataURL('image/jpeg')});
for(const kind of ['sketch','process','outcome']){const out=await p.evaluate(async({image,kind})=>{const r=await fetch('/api/sketch-feedback',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({image,kind,design:'功能测试合成示意图，无真实学生或作品。尺寸和材料尚未确定，请简短列出需要核对的问题。'})});const body=await r.json();return{status:r.status,feedbackLength:typeof body.feedback==='string'?body.feedback.length:0,error:body.error||null}}, {image,kind});assert.equal(out.status,200,JSON.stringify(out));assert(out.feedbackLength>0);console.log(JSON.stringify({kind,status:out.status,feedbackLength:out.feedbackLength,syntheticInput:true}))}
}finally{await browser.close()}
})().catch(e=>{console.error(e.message);process.exitCode=1});
