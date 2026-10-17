// The selected workshop design. All content comes from the existing portfolio.
'use strict';
function studioIcon(kind) {
  const paths = {
    home: '<rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/>',
    sketch: '<path d="m4 16 11-11 4 4L8 20H4v-4ZM13 7l4 4M4 20h16"/>',
    skills: '<path d="m12 3 9 5v9l-9 5-9-5V8l9-5Zm0 10 9-5M3 8l9 5v9"/>',
    making: '<rect x="3" y="6" width="14" height="13" rx="2"/><path d="m17 10 4-3v11l-4-3M7 3h6"/>',
    test: '<path d="M4 3v17h17M8 15v-3M13 15V8M18 15V5"/>',
    outcome: '<rect x="4" y="2" width="16" height="20" rx="2"/><path d="M8 6h8M8 16l3-4 5 5M8 19h8"/>',
    teacher: '<circle cx="9" cy="8" r="3"/><path d="M3 20v-3a6 6 0 0 1 12 0v3M16 5a3 3 0 0 1 0 6M18 14a5 5 0 0 1 3 4v2"/>',
    settings: '<path d="M4 7h16M4 17h16M8 4v6M16 14v6"/>',
    arrow: '<path d="M4 12h15m-5-5 5 5-5 5"/>',
    expand: '<path d="m12 3 9 5-9 5-9-5 9-5ZM3 12l9 5 9-5M3 16l9 5 9-5"/>',
    check: '<path d="m5 12 4 4L19 6"/>'
  };
  return `<svg class="studio-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${paths[kind] || paths.home}</svg>`;
}

function workshopLogo() {
  return '<svg viewBox="0 0 32 32" aria-hidden="true"><rect x="1" y="1" width="30" height="30" rx="8" fill="currentColor"/><path d="m8 22 1-12 7 8 7-8 1 12" fill="none" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="16" cy="7" r="1.5" fill="white"/></svg>';
}

function workshopShell(title, body) {
  const descriptions = {
    home: '从想法到作品，把每一步做好。', sketch: '画下想法，再看看哪里可以改进。',
    skills: '先练习，再到工位制作。', making: '开始监测，专心制作。',
    test: '记录一次测试，让改进有依据。', outcome: '把作品与成长一起留下。',
    teacher: '安排任务，关注每一组的进展。', settings: '管理作品，保留每一次尝试。'
  };
  return `<a class="skip-link" href="#workspace">跳到工作区</a><div class="shell">
    <aside class="side">
      <a class="workshop-brand" href="#workspace" data-page="home" aria-label="MakerLens 工作台">${workshopLogo()}<strong>MakerLens</strong></a>
      <span class="brand-sub">智创工坊</span><p class="nav-caption">我的项目</p>
      <nav class="workshop-nav" aria-label="工作区导航">${nav.map(([key, number, label], i) => `<button data-page="${key}" class="nav-item ${page === key ? 'active' : ''} ${i === 6 ? 'teacher-link' : ''}" ${page === key ? 'aria-current="page"' : ''}>${studioIcon(key)}<span>${label}</span>${i < 6 ? `<small>${number}</small>` : ''}</button>`).join('')}</nav>
      <div class="project-switcher"><label for="projectSelect">当前作品</label><select id="projectSelect">${projects.filter(x => !x.archived || x.id === data.id).map(x => `<option value="${esc(x.id)}" ${x.id === data.id ? 'selected' : ''}>${esc(x.name)}</option>`).join('')}</select><button id="newProject">＋ 新建作品</button><p>保存在此浏览器<br>换设备前可同步或备份</p></div>
    </aside>
    <div class="workshop-main"><header class="workshop-topbar"><div class="breadcrumb"><span>${esc(data.name)}</span><span aria-hidden="true">/</span><span>${esc(title)}</span></div><div class="workshop-identity"><span class="identity-dot">${studioIcon(classroom.isTeacher() ? 'teacher' : 'skills')}</span><span>${esc(classroom.isTeacher() ? '教师已验证' : data.student || '学生工作区')}</span></div></header>
      <section id="workspace" class="content" data-view="${page}" tabindex="-1" aria-label="${esc(title)}"><div class="page-heading"><div><h1>${page === 'home' ? '我的工作台' : esc(title)}</h1><p>${descriptions[page] || ''}</p></div></div>${body}</section>
      <footer class="site-footer"><span>MakerLens · STEM创作助手</span><a href="https://beian.miit.gov.cn/" target="_blank" rel="noopener noreferrer">闽ICP备2026039637号-1</a></footer>
    </div></div>`;
}

function workshopDrawing() {
  return `<svg class="workshop-drawing" viewBox="0 0 420 260" role="img" aria-label="作品设计概念示意图，不是施工图">
    <g class="ghost" fill="none" stroke="currentColor"><rect x="78" y="42" width="264" height="174" rx="18" stroke-dasharray="5 7"/><path d="M210 28v202M62 129h296" stroke-dasharray="3 6" opacity=".45"/></g>
    <g class="layer project-form"><rect x="126" y="76" width="168" height="106" rx="12" fill="currentColor" fill-opacity=".12"/><rect x="145" y="95" width="130" height="68" rx="8" fill="none"/><path d="M167 129h86M210 107v44" fill="none" opacity=".6"/><circle cx="210" cy="129" r="10" fill="currentColor" fill-opacity=".28"/></g>
    <g class="layer detail"><path d="M126 92 99 70M294 92l27-22M126 166 98 188M294 166l28 22" fill="none"/><circle cx="98" cy="70" r="5" fill="currentColor"/><circle cx="322" cy="70" r="5" fill="currentColor"/><circle cx="98" cy="188" r="5" fill="currentColor"/><circle cx="322" cy="188" r="5" fill="currentColor"/></g>
    <g class="drawing-label" fill="currentColor" font-size="10"><text x="175" y="239">作品概念示意 · 非施工尺寸</text></g>
  </svg>`;
}

function workshopArt() {
  const cover = data.outcomeImage || data.sketches.filter(x => x.image).at(-1)?.image;
  if (cover && img(cover)) return `<div class="workshop-art">${img(cover)}<div class="art-controls"><span>${data.outcomeImage ? '我的作品' : '最新草图'}</span><button data-page="${data.outcomeImage ? 'outcome' : 'sketch'}">查看记录 ${studioIcon('arrow')}</button></div></div>`;
  return `<div class="workshop-art">${workshopDrawing()}<div class="art-controls"><span>示意图 · 非施工尺寸</span><button id="expandStructure" aria-pressed="false">展开结构 ${studioIcon('expand')}</button></div></div>`;
}

function workshopMilestones() {
  return [
    {label:'明确学习任务', hint:'看看这次要完成什么', target:'settings', done:!!data.goal},
    {label:'完善设计草图', hint:'先确认尺寸与连接', target:'sketch', done:!!data.sketches.length},
    {label:'选择加工工序', hint:'看看需要哪些工具', target:'skills', done:!!(data.done.length || data.cubeDone.length)},
    {label:'记录制作过程', hint:'留下一次尝试', target:'making', done:!!data.records.length},
    {label:'做一次作品测试', hint:'记录，再改一个变量', target:'test', done:!!data.tests.length},
    {label:'整理作品与收获', hint:'把成长做成海报', target:'outcome', done:!!data.reflection}
  ];
}

function workshopActivity() {
  const events = ['sketches', 'records', 'tests'].flatMap((kind, group) => data[kind].map((record, i) => ({
    ...record, kind, target:['sketch','making','test'][group],
    title:kind === 'sketches' ? `保存第 ${i + 1} 版草图` : kind === 'tests' ? '记录作品测试' : '保存制作记录',
    order:Date.parse(record.time) || i
  }))).sort((a,b) => b.order - a.order).slice(0,3);
  return events.length ? events.map(x => `<button class="activity-row" data-page="${x.target}">${studioIcon(x.target)}<span><strong>${x.title}</strong><small>${esc(x.note || '已保存，点击查看')}</small></span><time>${esc(x.time)}</time></button>`).join('') : '<div class="workshop-empty">还没有学习记录。<br><span>保存一张草图，从第一个想法开始。</span></div>';
}

function homeView() {
  const milestones = workshopMilestones(), finished = milestones.filter(x => x.done).length;
  const next = milestones.filter(x => !x.done).slice(0,3);
  return `<div class="home-layout"><section class="project-card"><div class="project-copy"><span class="status-badge">${studioIcon('sketch')}${esc(data.status)}</span><div><h2>${esc(data.name)}</h2><p>${esc(data.goal || '从一个想法，走到一件真正的作品。')}</p></div><div class="project-meta"><span>${esc(data.student || '小组未设置')}</span><span>草图 ${data.sketches.length} 版</span><span>测试记录 ${data.tests.length} 条</span></div><div class="actions"><button class="primary" data-page="sketch">${studioIcon('arrow')}${data.sketches.length ? '继续设计' : '开始设计'}</button><button data-page="skills">${studioIcon('skills')}查看工序</button></div></div>${workshopArt()}</section>
    <aside class="next-up"><h2>下一步做什么</h2>${next.length ? `<ol>${next.map((x,i) => `<li><span class="step-dot">${i+1}</span><button data-page="${x.target}">${x.label}<small>${x.hint}</small></button></li>`).join('')}</ol>` : '<p>每个学习节点都有记录了。<br>回看证据，整理你的收获。</p><button data-page="outcome">查看成果</button>'}<div class="progress-caption"><span>学习节点</span><span>${finished} / 6</span></div><div class="progress" role="progressbar" aria-label="学习节点" aria-valuemin="0" aria-valuemax="6" aria-valuenow="${finished}"><span style="width:${finished/6*100}%"></span></div></aside></div>
    <div class="home-bottom"><section><div class="section-heading"><h2>最近的学习记录</h2><button class="text-button" data-page="outcome">查看档案</button></div>${workshopActivity()}</section><section><div class="section-heading"><h2>在这里继续</h2></div><button class="quick-row" data-page="making"><span>${studioIcon('making')}制作时，打开监测</span>${studioIcon('arrow')}</button><button class="quick-row" data-page="outcome"><span>${studioIcon('outcome')}把作品做成海报</span>${studioIcon('arrow')}</button><button class="quick-row" data-page="settings"><span>${studioIcon('settings')}管理作品与备份</span>${studioIcon('arrow')}</button></section></div>
    <details class="workshop-task"><summary>查看课堂任务与分工</summary><p>${esc(course?.instructions || data.goal)}</p><p>分工：${esc(data.members || '尚未填写')}</p><p>完成日期：${esc(data.deadline || course?.deadline || '未设置')}</p><button data-page="settings">编辑我的作品信息</button></details>`;
}

function workshopSketchView() {
  const latest = data.sketches.filter(x => x.image).at(-1);
  return `<div class="sketch-workspace"><section class="card sketch-editor"><div class="section-heading"><h2>我的草图</h2><span class="muted">${data.sketches.length ? `已保存 ${data.sketches.length} 版` : '从第一版开始'}</span></div><div id="sketchPreview" class="sketch-preview">${latest ? img(latest.image) : `${studioIcon('sketch')}<p>把你的想法放在这里</p><small>选择一张草图，开始设计。</small>`}</div>${input('sketchPhoto',latest?'更换 / 添加草图':'选择草图','','file')}${area('sketchNote','想补充什么？（选填）')}<button id="saveSketchOnly">保存草图版本</button></section>
    <section class="card sketch-advisor"><h2>设计建议</h2><div class="feedback-placeholder">${studioIcon('skills')}<h3>让想法更可行。</h3><p>检查尺寸、连接与所需工具，<br>看看有没有遗漏。</p></div><section id="feedbackCard" hidden><h3>本次反馈</h3><div id="aiFeedback" class="ai-feedback"></div>${select('aiDecision','我的判断',['','采纳并修改','不采纳','暂缓，先向教师确认'])}${area('aiEvidence','理由或证据')}<button class="primary" id="addSketch">保存我的判断</button></section><div class="advice-controls"><label class="check"><input id="aiConsent" type="checkbox">同意将草图与说明发送到阿里云百炼，已移除个人信息。</label><div class="actions"><button class="primary" id="analyzeSketch">请求 AI 建议</button><button id="designChecklist">离线检查清单</button></div><p id="aiStatus" role="status">正在检查 AI 服务…</p><p id="analysisStatus" role="status"></p><p class="muted advice-note">AI 建议需验证。设备操作遵守学校安全要求。</p></div></section></div>
    <details class="card"><summary>设计检查与学校工具</summary><ol class="steps"><li>标清尺寸与孔位。</li><li>说明连接、防松与配重。</li><li>确认所需工具，遵守教师设置的限制。</li><li>记录一个可验证的假设。</li></ol><h3>教师设置的材料与工具</h3><p id="schoolResources">${esc(course?.materials?.trim() || '教师尚未填写。AI 会建议所需工具，实际使用前请确认设备是否可用。')}</p></details><details class="card"><summary>草图版本对比</summary>${comparisonView()}</details><details class="card"><summary>草图记录与教师反馈</summary>${entries(data.sketches,'sketches')}</details>`;
}

function bindWorkshopDesign() {
  const expand = document.getElementById('expandStructure');
  if (expand) expand.onclick = () => {
    const open = expand.getAttribute('aria-pressed') !== 'true';
    document.querySelector('.workshop-drawing')?.classList.toggle('exploded', open);
    expand.setAttribute('aria-pressed', String(open));
    expand.innerHTML = `${open ? '收起结构' : '展开结构'} ${studioIcon('expand')}`;
  };
  const navElement = document.querySelector('.workshop-nav'), active = navElement?.querySelector('[aria-current="page"]');
  if (active && getComputedStyle(navElement).overflowX === 'auto') {
    navElement.scrollLeft = active.offsetLeft - navElement.offsetLeft - (navElement.clientWidth - active.clientWidth) / 2;
  }
  const file = document.getElementById('sketchPhoto');
  if (file) file.addEventListener('change', async () => {
    const selected = file.files[0];
    try {
      const image = await photo('#sketchPhoto');
      if (image && file.isConnected && file.files[0] === selected) document.getElementById('sketchPreview').innerHTML = img(image);
    } catch { /* The existing upload workflow reports validation errors. */ }
  });
}

function newProjectDialog() {
  const dialog=document.createElement('dialog');
  dialog.className='record-dialog';dialog.setAttribute('aria-labelledby','newProjectTitle');
  dialog.innerHTML='<form><h2 id="newProjectTitle">新建作品</h2><label for="newProjectName">作品名称</label><input id="newProjectName" required maxlength="120" placeholder="例如：我的手机支架" autofocus><p id="newProjectError" role="status"></p><div class="actions"><button type="submit" class="primary">创建作品</button><button type="button" id="newProjectCancel">取消</button></div></form>';
  document.body.append(dialog);dialog.showModal();
  dialog.querySelector('#newProjectCancel').onclick=()=>dialog.close();
  dialog.addEventListener('close',()=>dialog.remove());
  dialog.querySelector('form').onsubmit=async event=>{
    event.preventDefault();const name=dialog.querySelector('input').value.trim();if(!name)return;
    const submit=dialog.querySelector('[type=submit]');submit.disabled=true;
    const previous=data,previousPage=page;let created;
    try{captureDraft();await save();created=fresh();created.name=name;created.goal=projectGoal(name);data=created;projects.push(created);await save();page='home';dialog.close();render();toast('新作品已创建');}
    catch(error){if(created)projects=projects.filter(p=>p!==created);data=previous;page=previousPage;dialog.querySelector('#newProjectError').textContent=error.message||'保存失败，请重试';submit.disabled=false;}
  };
}
