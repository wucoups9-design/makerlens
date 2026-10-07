// Teacher-only viewing; low-bandwidth snapshots stay in server memory, not portfolios.
(()=>{
  let busy=false, task=null;
  const request=async(route,body={},teacher=false)=>{
    const r=await pilotFetch('/api/monitor/'+route,{method:'POST',headers:{'Content-Type':'application/json','X-MakerLens-Workspace':ownerKey,...(teacher?{'X-MakerLens-Teacher':classroom.teacherToken()}:{})},body:JSON.stringify(body)});
    const out=await r.json();if(!r.ok)throw Error(out.error||'监控连接失败');return out;
  };
  function teacherPanel(){
    let panel=document.getElementById('classroomMonitor');
    if(panel)return panel;
    panel=document.createElement('section');panel.id='classroomMonitor';panel.className='card';
    panel.innerHTML='<h2>课堂摄像头</h2><div class="actions"><button id="monitorBegin" class="primary">开始任务</button><button id="monitorEnd">结束任务</button></div><p id="monitorTaskState" role="status"></p><p class="muted">画面每3秒更新，仅直播、不存档。离线画面自动清除。</p><div id="monitorClients" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:16px"></div>';
    document.querySelector('.content').prepend(panel);
    panel.querySelector('#monitorBegin').onclick=async()=>{try{await request('start',{name:course?.name||'制作任务'},true);await tick()}catch(e){toast(e.message)}};
    panel.querySelector('#monitorEnd').onclick=async()=>{try{await request('stop',{},true);await tick()}catch(e){toast(e.message)}};
    return panel;
  }
  function renderClients(out){
    const p=teacherPanel();p.querySelector('#monitorTaskState').textContent=out.task?'进行中：'+out.task.name:'任务未开始';
    p.querySelector('#monitorBegin').disabled=!!out.task;p.querySelector('#monitorEnd').disabled=!out.task;
    const grid=p.querySelector('#monitorClients'), clients=out.clients||[];
    const ids=new Set(clients.map(c=>c.id));for(const node of [...grid.children])if(!ids.has(node.dataset.client))node.remove();
    for(const c of clients){
      let tile=[...grid.children].find(n=>n.dataset.client===c.id);
      if(!tile){tile=document.createElement('article');tile.className='entry';tile.dataset.client=c.id;tile.innerHTML='<b></b><p></p><button style="padding:0;width:100%" aria-label="放大摄像头画面"><img style="width:100%;aspect-ratio:4/3;object-fit:contain;background:#eee" alt="课堂摄像头当前画面"></button><small></small>';grid.append(tile);
        tile.querySelector('button').onclick=()=>{const img=tile.querySelector('img');if(img.hidden)return;const dialog=document.createElement('dialog');const full=document.createElement('img');full.src=img.src;full.style.cssText='width:100%;max-width:900px';const close=document.createElement('button');close.textContent='关闭';close.onclick=()=>dialog.close();dialog.append(full,close);dialog.addEventListener('close',()=>dialog.remove());document.body.append(dialog);dialog.showModal()};}
      tile.querySelector('b').textContent=c.station+' · '+c.id.slice(0,4);
      tile.querySelector('p').textContent=!c.online?'离线':c.camera?'摄像头已打开':'摄像头未打开';
      const img=tile.querySelector('img');img.hidden=!c.image;if(c.image)img.src=c.image;else img.removeAttribute('src');
      tile.querySelector('small').textContent='最近更新 '+new Date(c.updatedAt*1000).toLocaleTimeString();
    }
    if(!clients.length)p.querySelector('#monitorTaskState').textContent+=out.task?' · 等待学生端连接':'';
  }
  async function tick(){
    if(busy||document.hidden)return;busy=true;
    try{
      if(page==='teacher'&&classroom.isTeacher()){renderClients(await request('list',{},true));return}
      const out=await request('status');task=out.task;if(!task)return;
      const video=document.getElementById('ppeVideo');
      const camera=!!(video?.srcObject?.getVideoTracks().some(t=>t.readyState==='live'&&t.enabled));
      let image='';if(camera&&video.readyState>=2){const canvas=document.createElement('canvas');canvas.width=480;canvas.height=Math.round(480*video.videoHeight/video.videoWidth)||360;canvas.getContext('2d').drawImage(video,0,0,canvas.width,canvas.height);image=canvas.toDataURL('image/jpeg',.55)}
      await request('heartbeat',{taskId:task.id,station:data.student||'未填代号',camera,image});
    }catch(e){const status=document.getElementById('monitorTaskState');if(status)status.textContent='监控连接暂不可用：'+e.message}
    finally{busy=false}
  }
  setInterval(tick,3000);window.addEventListener('load',tick);
})();
