const state = {
  tab: "monitor",
  stream: null,
  imageUrl: null,
  scenario: "safe",
  rules: {
    goggles: true,
    handZone: true,
    crowding: true,
    hairClothing: false,
  },
  events: JSON.parse(localStorage.getItem("makerlens-events") || "[]"),
};

const scenarios = {
  safe: {
    level: "low",
    title: "未发现预设风险",
    message: "继续按教师示范和设备操作规程进行。系统不能证明现场绝对安全。",
    confidence: 88,
    boxes: [
      { x: 20, y: 13, w: 24, h: 22, label: "护目镜 0.94", type: "" },
      { x: 31, y: 48, w: 20, h: 27, label: "手部：安全区", type: "" },
    ],
  },
  goggles: {
    level: "high",
    title: "请停止操作并通知教师",
    message: "系统未识别到规定的眼部防护。先离开操作位置，由教师确认防护装备后再继续。",
    confidence: 91,
    rule: "未识别到护目镜",
    boxes: [
      { x: 21, y: 12, w: 24, h: 23, label: "未识别到护目镜 0.91", type: "risk" },
      { x: 31, y: 48, w: 20, h: 27, label: "手部", type: "" },
    ],
  },
  hand: {
    level: "high",
    title: "手部进入教师设定的警戒区",
    message: "立即停止当前动作并后退。摄像头只能判断二维位置，请由教师检查实际距离和设备状态。",
    confidence: 84,
    rule: "手部接近警戒区",
    boxes: [
      { x: 49, y: 49, w: 23, h: 29, label: "手部／警戒区 0.84", type: "risk" },
      { x: 43, y: 39, w: 34, h: 45, label: "教师设定区域", type: "warn" },
    ],
  },
  crowding: {
    level: "medium",
    title: "工作站人数超出设定值",
    message: "请非操作者退到等待线外，保持教师规定的工作站人数。",
    confidence: 79,
    rule: "工作站人数过多",
    boxes: [
      { x: 12, y: 18, w: 27, h: 61, label: "人员 1", type: "warn" },
      { x: 45, y: 15, w: 28, h: 64, label: "人员 2", type: "warn" },
      { x: 72, y: 20, w: 22, h: 58, label: "人员 3", type: "warn" },
    ],
  },
};

function nowTime() {
  return new Intl.DateTimeFormat("zh-Hans", { hour: "2-digit", minute: "2-digit", second: "2-digit", hour12: false }).format(new Date());
}

function saveEvents() {
  localStorage.setItem("makerlens-events", JSON.stringify(state.events.slice(0, 50)));
}

function addEvent(scenarioKey) {
  const s = scenarios[scenarioKey];
  if (!s.rule) return;
  const event = {
    id: crypto.randomUUID ? crypto.randomUUID() : String(Date.now()),
    time: nowTime(),
    station: "工作站 A-01",
    rule: s.rule,
    level: s.level,
    confidence: s.confidence,
    status: "待确认",
  };
  state.events.unshift(event);
  saveEvents();
}

function riskLabel(level) {
  return level === "high" ? "高优先提醒" : level === "medium" ? "需要关注" : "未发现预设风险";
}

function boxMarkup(box) {
  return `<div class="detect-box ${box.type}" style="left:${box.x}%;top:${box.y}%;width:${box.w}%;height:${box.h}%"><span>${box.label}</span></div>`;
}

function header() {
  return `
    <header class="topbar">
      <div class="brand"><div class="brand-mark">ML</div><div><h1>MakerLens Safety Lab</h1><p>AI辅助风险提醒原型</p></div></div>
      <nav class="nav" aria-label="主导航">
        <button data-tab="monitor" class="${state.tab === "monitor" ? "active" : ""}">工作站监控</button>
        <button data-tab="teacher" class="${state.tab === "teacher" ? "active" : ""}">教师总览</button>
        <button data-tab="design" class="${state.tab === "design" ? "active" : ""}">系统与课程</button>
      </nav>
      <div class="session"><span class="live-dot ${state.stream ? "on" : ""}"></span><span>${state.stream ? "摄像头已连接" : "演示模式"}</span><span>·</span><span>${nowTime()}</span></div>
    </header>`;
}

function monitorView() {
  const s = scenarios[state.scenario];
  const hasMedia = Boolean(state.imageUrl || state.stream);
  const media = state.imageUrl
    ? `<img src="${state.imageUrl}" alt="用户上传的测试画面" />`
    : `<video id="camera" autoplay playsinline muted ${state.stream ? "" : "hidden"}></video>`;
  return `
    <section class="page">
      <div class="view-head"><div><h2>工作站 A-01</h2><p>学生先按教师示范操作；系统只识别教师启用的可观察规则，并用“停止—退后—通知教师”作为高风险反馈。</p></div><span class="mode-badge">演示检测引擎 · 尚未用于真实安全决策</span></div>
      <div class="monitor-grid">
        <article class="card">
          <div class="card-head"><div><h3>实时画面</h3><small>原始画面默认不保存</small></div><small>720p · 本机预览</small></div>
          <div class="camera-wrap">
            ${media}
            ${!state.stream && !state.imageUrl ? `<div class="camera-empty"><div><strong>连接摄像头或上传测试图片</strong>学校平板只需浏览器摄像头权限，无须下载安装AI应用。</div></div>` : ""}
            <div class="camera-grid"></div>
            <i class="frame-corner tl"></i><i class="frame-corner tr"></i><i class="frame-corner bl"></i><i class="frame-corner br"></i>
            ${hasMedia ? s.boxes.map(boxMarkup).join("") : ""}
            <div class="camera-status"><span class="live-dot ${state.stream ? "on" : ""}"></span>${state.stream ? "实时画面" : "测试画面"} · ${riskLabel(s.level)}</div>
          </div>
          <div class="controlbar">
            <button class="btn primary" id="cameraBtn">${state.stream ? "停止摄像头" : "启动摄像头"}</button>
            <button class="btn" id="uploadBtn">上传测试图片</button>
            <input id="imageInput" type="file" accept="image/*" capture="environment" hidden />
            <select class="select" id="scenarioSelect" aria-label="选择演示情景">
              <option value="safe" ${state.scenario === "safe" ? "selected" : ""}>情景：符合预设规则</option>
              <option value="goggles" ${state.scenario === "goggles" ? "selected" : ""}>情景：未识别到护目镜</option>
              <option value="hand" ${state.scenario === "hand" ? "selected" : ""}>情景：手部接近警戒区</option>
              <option value="crowding" ${state.scenario === "crowding" ? "selected" : ""}>情景：工作站人数过多</option>
            </select>
            <button class="btn ghost" id="runBtn">运行演示分析</button>
          </div>
          <div class="helper">目前的框和置信度来自可控演示情景，不代表模型已能识别钻床或锯床操作。正式版须使用学校场景数据训练与验证，并由设备负责人定义规则。</div>
        </article>
        <aside class="side-stack">
          <article class="card risk-summary">
            <div class="risk-state"><div class="risk-icon ${s.level}">${s.level === "high" ? "!" : s.level === "medium" ? "△" : "✓"}</div><div><h3>${s.title}</h3><p>${riskLabel(s.level)}</p></div></div>
            <div class="alert-box"><h4>给学生的反馈</h4><p>${s.message}</p></div>
            <div class="confidence"><div class="confidence-line"><span>演示置信度</span><b>${s.confidence}%</b></div><div class="meter"><span style="width:${s.confidence}%;background:${s.level === "high" ? "var(--red)" : s.level === "medium" ? "var(--amber)" : "var(--mint)"}"></span></div></div>
            ${s.rule ? `<div class="action-row"><button class="btn small primary" id="correctedBtn">我已停止并通知教师</button><button class="btn small" id="whyBtn">为什么提醒我？</button></div>` : ""}
          </article>
          <article class="card">
            <div class="card-head"><h3>本机事件</h3><button class="btn small ghost" id="clearBtn">清空</button></div>
            <div class="events">${eventList(5)}</div>
          </article>
        </aside>
      </div>
    </section>`;
}

function eventList(limit = 50) {
  if (!state.events.length) return `<div class="empty-list">运行一个风险情景后，这里会记录事件元数据。</div>`;
  return state.events.slice(0, limit).map(e => `
    <div class="event"><span class="event-dot ${e.level}"></span><div><strong>${e.rule}</strong><p>${e.station} · ${e.confidence}% · ${e.status}</p></div><time>${e.time}</time></div>`).join("");
}

function teacherView() {
  const high = state.events.filter(e => e.level === "high").length;
  const medium = state.events.filter(e => e.level === "medium").length;
  const corrected = state.events.filter(e => e.status === "学生已停止，待教师确认").length;
  return `
    <section class="page">
      <div class="view-head"><div><h2>教师总览</h2><p>只呈现需要教师判断的事件，不把AI输出当作事故结论。默认记录时间、规则、置信度和处理状态，不保存连续视频。</p></div><button class="btn" id="exportBtn">导出事件记录</button></div>
      <div class="teacher-grid">
        <article class="card stat"><div class="stat-label">今日事件</div><div class="stat-value">${state.events.length}</div><div class="stat-note">浏览器本机演示数据</div></article>
        <article class="card stat"><div class="stat-label">高优先提醒</div><div class="stat-value" style="color:var(--red)">${high}</div><div class="stat-note">需要教师现场复核</div></article>
        <article class="card stat"><div class="stat-label">需要关注</div><div class="stat-value" style="color:var(--amber)">${medium}</div><div class="stat-note">不等于真实违规</div></article>
        <article class="card stat"><div class="stat-label">学生已响应</div><div class="stat-value" style="color:var(--mint)">${corrected}</div><div class="stat-note">仍需教师确认</div></article>
      </div>
      <div class="teacher-layout">
        <article class="card">
          <div class="card-head"><h3>风险事件记录</h3><small>最多保留50条本机记录</small></div>
          <div class="table-wrap"><table><thead><tr><th>时间</th><th>工作站</th><th>规则</th><th>等级</th><th>置信度</th><th>处理状态</th></tr></thead><tbody>
          ${state.events.length ? state.events.map(e => `<tr><td>${e.time}</td><td>${e.station}</td><td>${e.rule}</td><td><span class="pill ${e.level}">${e.level === "high" ? "高优先" : "关注"}</span></td><td>${e.confidence}%</td><td>${e.status}</td></tr>`).join("") : `<tr><td colspan="6" style="text-align:center;color:var(--muted);padding:34px">暂无事件。请在工作站监控页运行演示情景。</td></tr>`}
          </tbody></table></div>
        </article>
        <article class="card">
          <div class="card-head"><div><h3>本节课规则</h3><small>设备：演示工作站</small></div></div>
          <div class="rule-list">
            ${ruleRow("goggles","识别规定的眼部防护","由教师按任务要求启用")}
            ${ruleRow("handZone","手部接近教师设定区域","二维画面只能辅助提醒")}
            ${ruleRow("crowding","工作站人数超出上限","当前上限：2人")}
            ${ruleRow("hairClothing","长发／宽松衣物风险","需专门数据后才能测试")}
          </div>
          <div class="helper">不同设备的安全规则不能通用。例如旋转设备旁是否允许戴手套，应由学校设备规程和负责人决定，不能由AI自行推断。</div>
        </article>
      </div>
    </section>`;
}

function ruleRow(key, title, note) {
  return `<div class="rule"><div><strong>${title}</strong><span>${note}</span></div><button class="switch ${state.rules[key] ? "on" : ""}" data-rule="${key}" aria-label="${title}" aria-pressed="${state.rules[key]}"></button></div>`;
}

function designView() {
  return `
    <section class="page">
      <div class="view-head"><div><h2>系统设计与课程适配</h2><p>原型借鉴SiteGuard把“视觉模型”和“风险规则”分开的思路，并改造成面向学校Maker课堂的AI-supported学习系统。</p></div><span class="mode-badge">INT6065 Group Project 原型</span></div>
      <div class="design-grid">
        <article class="card flow"><div class="eyebrow">Learning loop</div><h3>AI不替学生操作，而是触发观察、解释、纠正与反思</h3><div class="flow-row">
          <div class="flow-step"><b>01</b><strong>教师定义规则</strong><p>按设备、任务和年级选择可观察风险。</p></div>
          <div class="flow-step"><b>02</b><strong>本机画面输入</strong><p>平板浏览器或固定摄像头提供画面。</p></div>
          <div class="flow-step"><b>03</b><strong>模型提出可能性</strong><p>检测对象与位置，不宣称理解全部情境。</p></div>
          <div class="flow-step"><b>04</b><strong>规则生成提醒</strong><p>高风险统一要求停止、退后并通知教师。</p></div>
          <div class="flow-step"><b>05</b><strong>学生与教师复核</strong><p>记录纠正、误报及规则改进证据。</p></div>
        </div></article>
        <article class="card info-card"><div class="eyebrow">AI concepts</div><h3>计算机视觉与可解释规则</h3><ul><li>目标检测：识别人员、防护装备和指定区域</li><li>置信度：表达模型不确定性</li><li>规则引擎：把检测结果转成分级提醒</li><li>人机协作：教师保留最终安全判断</li></ul></article>
        <article class="card info-card"><div class="eyebrow">Pedagogy</div><h3>保留学生的认知工作</h3><ul><li>学生先学习并复述安全规则</li><li>收到提醒后解释问题和纠正方法</li><li>识别AI误报与漏报，发展AI素养</li><li>用事件记录支持形成性反馈，而非惩罚排名</li></ul></article>
        <article class="card info-card"><div class="eyebrow">Feasibility</div><h3>学校平板兼容路径</h3><ul><li>优先使用浏览器，无需学生安装AI应用</li><li>原型可调用平板摄像头并上传测试图片</li><li>正式推理可改为校内电脑或边缘设备运行</li><li>最终兼容性仍需学校技术人员测试与批准</li></ul></article>
        <article class="card info-card"><div class="eyebrow">Ethics</div><h3>最小化影像与责任边界</h3><ul><li>默认不保存连续视频</li><li>只记录事件元数据和处理状态</li><li>不做人脸识别、身份推断或情绪识别</li><li>模型漏报不能视为“现场安全”</li></ul></article>
        <article class="card info-card"><div class="eyebrow">Evaluation</div><h3>原型需要怎样验证</h3><ul><li>技术：精确率、召回率、延迟和误报频率</li><li>教学：安全规则理解与反思质量</li><li>课堂：教师负担、干扰程度和可用性</li><li>公平：光线、肤色、衣着、遮挡和设备差异</li></ul></article>
        <article class="card info-card"><div class="eyebrow">Prototype scope</div><h3>第一版刻意不做什么</h3><ul><li>不连接或自动停止真实机器</li><li>不声称已经识别钻床操作意图</li><li>不把AI记录直接用于纪律处分</li><li>不在未审批情况下采集未成年人影像</li></ul></article>
        <div class="notice"><strong>课程边界：</strong>完整MakerLens系统适合INT6065，因为可说明AI概念、教学法、系统设计、教育价值、可行性、限制与伦理。它不直接满足INT6064“学生必须编写、测试和调试代码以发展计算思维”的核心要求，不能把同一个成品重复包装为两门课的作业。</div>
        <article class="card info-card" style="grid-column:1/-1"><div class="eyebrow">Open-source reference</div><h3>SiteGuard借鉴范围</h3><p>参考其摄像头传输、检测结果展示、模型与规则分离、风险日志和教师端界面结构。建筑工地PPE模型不能直接证明适用于学校钻床或锯床场景；正式版必须重新定义类别、收集经批准的数据并验证。参考：<a class="source-link" href="https://github.com/C-Nekopedia/SiteGuard" target="_blank" rel="noreferrer">C-Nekopedia/SiteGuard（MIT）</a>。</p></article>
      </div>
    </section>`;
}

function render() {
  const app = document.querySelector("#app");
  app.setAttribute("aria-busy", "false");
  app.innerHTML = `<div class="app-shell">${header()}${state.tab === "monitor" ? monitorView() : state.tab === "teacher" ? teacherView() : designView()}</div><div class="toast" id="toast"></div>`;
  bindEvents();
  if (state.stream) {
    const video = document.querySelector("#camera");
    if (video) video.srcObject = state.stream;
  }
}

function toast(message) {
  const el = document.querySelector("#toast");
  if (!el) return;
  el.textContent = message;
  el.classList.add("show");
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => el.classList.remove("show"), 2800);
}

async function toggleCamera() {
  if (state.stream) {
    state.stream.getTracks().forEach(t => t.stop());
    state.stream = null;
    render();
    return;
  }
  try {
    state.stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: "environment" }, width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false });
    if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
    state.imageUrl = null;
    render();
    toast("摄像头已连接。画面只在本机预览。 ");
  } catch (error) {
    toast("无法打开摄像头，请检查浏览器权限或改用上传图片。 ");
  }
}

function runScenario() {
  if (state.scenario !== "safe") addEvent(state.scenario);
  render();
  toast(state.scenario === "safe" ? "演示分析完成：未发现已启用规则中的风险。" : "已生成辅助提醒，并写入本机事件记录。 ");
}

function bindEvents() {
  document.querySelectorAll("[data-tab]").forEach(btn => btn.addEventListener("click", () => { state.tab = btn.dataset.tab; render(); }));
  document.querySelector("#cameraBtn")?.addEventListener("click", toggleCamera);
  document.querySelector("#uploadBtn")?.addEventListener("click", () => document.querySelector("#imageInput")?.click());
  document.querySelector("#imageInput")?.addEventListener("change", e => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (state.stream) state.stream.getTracks().forEach(t => t.stop());
    state.stream = null;
    if (state.imageUrl) URL.revokeObjectURL(state.imageUrl);
    state.imageUrl = URL.createObjectURL(file);
    render();
    toast("测试图片仅在当前浏览器中显示，没有上传到服务器。 ");
  });
  document.querySelector("#scenarioSelect")?.addEventListener("change", e => { state.scenario = e.target.value; render(); });
  document.querySelector("#runBtn")?.addEventListener("click", runScenario);
  document.querySelector("#clearBtn")?.addEventListener("click", () => { state.events = []; saveEvents(); render(); toast("本机演示记录已清空。 "); });
  document.querySelector("#correctedBtn")?.addEventListener("click", () => {
    const item = state.events.find(e => e.rule === scenarios[state.scenario].rule && e.status === "待确认");
    if (item) item.status = "学生已停止，待教师确认";
    saveEvents();
    render();
    toast("已记录学生响应；教师仍需现场确认。 ");
  });
  document.querySelector("#whyBtn")?.addEventListener("click", () => toast("AI根据画面目标和教师启用的规则提出可能风险；它无法确认设备状态或学生意图。 "));
  document.querySelectorAll("[data-rule]").forEach(btn => btn.addEventListener("click", () => { const key = btn.dataset.rule; state.rules[key] = !state.rules[key]; render(); }));
  document.querySelector("#exportBtn")?.addEventListener("click", () => {
    const payload = { exportedAt: new Date().toISOString(), prototype: true, note: "AI事件需由教师复核，不是事故结论", events: state.events };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `makerlens-events-${new Date().toISOString().slice(0,10)}.json`;
    link.click();
    setTimeout(() => URL.revokeObjectURL(link.href), 1000);
  });
}

render();
setInterval(() => {
  const session = document.querySelector(".session span:last-child");
  if (session) session.textContent = nowTime();
}, 1000);

window.addEventListener("beforeunload", () => state.stream?.getTracks().forEach(t => t.stop()));
