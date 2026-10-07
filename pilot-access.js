// One in-memory access code for both cloud services; never exported or persisted.
let pilotCode = '';
let pilotStatusPromise;
async function accessRequired(){
  pilotStatusPromise ||= fetch('/api/status',{signal:AbortSignal.timeout(4000)}).then(r=>r.json()).catch(()=>({access_code_required:true}));
  return !!(await pilotStatusPromise).access_code_required;
}
async function pilotFetch(url, options) {
  if (await accessRequired()) {
    pilotCode = (document.querySelector('#pilotAccess')?.value || document.querySelector('#ppeAccess')?.value || pilotCode).trim();
    if (pilotCode.length < 24) throw Error('请输入教师提供的试点访问码（两个 AI 功能共用）');
    options.headers = {...options.headers, Authorization: 'Bearer ' + pilotCode};
  }
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 195000);
  try { return await fetch(url, {...options, signal: options.signal || controller.signal}); }
  finally { clearTimeout(timer); }
}
function syncPilotAccess() {
  const button = document.querySelector('#analyzeSketch') || document.querySelector('#syncProject') || document.querySelector('#teacherCode') || document.querySelector('#processAdvice') || document.querySelector('#outcomeAdvice');
  if (button && !document.querySelector('#pilotAccess')) {
    const label = document.createElement('label');
    label.htmlFor = 'pilotAccess'; label.textContent = '课堂访问码（正式试点使用，不保存到档案）';
    const input = document.createElement('input');
    input.id = 'pilotAccess'; input.type = 'password'; input.autocomplete = 'off'; input.value = pilotCode;
    input.addEventListener('input', () => { pilotCode = input.value.trim(); });
    const panel=document.createElement('div');panel.className='pilot-access-panel';panel.append(label,input);button.before(panel);
  }
  const ppe = document.querySelector('#ppeAccess');
  if (ppe && !ppe.dataset.shared) {
    ppe.dataset.shared = 'true'; ppe.value = pilotCode;
    ppe.addEventListener('input', () => { pilotCode = ppe.value.trim(); });
  }
}
new MutationObserver(syncPilotAccess).observe(document.getElementById('app'), {childList:true, subtree:true});
