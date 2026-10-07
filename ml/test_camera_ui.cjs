// Deterministic browser-API mocks. Never opens a physical camera or sends images.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const ids=['ppeAlarm','ppeSoundState','ppeSoundTest','ppeGloveRule','ppeGoggleRule','ppeAlarmSound','ppeLivePanel','ppeVideo','ppeStatus','ppeResult','ppeStart','ppeStop','ppeModeLabel','ppeTeacherMode','ppeTeacherControls','ppeTeacherStatus','ppeTeacherUnlock','ppeTeacherSave','ppeTeacherCode','ppeLiveConsent','ppePreview','ppeSummary','ppeSampleTime'];
const elements=Object.fromEntries(ids.map(id=>[id,{style:{},disabled:id==='ppeTeacherControls',hidden:false,value:'',textContent:'',checked:true}]));
Object.assign(elements.ppeVideo,{readyState:4,videoWidth:640,videoHeight:480,play:async()=>{}});
let stops=0,calls=[],timers=new Map(),counter=0,events={},fail=false,denied=false;
const track={stop(){stops++},addEventListener(){}};
const context=vm.createContext({console,AbortController,Date,Math,Promise,Error,
 PPEAlerts:require('../ppe-alerts.js'),performance:{now:()=>0},setTimeout:(f,ms)=>{timers.set(++counter,{f,ms});return counter},clearTimeout:id=>timers.delete(id),
 document:{hidden:false,getElementById:id=>elements[id]||null,addEventListener:(n,f)=>events[n]=f,createElement:()=>({getContext:()=>({drawImage(){}}),toBlob:f=>f({synthetic:true})})},
 window:{addEventListener:(n,f)=>events[n]=f},navigator:{mediaDevices:{getUserMedia:async opts=>{assert.equal(opts.audio,false);if(denied)throw Error('Permission denied');return{getTracks:()=>[track],getVideoTracks:()=>[track]}}}},
 fetch:async()=>({json:async()=>({configured:true,capture:'camera-sampled',mode:'both'})}),
 pilotFetch:async(path,opts)=>{calls.push({path,opts});if(fail)throw Error('network failed');return{ok:true,json:async()=>path.endsWith('/detect')?{mode:'both',settings_revision:1,detections:[],image:'test'}:{configured:true,capture:'camera-sampled',mode:'both'}}},
 action:(id,fn)=>{elements[id.slice(1)].onclick=fn},toast:()=>{}
});
vm.runInContext(fs.readFileSync(require('path').join(__dirname,'../ppe-live.js'),'utf8')+'\nglobalThis.testLive=ppeLive;',context);
const flush=async()=>{for(let i=0;i<20;i++)await Promise.resolve()};
(async()=>{
 context.testLive.bind();await flush();assert(elements.ppeTeacherControls.disabled);
 await elements.ppeStart.onclick();await flush();assert(calls.some(c=>c.path.endsWith('/detect')));assert(elements.ppeStart.disabled);assert(!elements.ppeResult.hidden);
 const detect=calls.find(c=>c.path.endsWith('/detect'));assert(!('X-MakerLens-Mode' in detect.opts.headers));
 const next=[...timers.values()].find(t=>t.ms===1000);assert(next);next.f();await flush();assert.equal(calls.filter(c=>c.path.endsWith('/detect')).length,2);
 elements.ppeStop.onclick();assert(stops>0);assert(elements.ppeResult.hidden);assert(!elements.ppeStart.disabled);
 await elements.ppeStart.onclick();await flush();context.document.hidden=true;events.visibilitychange();assert(elements.ppeResult.hidden);assert(!elements.ppeStart.disabled);context.document.hidden=false;
 denied=true;await elements.ppeStart.onclick();await flush();assert(elements.ppeStatus.textContent.includes('Permission denied'));denied=false;
 fail=true;await elements.ppeStart.onclick();await flush();assert(elements.ppeStatus.textContent.includes('network failed'));fail=false;
 elements.ppeLiveConsent.checked=false;let before=calls.length;await elements.ppeStart.onclick();await flush();assert.equal(calls.length,before);
 console.log('PASS: serial camera sampling, shared access, no client mode, stop/background cleanup, permission/network failure, consent gate.');
})().catch(e=>{console.error(e);process.exitCode=1});
