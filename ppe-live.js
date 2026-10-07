// Continuous, serial camera sampling. Separate from the 20-minute local diary.
function ppeLivePanel(){return `<section class="card" id="ppeLivePanel"><h2>摄像头护具监测</h2><p>点击开始，允许摄像头后连续监测；点击停止即可关闭。</p><p id="ppeModeLabel" role="status">正在读取教师设置…</p><p class="muted">仅在已获学校及参与者授权的课堂使用。点击开始将上传摄像头抽帧用于识别；不开启录音、不保存监测视频。</p><video id="ppeVideo" autoplay muted playsinline style="width:100%;background:#eee;border-radius:12px" aria-label="摄像头实时预览"></video><div class="actions"><button id="ppeStart" class="primary">打开摄像头并开始监测</button><button id="ppeStop" disabled>停止监测并关闭摄像头</button></div><p id="ppeStatus" role="status">未开启；当前没有监测。</p><p id="ppeAlarm" role="alert" style="padding:12px;border:2px solid #aaa">未监测，无法判断。</p><button id="ppeSoundTest">测试提示音</button><span id="ppeSoundState">声音尚未启用</span><div id="ppeResult" hidden><p id="ppeSampleTime"></p><img id="ppePreview" class="thumb" alt="最近一次送检画面的识别结果，不是当前实时画面"><p id="ppeSummary"></p></div><details id="ppeTeacher"><summary>教师管理：设置检测项目</summary><p>需要独立的教师管理码。修改将作用于当前试点课堂的所有监测页面。</p><label for="ppeTeacherCode">教师管理码（不保存到档案）</label><input id="ppeTeacherCode" type="password" autocomplete="off"><button id="ppeTeacherUnlock">验证教师身份</button><fieldset id="ppeTeacherControls" disabled><label for="ppeTeacherMode">检测项目（仅教师可修改）</label><select id="ppeTeacherMode"><option value="both">护目镜与手套</option><option value="goggles">只检测护目镜</option><option value="gloves">只检测手套</option></select><label for="ppeGloveRule">当前工序手套规则</label><select id="ppeGloveRule"><option value="required">要求戴手套</option><option value="forbidden">禁止戴手套</option></select><label><input id="ppeGoggleRule" type="checkbox">当前工序要求护目镜</label><label><input id="ppeAlarmSound" type="checkbox" checked>启用提示音（每10秒至多一次）</label><p>连续3帧出现同类异常才提醒；无检出显示无法判断。仅用于单人/单工位试点，不识别人员身份。</p><button id="ppeTeacherSave">保存教师设置</button></fieldset><p id="ppeTeacherStatus" role="status">尚未验证教师身份。</p></details><details class="notice"><summary>监测说明与安全边界</summary><p>无框、断网、画面遮挡或结果过期均不代表安全。是否需要手套由教师按具体工序确认；系统不能自动判断设备状态、控制设备或处罚学生。后台或离开此页会关闭监测摄像头；下方每20分钟的学习留档是另一项独立功能。</p></details></section>`;}

const ppeLive = (()=>{
  const alarms=new PPEAlerts();let audio=null,reportPending=false;
  async function enableSound(){try{audio ||= new (window.AudioContext||window.webkitAudioContext)();await audio.resume();if(el('ppeSoundState'))el('ppeSoundState').textContent=audio.state==='running'?'提示音已启用':'声音被浏览器阻止，请点击测试提示音';}catch{if(el('ppeSoundState'))el('ppeSoundState').textContent='声音不可用，请关注页面提醒';}}
  function beep(){if(!audio||audio.state!=='running')return;const o=audio.createOscillator(),g=audio.createGain();o.connect(g);g.connect(audio.destination);o.frequency.value=880;g.gain.setValueAtTime(.10,audio.currentTime);g.gain.exponentialRampToValueAtTime(.001,audio.currentTime+.3);o.start();o.stop(audio.currentTime+.3);}
  function showAlarm(out){const a=alarms.update(out),box=el('ppeAlarm');if(!box)return;box.textContent=[...a.alerts,...a.unknown,...a.pending].join('；')||(a.observing?'教师尚未设置佩戴规则：只显示识别，不触发违规警报。':'本帧未触发规则提醒；不代表安全。');box.style.borderColor=a.alerts.length?'#b42318':'#9a6700';box.style.background=a.alerts.length?'#fff0ed':'#fff9e8';if(a.beep)beep();if((a.escalate||a.missingEscalate)&&!reportPending){reportPending=true;pilotFetch('/api/classroom/ppe-report',{method:'POST',headers:{'Content-Type':'application/json','X-MakerLens-Workspace':ownerKey},body:JSON.stringify({station:data.student||'未填小组代号',reason:a.escalate?'gloves_missing':'hands_not_visible'})}).then(r=>{if(!r.ok)throw Error();if(a.escalate)alarms.reported=true;else alarms.noHandsReported=true;status('已通知教师')}).catch(()=>status('教师通知发送失败，将重试')).finally(()=>{reportPending=false})}}
  let stream=null, timer=null, active=false, run=0, request=null, teacherCode='', config=null;
  const labels={both:'护目镜与手套',goggles:'护目镜',gloves:'手套'};
  const classes={goggles_worn:'佩戴护目镜',eyes_unprotected:'眼部未保护',gloves_worn:'戴手套的手',bare_hands:'裸手'};
  const el=id=>document.getElementById(id);
  function status(text){if(el('ppeStatus'))el('ppeStatus').textContent=text;}
  function stop(message='已停止；当前没有监测。'){
    el('ppeLivePanel')?.classList.remove('monitoring');
    alarms.reset();if(el('ppeAlarm'))el('ppeAlarm').textContent='监测已停止，无法判断。';
    active=false;run++;clearTimeout(timer);request?.abort();request=null;
    stream?.getTracks().forEach(t=>t.stop());stream=null;
    if(el('ppeVideo'))el('ppeVideo').srcObject=null;
    if(el('ppeStart'))el('ppeStart').disabled=config?.configured===false;
    if(el('ppePreviewStart'))el('ppePreviewStart').disabled=false;
    if(el('ppeStop'))el('ppeStop').disabled=true;
    if(el('ppeResult'))el('ppeResult').hidden=true;
    status(message);
  }
  function showConfig(c){config={...config,...c};if(!active&&el('ppeStart'))el('ppeStart').disabled=config.configured===false;const rules=c.rules||{gloves:'required',goggles_required:false,sound:true};if(el('ppeModeLabel'))el('ppeModeLabel').textContent='教师设置：'+labels[c.mode]+'；手套：'+({observe:'仅观察',required:'要求佩戴',forbidden:'禁止佩戴'}[rules.gloves])+'；护目镜：'+(rules.goggles_required?'要求佩戴':'仅观察')+'（学生不可修改）';if(el('ppeTeacherMode')&&el('ppeTeacherControls').disabled){el('ppeTeacherMode').value=c.mode;el('ppeGloveRule').value=rules.gloves;el('ppeGoggleRule').checked=rules.goggles_required;el('ppeAlarmSound').checked=rules.sound;}}
  async function api(path,body,teacher=false,signal){
    const response=await pilotFetch(path,{method:'POST',headers:{'Content-Type':'application/json',...(teacher?{'X-MakerLens-Teacher':teacherCode}:{})},body:JSON.stringify(body||{}),signal});
    const out=await response.json();if(!response.ok)throw Error(out.error||'服务暂不可用');return out;
  }
  async function sample(id){
    if(!active||id!==run||document.hidden)return;
    const video=el('ppeVideo');if(!video||video.readyState<2){stop('摄像头没有可用画面；当前没有监测。');return;}
    const started=performance.now(),taken=new Date();let timeout,controller;
    try{
      // Hide the previous result immediately; never label an old detection as current.
      status('监测运行中');

      const canvas=document.createElement('canvas'),ratio=Math.min(1,960/video.videoWidth);
      canvas.width=Math.round(video.videoWidth*ratio);canvas.height=Math.round(video.videoHeight*ratio);
      canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);
      const blob=await new Promise(resolve=>canvas.toBlob(resolve,'image/jpeg',.72));
      if(!active||id!==run)return;if(!blob)throw Error('无法读取摄像头画面');
      controller=new AbortController();request=controller;timeout=setTimeout(()=>controller.abort(),15000);
      const response=await pilotFetch('/api/ppe/detect',{method:'POST',headers:{'Content-Type':'application/octet-stream','X-MakerLens':'image'},body:blob,signal:controller.signal,cache:'no-store'});
      const out=await response.json();if(!response.ok)throw Error(out.error||'识别服务暂不可用');
      if(!active||id!==run)return;
      const elapsed=(performance.now()-started)/1000;
      if(elapsed>10)throw Error('识别结果延迟超过10秒，已停止，不能作为当前监测结果');
      el('ppePreview').src=out.image;
      el('ppeSampleTime').textContent=`送检画面：${taken.toLocaleTimeString()} · 返回延迟 ${elapsed.toFixed(1)} 秒（非当前帧）`;
      el('ppeSummary').textContent=out.detections.length?out.detections.map(d=>`${classes[d.class]||d.class} ${Math.round(d.confidence*100)}%`).join('；'):'未识别到目标，不能据此判断安全。';
      el('ppeResult').hidden=true;showConfig({mode:out.mode,revision:out.settings_revision,rules:out.rules});showAlarm(out);
      status('监测运行中');
      timer=setTimeout(()=>sample(id),Math.max(750,1000-(performance.now()-started)));
    }catch(e){if(active&&id===run)stop((e.name==='AbortError'?'检测超时或连接中断':e.message)+'；已停止监测，请检查后重新开启。');}
    finally{clearTimeout(timeout);if(request===controller)request=null;}
  }
  async function start(){
    if(!navigator.mediaDevices?.getUserMedia)throw Error('摄像头需要 HTTPS 或 localhost，以及浏览器摄像头权限');
    await enableSound();
    // One camera function at a time: the diary may be using the same physical device.
    const diaryStop=document.getElementById('captureStop');if(diaryStop&&!diaryStop.disabled)diaryStop.click();
    stop();active=true;const id=run;el('ppeStart').disabled=true;el('ppeStop').disabled=false;
    try{
      showConfig(await api('/api/ppe/session'));
      if(!active||id!==run)return;
      status('请允许摄像头权限；尚未开始识别。');
      const incoming=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720},facingMode:{ideal:'environment'}},audio:false});
      if(!active||id!==run){incoming.getTracks().forEach(t=>t.stop());return;}
      stream=incoming;el('ppeVideo').srcObject=stream;await el('ppeVideo').play();el('ppeLivePanel')?.classList.add('monitoring');
      stream.getVideoTracks()[0].addEventListener('ended',()=>stop('摄像头已断开；当前没有监测。'));
      if(active&&id===run)sample(id);
    }catch(e){if(id===run)stop('无法开启监测：'+e.message);}
  }
  async function startPreview(){
    if(!navigator.mediaDevices?.getUserMedia)throw Error('摄像头需要 HTTPS 或 localhost');
    const diaryStop=document.getElementById('captureStop');if(diaryStop&&!diaryStop.disabled)diaryStop.click();
    stop();active=true;const id=run;el('ppePreviewStart').disabled=true;el('ppeStart').disabled=true;el('ppeStop').disabled=false;
    try{const incoming=await navigator.mediaDevices.getUserMedia({video:{width:{ideal:1280},height:{ideal:720},facingMode:{ideal:'environment'}},audio:false});if(!active||id!==run){incoming.getTracks().forEach(t=>t.stop());return}stream=incoming;el('ppeVideo').srcObject=stream;await el('ppeVideo').play();stream.getVideoTracks()[0].addEventListener('ended',()=>stop('摄像头已断开'));status('摄像头仅预览 · 没有上传画面或运行识别');el('ppeAlarm').textContent='模型识别暂缓：无法判断是否佩戴护具。'}catch(e){if(id===run)stop('无法开启摄像头：'+e.message)}
  }
  function bind(){
    stop();
    if(!el('ppeLivePanel')){stop();teacherCode='';return;}
    fetch('/api/ppe/status',{cache:'no-store'}).then(r=>r.json()).then(c=>{
      showConfig(c);if(!c.configured||c.capture!=='camera-sampled'){el('ppeStart').disabled=true;status('检测服务未连接，暂时无法开始检测。');}
    }).catch(e=>status(e.message));
    el('ppeStart').onclick=()=>start().catch(e=>{status(e.message);toast(e.message)});el('ppeStop').onclick=()=>stop();
    if(el('ppePreviewStart'))el('ppePreviewStart').onclick=()=>startPreview().catch(e=>{status(e.message);toast(e.message)});
    el('ppeSoundTest').onclick=async()=>{await enableSound();beep();};
    action('#ppeTeacherUnlock',async()=>{
      teacherCode=el('ppeTeacherCode').value.trim()||(typeof classroom!=='undefined'?classroom.teacherToken():'');el('ppeTeacherControls').disabled=true;
      try{const c=await api('/api/ppe/teacher/verify',{},true);showConfig(c);el('ppeTeacherControls').disabled=false;el('ppeTeacherStatus').textContent='教师身份已验证；保存后对当前课堂生效。';}
      catch(e){teacherCode='';el('ppeTeacherStatus').textContent=e.message;throw e;}
    });
    action('#ppeTeacherSave',async()=>{
      try{showConfig(await api('/api/ppe/settings',{mode:el('ppeTeacherMode').value,rules:{gloves:el('ppeGloveRule').value,goggles_required:el('ppeGoggleRule').checked,sound:el('ppeAlarmSound').checked}},true));alarms.reset();el('ppeTeacherStatus').textContent='已保存；新送检画面将使用此设置。';}
      catch(e){el('ppeTeacherControls').disabled=true;el('ppeTeacherStatus').textContent=e.message;throw e;}
    });
  }
  document.addEventListener('visibilitychange',()=>{if(document.hidden&&active)stop('页面进入后台，摄像头已关闭；返回后请手动开启。');});
  window.addEventListener('pagehide',()=>stop());
  return {bind,stop};
})();
const basePPEPanel=ppeLivePanel;
ppeLivePanel=()=>basePPEPanel();
