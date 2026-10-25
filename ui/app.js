'use strict';
const icons = {
  network:'<rect x="7" y="2" width="10" height="6" rx="1.5"/><path d="M12 8v5M4 17v-4h16v4"/><rect x="1" y="17" width="6" height="5" rx="1"/><rect x="9" y="17" width="6" height="5" rx="1"/><rect x="17" y="17" width="6" height="5" rx="1"/>',
  dashboard:'<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  server:'<rect x="3" y="3" width="18" height="7" rx="2"/><rect x="3" y="14" width="18" height="7" rx="2"/><path d="M7 6.5h.01M7 17.5h.01M16 6.5h2M16 17.5h2"/>',
  activity:'<path d="M2 12h4l3-8 5 16 3-8h5"/>',
  folder:'<path d="M3 6a2 2 0 0 1 2-2h5l2 3h7a2 2 0 0 1 2 2v10a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2Z"/><path d="M3 10h18"/>',
  sliders:'<path d="M4 4v5m0 4v7M12 4v9m0 4v3M20 4v1m0 4v11M1 9h6M9 17h6M17 5h6"/>',
  shield:'<path d="m12 2 8 4v6c0 5-8 10-8 10S4 17 4 12V6Z"/><path d="m8 12 3 3 5-6"/>',
  'arrow-up-right':'<path d="M7 17 17 7M7 7h10v10"/>',
  'arrow-right':'<path d="M4 12h16m-6-6 6 6-6 6"/>',
  'chevron-right':'<path d="m9 5 7 7-7 7"/>',
  'chevron-left':'<path d="m15 5-7 7 7 7"/>',
  monitor:'<rect x="3" y="3" width="18" height="13" rx="2"/><path d="M8 21h8m-4-5v5"/>',
  panel:'<rect x="3" y="3" width="18" height="18" rx="2"/><path d="M9 3v18"/>',
  help:'<circle cx="12" cy="12" r="9"/><path d="M9.5 9a2.5 2.5 0 0 1 5 .5c0 1.7-2.5 2-2.5 4M12 17h.01"/>',
  flask:'<path d="M9 3h6m-5 0v7L4 19a1.5 1.5 0 0 0 1.3 2h13.4a1.5 1.5 0 0 0 1.3-2l-6-9V3M7 15h10"/>',
  upload:'<path d="M12 16V3m-5 5 5-5 5 5M4 15v5a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-5"/>',
  download:'<path d="M12 3v13m-5-5 5 5 5-5M4 16v4a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-4"/>',
  play:'<path d="m8 4 12 8-12 8Z"/>',
  lock:'<rect x="5" y="10" width="14" height="11" rx="2"/><path d="M8 10V7a4 4 0 0 1 8 0v3M12 14v3"/>',
  check:'<path d="m5 12 4 4L19 6"/>',
  circlecheck:'<circle cx="12" cy="12" r="9"/><path d="m8 12 3 3 6-7"/>',
  warning:'<path d="m10.3 4-8 14a2 2 0 0 0 1.7 3h16a2 2 0 0 0 1.7-3l-8-14a2 2 0 0 0-3.4 0ZM12 9v4M12 17h.01"/>',
  disconnect:'<path d="M5 3v5m4-5v5M3 8h8v3a4 4 0 0 1-4 4v6m9-7 6 6m0-6-6 6"/>',
  plus:'<path d="M12 5v14M5 12h14"/>',
  search:'<circle cx="10.5" cy="10.5" r="6.5"/><path d="m16 16 5 5"/>',
  filter:'<path d="M3 5h18l-7 8v6l-4 2v-8Z"/>',
  more:'<circle cx="5" cy="12" r="1"/><circle cx="12" cy="12" r="1"/><circle cx="19" cy="12" r="1"/>',
  cpu:'<rect x="6" y="6" width="12" height="12" rx="2"/><rect x="9" y="9" width="6" height="6" rx="1"/><path d="M9 2v4m6-4v4M9 18v4m6-4v4M2 9h4m-4 6h4M18 9h4m-4 6h4"/>',
  memory:'<rect x="3" y="6" width="18" height="12" rx="1"/><path d="M7 10v4m5-4v4m5-4v4M6 18v3m4-3v3m4-3v3m4-3v3"/>',
  fan:'<circle cx="12" cy="12" r="2"/><path d="M10 10C3 6 10 0 13 5l1 5m0 2c7-3 9 5 3 6l-4-3m-3-1c0 8-8 6-7 1l5-3"/>',
  file:'<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Zm0 0v6h6M8 13h8M8 17h6"/>',
  clock:'<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  info:'<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  close:'<path d="m6 6 12 12M6 18 18 6"/>',
  edit:'<path d="m16 3 5 5-12 12-6 1 1-6ZM13 6l5 5"/>',
  trash:'<path d="M3 6h18M9 6V3h6v3M5 6l1 15h12l1-15M10 10v7m4-7v7"/>',
  stop:'<rect x="6" y="6" width="12" height="12" rx="1"/>',
  refresh:'<path d="M20 8a8 8 0 0 0-14-3L3 8m0-5v5h5M4 16a8 8 0 0 0 14 3l3-3m0 5v-5h-5"/>',
};
const $ = (s, root=document) => root.querySelector(s);
const $$ = (s, root=document) => [...root.querySelectorAll(s)];
const esc = value => String(value ?? '').replace(/[&<>"']/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
const icon = name => `<svg viewBox="0 0 24 24" aria-hidden="true">${icons[name] || icons.info}</svg>`;
function hydrate(root=document){$$('[data-icon]', root).forEach(el=>{el.innerHTML=icon(el.dataset.icon);});}
const labels = {ok:'正常',warn:'需关注',fail:'采集失败',unknown:'待核实',idle:'未巡检',running:'采集中',cancelled:'已取消',done:'已完成',cancelling:'正在取消',error:'保存失败'};
const vendorLabel = vendor => vendor==='huawei'?'华为 / VRP':vendor==='hp_comware'?'H3C / Comware':'未指定';
const supportedVendor = vendor => vendor==='huawei' || vendor==='hp_comware';
const pill = status => `<span class="status-pill ${esc(status)}"><i></i>${labels[status] || '未巡检'}</span>`;
const shortTime = iso => iso ? new Date(iso).toLocaleTimeString('zh-CN',{hour:'2-digit',minute:'2-digit',hour12:false}) : '—';
const fullDate = iso => iso ? new Date(iso).toLocaleString('zh-CN',{hour12:false}) : '—';
const nowISO = () => new Date().toISOString();

const analysisPresets = Object.fromEntries(['huawei','hp_comware'].map(v=>[v,['display environment','display interface brief',v==='huawei'?'display alarm active':'display alarm',v==='huawei'?'display logbuffer':'display logbuffer reverse','display counters errors inbound','display counters errors outbound']]));
const demoDefaults = {huawei:['display current-configuration','display cpu-usage','display memory-usage','display device',...analysisPresets.huawei],hp_comware:['display current-configuration','display cpu-usage summary','display memory','display fan','display power',...analysisPresets.hp_comware]};
function demoData(){
  const names=['HQ-CORE-SW01','HQ-CORE-SW02','HQ-AGG-SW01','HQ-AGG-SW02','OFFICE-ACC-01','OFFICE-ACC-02','IDC-TOR-SW01','IDC-TOR-SW02','BRANCH-SW01','BRANCH-SW02','LAB-SW01','LAB-SW02'];
  const cpus=[12,18,86,8,23,null,32,14,16,9,11,22], memories=[36,42,68,31,45,null,51,41,33,39,21,44];
  const assets=names.map((name,i)=>{
    const status=i===2?'warn':i===5?'fail':'ok', host=`192.168.${i<8?'10':'20'}.${i%8+1}`, vendor=i%3===1?'hp_comware':'huawei';
    const collected=new Date(Date.now()-1000*60*(5+i)).toISOString();
    return {name,host,vendor,port:22,group:i<4?'总部 · 核心网络':i<6?'总部 · 办公网络':i<8?'数据中心':'分支与实验室',result:{host,name,vendor,status,collected,metrics:{cpu:cpus[i],memory:memories[i],fanpower:{found:true,units:[{name:'FAN1',state:'Normal'},{name:'PWR1',state:'Normal'}]}},error:status==='fail'?'SSH 连接超时，请检查管理地址与网络连通性':''}};
  });
  return {assets, history:[{id:'demo-run',started:new Date(Date.now()-15*60000).toISOString(),state:'done',count:12,total:12,ok:10,warn:1,fail:1,results:assets.map(a=>a.result)}],run:{state:'idle',total:0,completed:0,results:[],logs:[],active:[]},commands:Object.fromEntries(Object.entries(demoDefaults).map(([v,commands])=>[v,commands.map(command=>({command,enabled:true}))])),analysis_commands:analysisPresets,data_dir:'演示工作空间（不会保存真实资产）'};
}

const app = {
  page:'dashboard',demo:new URLSearchParams(location.search).get('demo')==='1',
  data:{assets:[],history:[],commands:{huawei:[],hp_comware:[]},run:{state:'idle',total:0,completed:0,results:[],logs:[],active:[]}},
  selected:new Set(),query:'',vendor:'all',status:'all',group:'all',pageIndex:1,
  defaults:{vendor:'huawei',username:'',password:'',port:22,group:'未分组',workers:5},busy:false,initialized:false,polling:false,
  async call(method,...args){
    if(this.demo) return this.demoCall(method,...args);
    if(!window.pywebview?.api) throw new Error('浏览器中仅支持界面演示，请使用桌面应用操作真实设备。');
    const result=await window.pywebview.api[method](...args);
    if(result?.error) throw new Error(result.error);
    return result;
  },
  async refresh(render=true){
    if(this.polling) return;
    this.polling=true;
    try{
      if(!this.demo) this.data=await this.call('snapshot');
      const hosts=new Set(this.data.assets.map(a=>a.host));
      this.selected=new Set([...this.selected].filter(h=>hosts.has(h)));
      if(render) this.render();
    }catch(e){this.toast(e.message);}
    finally{this.polling=false;}
  },
  get running(){return ['running','cancelling'].includes(this.data.run.state);},
  get stats(){
    const rows=this.data.assets.map(a=>a.result);
    return {total:rows.length,ok:rows.filter(a=>a?.status==='ok').length,warn:rows.filter(a=>['warn','unknown'].includes(a?.status)).length,fail:rows.filter(a=>a?.status==='fail').length,idle:rows.filter(a=>!a).length};
  },
  navigate(page){
    if(!['dashboard','assets','tasks','reports','settings'].includes(page)) page='dashboard';
    this.page=page;this.pageIndex=1;this.query='';this.vendor='all';this.status='all';this.group='all';
    history.replaceState(null,'',`${location.pathname}${location.search}#${page}`);
    this.render();
  },
  render(){
    const titles={dashboard:['巡检工作台','交换机状态与最近巡检结果。',''],assets:['资产管理','华为 VRP 与 H3C Comware 设备。',''],tasks:['巡检任务','查看采集进度与执行结果。',''],reports:['报告与归档','历史结果及设备配置文件。',''],settings:['巡检设置','并发数与网段默认凭据。','']};
    const [title,description,eyebrow]=titles[this.page];
    $('#page-title').textContent=title;$('#breadcrumb-title').textContent=title;$('#page-description').textContent=description;$('#eyebrow').textContent=eyebrow;
    $$('.nav-item').forEach(el=>{el.classList.toggle('active',el.dataset.nav===this.page);el.setAttribute('aria-current',el.dataset.nav===this.page?'page':'false');});
    $('#nav-count').textContent=this.data.assets.length;$('#demo-banner').hidden=!this.demo;$('#running-dot').hidden=!this.running;
    $('#start-button').disabled=this.running;
    $('#start-button').innerHTML=icon(this.running?'activity':'play')+(this.running?'巡检进行中':'开始巡检')+'<span class="key-hint">↵</span>';
    $('#heading-secondary').innerHTML=icon(this.page==='reports'?'refresh':this.page==='settings'?'help':'upload')+(this.page==='reports'?'刷新记录':this.page==='settings'?'使用帮助':'导入资产');
    $('#status-label').textContent=this.demo?'演示模式 · 不连接真实设备':this.running?`采集进度 ${this.data.run.completed} / ${this.data.run.total}`:'工作空间已就绪';
    $('#footer-time').textContent=new Date().toLocaleDateString('zh-CN',{year:'numeric',month:'2-digit',day:'2-digit',weekday:'long'});
    $('#stats-grid').hidden=!['dashboard','assets'].includes(this.page);
    $('#stats-grid').style.display=['dashboard','assets'].includes(this.page)?'grid':'none';
    this.renderStats();
    const content=$('#page-content');
    if(this.page==='dashboard') content.innerHTML=`<div class="workspace-grid"><div>${this.tableMarkup()}${this.activityMarkup()}</div><aside class="side-stack" aria-label="巡检辅助信息">${this.healthMarkup()}${this.scopeMarkup()}</aside></div>`;
    if(this.page==='assets') content.innerHTML=this.tableMarkup(true);
    if(this.page==='tasks') content.innerHTML=this.tasksMarkup();
    if(this.page==='reports') content.innerHTML=this.reportsMarkup();
    if(this.page==='settings') content.innerHTML=this.settingsMarkup();
    this.bindPage();hydrate(content);
    if(this.page==='reports'&&this.data.history.length)this.loadReport();
  },
  renderStats(){
    const s=this.stats;
    const cards=[['资产总数',s.total,'server','',this.demo?'2 个网段 · 4 个设备分组':`${new Set(this.data.assets.map(a=>a.group)).size} 个设备分组 · 华为 / H3C`],['运行正常',s.ok,'circlecheck','good',s.ok?'最近采集状态正常':'等待设备状态采集'],['需要关注',s.warn,'warning','warn',s.warn?'含指标告警与待核实项':'当前没有指标告警'],['采集失败',s.fail,'disconnect','bad',s.fail?'检查设备连接与访问凭据':'当前没有失败的采集']];
    $('#stats-grid').innerHTML=cards.map(([label,value,i,cls,caption])=>`<article class="stat-card ${cls}"><div class="stat-top"><span>${label}</span><span class="stat-icon">${icon(i)}</span></div><div class="stat-value">${value}<small>台</small></div><div class="stat-caption">${cls?'<i></i>':''}${esc(caption)}</div></article>`).join('');
  },
  filtered(){
    const q=this.query.toLowerCase();
    return this.data.assets.filter(a=>(!q||[a.name,a.host,a.group].some(v=>v.toLowerCase().includes(q)))&&(this.vendor==='all'||a.vendor===this.vendor)&&(this.status==='all'||(a.result?.status||'idle')===this.status)&&(this.group==='all'||a.group===this.group));
  },
  tableMarkup(extended=false){
    const groups=[...new Set(this.data.assets.map(a=>a.group))];
    return `<section class="card asset-card" aria-label="设备列表"><div class="card-titlebar"><div class="card-title"><h2>设备清单</h2><span class="count-pill">${this.data.assets.length} 台设备</span></div><div class="card-actions"><button class="text-action" id="template-button">${icon('download')}下载模板</button><button class="button small" id="add-button">${icon('plus')}添加设备</button></div></div><div class="table-toolbar"><label class="searchbox"><span>${icon('search')}</span><input id="asset-search" type="search" placeholder="搜索设备名称、IP 地址或分组..." aria-label="搜索设备" value="${esc(this.query)}"><kbd class="shortcut">/</kbd></label><select id="vendor-filter" class="filter-select" aria-label="按厂商筛选"><option value="all">全部厂商</option><option value="huawei" ${this.vendor==='huawei'?'selected':''}>华为</option><option value="hp_comware" ${this.vendor==='hp_comware'?'selected':''}>H3C</option><option value="" ${this.vendor===''?'selected':''}>未指定</option></select><select id="status-filter" class="filter-select" aria-label="按状态筛选">${[['all','全部状态'],['ok','正常'],['warn','需关注'],['unknown','待核实'],['fail','采集失败'],['idle','未巡检']].map(([v,l])=>`<option value="${v}" ${this.status===v?'selected':''}>${l}</option>`).join('')}</select>${extended?`<select id="group-filter" class="filter-select" aria-label="按分组筛选"><option value="all">全部分组</option>${groups.map(g=>`<option ${this.group===g?'selected':''}>${esc(g)}</option>`).join('')}</select>`:''}</div><div id="table-inner">${this.tableBodyMarkup()}</div></section>`;
  },
  tableBodyMarkup(){
    const rows=this.filtered(), visible=rows;
    this.visible=visible;
    const metric=(value)=>value==null?'<span class="metric-value">—</span>':`<span class="metric-value ${value>=80?'hot':''}">${Number(value)}<span style="font-size:9px">%</span></span><div class="mini-bar"><span class="${value>=80?'hot':''}" style="width:${Math.max(0,Math.min(100,Number(value)))}%"></span></div>`;
    let body;
    if(!rows.length) body=`<div class="empty-state"><span>${icon(this.data.assets.length?'search':'server')}</span><h3>${this.data.assets.length?'没有匹配的设备':'从第一台交换机开始'}</h3><p>${this.data.assets.length?'尝试调整搜索关键词，或清除筛选条件。':'添加单台设备、批量导入 IP 网段，或从 Excel 导入资产。<br>配置好连接凭据，即可开始只读巡检。'}</p><div class="empty-actions">${this.data.assets.length?'<button class="button" id="clear-filters">清除筛选</button>':`<button class="button primary" id="empty-add">${icon('plus')}添加设备</button><button class="button" id="enter-demo">${icon('flask')}体验演示工作空间</button>`}</div></div>`;
    else body=`<div class="table-scroll"><table><thead><tr><th><input type="checkbox" id="select-all" aria-label="选择本页全部设备" ${visible.length&&visible.every(a=>this.selected.has(a.host))?'checked':''}></th><th>设备名称 / 分组</th><th>IP 地址</th><th>厂商</th><th>状态</th><th>CPU</th><th>内存</th><th class="time-col">最近巡检</th><th aria-label="操作"></th></tr></thead><tbody>${visible.map(a=>{
      const r=a.result,m=r?.metrics||{},status=this.data.run.active?.includes(a.host)?'running':r?.status||'idle';
      return `<tr class="${this.selected.has(a.host)?'selected':''}"><td><input type="checkbox" data-select="${esc(a.host)}" aria-label="选择 ${esc(a.name)}" ${this.selected.has(a.host)?'checked':''}></td><td><div class="device-cell"><span class="device-icon">${icon('server')}</span><div><button class="device-name" data-detail="${esc(a.host)}">${esc(a.name)}</button><div class="device-group">${esc(a.group)}</div></div></div></td><td class="mono">${esc(a.host)}</td><td><span class="vendor ${a.vendor==='hp_comware'?'h3c':''}">${vendorLabel(a.vendor)}</span></td><td>${pill(status)}</td><td class="metric-cell">${metric(m.cpu)}</td><td class="metric-cell">${metric(m.memory)}</td><td class="time-cell time-col">${r?'最近 '+shortTime(r.collected):'尚未巡检'}</td><td><button class="icon-button" data-menu="${esc(a.host)}" aria-label="${esc(a.name)} 的操作" title="设备操作">${icon('more')}</button></td></tr>`;
    }).join('')}</tbody></table></div>`;
    return body+`${this.selected.size?`<div class="selection-bar"><span>已选择 ${this.selected.size} 台设备</span><button class="text-action accent" id="inspect-selected">${icon('play')}巡检所选</button><button class="text-action" id="delete-selected">${icon('trash')}删除</button><button class="text-action" id="clear-selection">取消选择</button></div>`:''}<div class="table-bottom"><span>${rows.length?`共 ${rows.length} 台设备`:'暂无设备'}${this.selected.size?` · 已选 ${this.selected.size} 台`:''}</span><span class="table-note">筛选结果已全部显示，可在表格内滚动查看</span></div>`;
  },
  refreshTable(){
    if(!$('#table-inner')) return;
    $('#table-inner').innerHTML=this.tableBodyMarkup();this.bindTable();
  },
  healthMarkup(){
    const s=this.stats, inspected=s.ok+s.warn+s.fail, rate=inspected?Math.round(s.ok/inspected*100):0, warnings=inspected?(s.ok+s.warn)/inspected*100:0;
    return `<section class="card side-card"><div class="card-titlebar"><h2>设备健康概览</h2><span class="tag">最近巡检</span></div><div class="health-display"><div class="donut" style="--percent:${rate};--warn-percent:${warnings}"><div class="donut-content"><strong>${inspected?rate:'—'}${inspected?'<small>%</small>':''}</strong><span>设备健康率</span></div></div><div class="health-legend"><div><span class="legend-label"><i class="legend-dot"></i>正常</span><strong>${s.ok}</strong></div><div><span class="legend-label"><i class="legend-dot warn"></i>关注</span><strong>${s.warn}</strong></div><div><span class="legend-label"><i class="legend-dot fail"></i>失败</span><strong>${s.fail}</strong></div></div></div><div class="side-note">${icon('clock')}${inspected?`基于 ${inspected} 台设备的最近采集结果`:'完成首次巡检后生成健康概览'}</div></section>`;
  },
  scopeMarkup(){
    return `<section class="card side-card"><div class="card-titlebar"><h2>本次采集范围</h2><span>${icon('shield')}</span></div><div class="scope-list">${[['cpu','CPU 使用率'],['memory','内存使用率'],['fan','风扇 / 电源状态'],['file','设备全量配置']].map(([i,l])=>`<div class="scope-row"><span>${icon(i)}${l}</span><span>${icon('circlecheck')}</span></div>`).join('')}</div><div class="scope-footer"><span>支持设备</span><div class="vendor-logos"><strong>HUAWEI</strong><strong>H3C</strong></div></div></section>`;
  },
  activityMarkup(){
    const history=this.data.history.slice(0,2);
    let rows;
    if(this.running) rows=`<div class="activity-row"><span class="activity-icon">${icon('activity')}</span><div class="activity-text">巡检正在进行<small>已采集 ${this.data.run.completed} / ${this.data.run.total} 台 · 并发 ${this.data.run.workers}</small></div><button class="text-action accent" id="activity-task">查看进度 ${icon('arrow-right')}</button></div>`;
    else if(history.length) rows=history.map((run,i)=>`<div class="activity-row"><span class="activity-icon ${run.fail?'warn':''}">${icon(run.fail?'warning':'circlecheck')}</span><div class="activity-text">${this.demo?'示例巡检任务':run.state==='cancelled'?'巡检任务已取消':'巡检任务已完成'}<small>${run.count} 台设备 · ${run.ok} 台正常${run.warn?` · ${run.warn} 台需关注`:''}${run.fail?` · ${run.fail} 台采集失败`:''}</small></div><span class="activity-time">${shortTime(run.started)}</span><button class="icon-button" data-report="${esc(run.id)}" aria-label="查看此次报告">${icon('arrow-up-right')}</button></div>`).join('');
    else rows=`<div class="activity-row"><span class="activity-icon">${icon('shield')}</span><div class="activity-text">工作空间已就绪<small>添加设备后，开始你的第一次只读巡检。</small></div><span class="tag">等待首次巡检</span></div>`;
    if(this.demo && !this.running) rows+=`<div class="activity-row"><span class="activity-icon">${icon('file')}</span><div class="activity-text">示例配置归档已就绪<small>HTML 报告、JSON 结果及逐设备配置，可按任务统一查看。</small></div><button class="text-action" id="activity-archive">查看归档 ${icon('arrow-right')}</button></div>`;
    return `<section class="card activity-card"><div class="card-titlebar"><h2>最近动态</h2><button class="text-action" id="all-tasks">全部任务 ${icon('arrow-right')}</button></div><div class="activity-list">${rows}</div></section>`;
  },
  tasksMarkup(){
    const r=this.data.run,active=r.state!=='idle',pct=r.total?Math.round(r.completed/r.total*100):0;
    if(!active) return `<section class="card"><div class="empty-state"><span>${icon('activity')}</span><h3>准备好，开始一次巡检</h3><p>选择设备后启动任务，实时查看每台设备的采集进度。<br>历史任务与输出文件可在报告与归档中查看。</p><div class="empty-actions"><button class="button primary" id="task-start">${icon('play')}开始巡检</button><button class="button" id="to-reports">查看历史记录</button></div></div></section>`;
    return `<section class="card task-card"><div class="task-top"><div><h2>${this.demo?'演示巡检任务':'设备批量巡检'} ${pill(r.state)}</h2><p>${esc(r.id)} · ${fullDate(r.started)} · 并发 ${r.workers} 台</p></div><div class="card-actions">${this.running?`<button class="button danger" id="cancel-task" ${r.state==='cancelling'?'disabled':''}>${icon('stop')}${r.state==='cancelling'?'等待当前会话结束':'取消任务'}</button>`:`<button class="button" id="to-reports">${icon('folder')}查看归档</button>`}</div></div><div class="progress-track"><span style="width:${pct}%"></span></div><div class="progress-label"><span>已完成 ${r.completed} / ${r.total} 台${r.state==='cancelled'?` · 未派发 ${r.total-r.completed} 台`:''}</span><span>${pct}%</span></div>${r.error?`<p class="result-error">${esc(r.error)}</p>`:''}<div class="task-logs" role="log" aria-label="采集日志"><div class="log-line"><span>${shortTime(r.started)}</span><span>${this.demo?'[DEMO] ':' '}任务已创建，等待设备返回采集结果。</span></div>${r.logs.map(log=>`<div class="log-line"><span>${esc(log.time)}</span><span class="${esc(log.status)}">${esc(log.host)}</span><span>${labels[log.status]} · ${esc(log.message)}</span></div>`).join('')}${this.running?'<div class="log-line"><span>···</span><span>等待当前设备会话返回结果</span></div>':''}${r.finished?`<div class="log-line"><span>${shortTime(r.finished)}</span><span>任务${r.state==='cancelled'?'已取消':'已结束'}，已返回结果完成归档。</span></div>`:''}</div>${this.commandConsoleMarkup(r)}<p class="dialog-note">取消任务会停止派发新设备；已建立的设备会话正常结束后释放连接。</p></section>`;
  },
  commandConsoleMarkup(r){
    const slots=Array.isArray(r.consoles)?r.consoles:[];
    if(!slots.length)return '';
    const statusText={idle:'等待设备',queued:'准备连接',connecting:'连接中',running:'执行中',complete:'命令完成',done:'设备完成',fail:'执行失败'};
    return `<section class="command-console" aria-label="命令执行窗口"><div class="console-heading"><div><h3>命令执行窗口</h3><p>每个窗口对应一个并发线程，实时显示当前命令输出。</p></div><span class="tag">${slots.length} 个线程</span></div><div class="console-grid">${slots.map((slot,index)=>{const state=slot.status||'idle';return `<article class="console-pane"><div class="console-pane-head"><span class="console-thread">线程 ${slot.slot||index+1}${slot.transport?` · ${esc(slot.transport.toUpperCase())}`:''}</span><span class="console-state ${esc(state)}">${statusText[state]||esc(state)}</span></div><div class="console-device">${slot.name?esc(slot.name)+' · ':''}${esc(slot.host||'等待分配设备')}</div><div class="console-command">${slot.command?`<code>${esc(slot.command)}</code>`:'等待命令'}</div><pre class="console-output">${esc(slot.output||'等待设备输出…')}</pre>${slot.error?`<p class="result-error" style="margin:8px 10px">${esc(slot.error)}</p>`:''}<div class="console-time">${slot.updated?`更新于 ${shortTime(slot.updated)}`:'尚未开始'}</div></article>`;}).join('')}</div></section>`;
  },
  reportsMarkup(){
    const rows=this.data.history;
    if(!rows.length) return `<section class="card"><div class="empty-state"><span>${icon('folder')}</span><h3>这里将保存每一次巡检</h3><p>任务完成后，自动生成 HTML 巡检报告、JSON 结果<br>以及按设备 IP 命名的完整配置归档。</p><button class="button primary" id="task-start">${icon('play')}开始首次巡检</button></div></section>`;
    if(!rows.some(r=>r.id===this.reportId))this.reportId=rows[0].id;
    const selector=`<div class="card report-selector-bar"><label for="report-select">选择巡检任务</label><select id="report-select">${rows.map(r=>`<option value="${esc(r.id)}" ${r.id===this.reportId?'selected':''}>${fullDate(r.started)} · ${r.count}/${r.total} 台 · ${labels[r.state]||'已完成'}</option>`).join('')}</select><div class="card-actions"><button class="button small" id="report-html">${icon('file')}离线 HTML</button><button class="button small" data-folder="${esc(this.reportId)}">${icon('folder')}归档目录</button></div></div><div id="report-view" aria-live="polite"><p class="dialog-note">正在读取巡检分析…</p></div>`;
    return selector+`<section class="card report-history"><div class="card-titlebar"><div class="card-title"><h2>巡检归档</h2><span class="count-pill">${rows.length} 次巡检</span></div><span class="tag">仅保存在本机</span></div><div class="table-scroll"><table class="archive-table"><thead><tr><th>巡检任务</th><th>任务状态</th><th>设备数量</th><th>正常 / 关注 / 失败</th><th>输出文件</th><th>操作</th></tr></thead><tbody>${rows.map(r=>`<tr><td><div class="report-name">${this.demo?'示例设备巡检':'设备批量巡检'}</div><div class="archive-meta">${fullDate(r.started)}</div></td><td>${pill(r.state)}</td><td class="mono">${r.count} / ${r.total}</td><td><span style="color:var(--accent)">${r.ok}</span> <span style="color:#aab8bd">/</span> <span style="color:var(--warn)">${r.warn}</span> <span style="color:#aab8bd">/</span> <span style="color:var(--danger)">${r.fail}</span></td><td><span class="archive-meta">HTML · JSON · TXT</span></td><td><div class="card-actions"><button class="button small" data-report="${esc(r.id)}">${icon('file')}报告</button><button class="icon-button" data-folder="${esc(r.id)}" aria-label="打开归档目录">${icon('folder')}</button></div></td></tr>`).join('')}</tbody></table></div><div class="side-note">${icon('lock')}配置归档可能包含设备敏感配置，请妥善保管输出文件。</div></section>`;
  },
  settingsMarkup(){
    const d=this.defaults;
    const commandPanel=(vendor,label)=>{const rows=this.data.commands?.[vendor]||[];return `<section class="command-panel" data-command-panel="${vendor}"><div class="command-panel-head"><div><h3>${label}</h3><p>按顺序执行；仅允许单行 display / show 命令。</p></div><button type="button" class="button small" data-command-add="${vendor}">${icon('plus')}新增命令</button></div><div class="command-list">${rows.map((row,i)=>`<div class="command-row" data-command-row><input class="command-input" value="${esc(row.command)}" maxlength="240" aria-label="${label}命令 ${i+1}"><label class="command-enabled"><input type="checkbox" ${row.enabled?'checked':''}>启用</label><button type="button" class="icon-button" data-command-up aria-label="上移命令">↑</button><button type="button" class="icon-button" data-command-down aria-label="下移命令">↓</button><button type="button" class="icon-button" data-command-delete aria-label="删除命令">${icon('trash')}</button></div>`).join('')}</div><div class="settings-actions"><button type="button" class="button primary" data-command-save="${vendor}">${icon('check')}保存${label}命令</button><button type="button" class="button" data-command-supplement="${vendor}">补充分析命令</button><button type="button" class="button" data-command-reset="${vendor}">恢复默认</button></div></section>`;};
    return `<form id="settings-form" class="card settings-card"><h2>采集偏好</h2><p>登录后先识别设备版本，再按实际平台执行命令。</p><div class="form-grid"><label class="field"><span>最大并发数</span><input name="workers" type="number" min="1" max="16" required value="${d.workers}"><small>1–16 台，默认 5 台并发采集</small></label><label class="field"><span>默认连接端口</span><input name="port" type="number" min="1" max="65535" required value="${d.port}"></label></div><h2 style="margin-top:28px">网段添加默认值</h2><p>仅用于当前会话中新增的网段 / 地址范围设备，不覆盖已有设备。</p><div class="form-grid"><label class="field"><span>默认设备厂商</span><select name="vendor"><option value="huawei" ${d.vendor==='huawei'?'selected':''}>华为 / VRP</option><option value="hp_comware" ${d.vendor==='hp_comware'?'selected':''}>H3C / Comware</option></select></label><label class="field"><span>默认分组</span><input name="group" value="${esc(d.group)}" maxlength="80" required></label><label class="field"><span>默认用户名</span><input name="username" autocomplete="off" value="${esc(d.username)}" placeholder="输入设备登录用户名"></label><label class="field"><span>默认密码</span><input name="password" type="password" autocomplete="new-password" value="${esc(d.password)}" placeholder="输入设备登录密码"></label></div><div class="form-hint">${icon('lock')}默认凭据仅在本次应用会话中保留；已添加资产的凭据由 Windows DPAPI 加密保存。Excel 文件中的凭据仍为明文。</div><div class="settings-actions"><button class="button primary" type="submit">${icon('check')}保存偏好</button></div></form><section class="card settings-card command-settings"><h2>平台执行命令</h2><p>默认命令可按实际设备型号调整。每次巡检开始前会再次展示启用命令，人工确认后才执行。</p>${commandPanel('huawei','华为 / VRP')}${commandPanel('hp_comware','H3C / Comware')}<div class="form-hint">${icon('shield')}命令必须以 display 或 show 开头；不允许换行、分隔符或配置模式命令。</div></section><section class="card settings-card"><h2>只读采集规则</h2>${this.rulesMarkup()}</section>`;
  },
  rulesMarkup(){
    return `<ul class="rule-list"><li>${icon('shield')}<span>连接后确认处于 <code>&lt;hostname&gt;</code> 用户视图，视图异常立即停止。</span></li><li>${icon('check')}<span>先执行 <code>display version</code> 识别平台，再设置分页并执行已确认命令。</span></li><li>${icon('check')}<span>优先关闭分页；Console 明确不支持 VTY 临时设置时自动翻页，超时或超过安全上限立即停止。</span></li><li>${icon('lock')}<span>采集日志与结果去除本次连接凭据，输出按设备和任务自动归档。</span></li></ul>`;
  },
  bindPage(){
    const on=(s,fn)=>{const el=$(s);if(el)el.onclick=fn;};
    on('#add-button',()=>this.assetModal());on('#template-button',()=>this.downloadTemplate());
    on('#all-tasks',()=>this.navigate('tasks'));on('#activity-task',()=>this.navigate('tasks'));on('#activity-archive',()=>this.navigate('reports'));
    on('#task-start',()=>this.startModal());on('#to-reports',()=>this.navigate('reports'));on('#cancel-task',()=>this.cancelTask());
    $$('[data-report]').forEach(el=>el.onclick=()=>this.openReport(el.dataset.report));
    $$('[data-folder]').forEach(el=>el.onclick=()=>this.openReport(el.dataset.folder,true));
    on('#report-select',()=>{});
    if($('#report-select'))$('#report-select').onchange=e=>{this.reportId=e.target.value;this.render();};
    on('#report-html',()=>this.openReportFile(this.reportId));
    const search=$('#asset-search');
    if(search)search.oninput=()=>{this.query=search.value;this.pageIndex=1;this.refreshTable();};
    [['#vendor-filter','vendor'],['#status-filter','status'],['#group-filter','group']].forEach(([s,k])=>{const el=$(s);if(el)el.onchange=()=>{this[k]=el.value;this.pageIndex=1;this.refreshTable();};});
    if($('#settings-form'))$('#settings-form').onsubmit=e=>{e.preventDefault();const values=Object.fromEntries(new FormData(e.target));this.defaults={...values,workers:Number(values.workers),port:Number(values.port)};this.toast('偏好已保存，默认凭据仅在当前会话中保留');};
    $$('[data-command-add]').forEach(el=>el.onclick=()=>{const list=el.closest('[data-command-panel]').querySelector('.command-list');const row=document.createElement('div');row.className='command-row';row.setAttribute('data-command-row','');row.innerHTML='<input class="command-input" maxlength="240" aria-label="新增命令"><label class="command-enabled"><input type="checkbox" checked>启用</label><button type="button" class="icon-button" data-command-up aria-label="上移命令">↑</button><button type="button" class="icon-button" data-command-down aria-label="下移命令">↓</button><button type="button" class="icon-button" data-command-delete aria-label="删除命令">'+icon('trash')+'</button>';list.appendChild(row);row.querySelector('.command-input').focus();this.bindCommandRows();});
    $$('[data-command-save]').forEach(el=>el.onclick=()=>this.saveCommandPanel(el.dataset.commandSave));
    $$('[data-command-reset]').forEach(el=>el.onclick=()=>this.resetCommandPanel(el.dataset.commandReset));
    $$('[data-command-supplement]').forEach(el=>el.onclick=()=>this.supplementCommands(el.dataset.commandSupplement));
    this.bindCommandRows();
    this.bindTable();
  },
  supplementCommands(vendor){
    const panel=$(`[data-command-panel="${vendor}"]`),list=$('.command-list',panel);
    const present=new Set($$('.command-input',panel).map(el=>el.value.trim().toLowerCase().replace(/\s+/g,' ')));
    const missing=(this.data.analysis_commands?.[vendor]||analysisPresets[vendor]).filter(command=>!present.has(command));
    missing.forEach(command=>{
      const row=$('[data-command-row]',panel).cloneNode(true);
      $('.command-input',row).value=command;$('.command-input',row).setAttribute('aria-label','补充分析命令');
      $('.command-enabled input',row).checked=true;list.appendChild(row);
    });
    this.bindCommandRows();this.toast(missing.length?`已补充 ${missing.length} 条命令，请核对后保存`:'分析命令已齐全，现有设置保持不变');
  },
  bindCommandRows(){
    $$('[data-command-panel] [data-command-up]').forEach(el=>el.onclick=()=>{const row=el.closest('[data-command-row]'),prev=row.previousElementSibling;if(prev)row.parentElement.insertBefore(row,prev);});
    $$('[data-command-panel] [data-command-down]').forEach(el=>el.onclick=()=>{const row=el.closest('[data-command-row]'),next=row.nextElementSibling;if(next)row.parentElement.insertBefore(next,row);});
    $$('[data-command-panel] [data-command-delete]').forEach(el=>el.onclick=()=>{const list=el.closest('.command-list');if(list.children.length<=1){this.toast('至少保留一条命令');return;}el.closest('[data-command-row]').remove();});
  },
  async saveCommandPanel(vendor){
    const panel=$(`[data-command-panel="${vendor}"]`);if(!panel)return;
    const commands=[...panel.querySelectorAll('[data-command-row]')].map(row=>({command:row.querySelector('.command-input').value,enabled:row.querySelector('.command-enabled input').checked}));
    try{const result=await this.call('save_commands',vendor,commands);this.data.commands[vendor]=result.commands;this.toast('命令清单已保存');this.render();}catch(e){this.toast(e.message);}
  },
  async resetCommandPanel(vendor){
    try{const result=await this.call('reset_commands',vendor);this.data.commands[vendor]=result.commands;this.toast('已恢复默认命令');this.render();}catch(e){this.toast(e.message);}
  },
  bindTable(){
    $$('[data-select]').forEach(el=>el.onchange=()=>{el.checked?this.selected.add(el.dataset.select):this.selected.delete(el.dataset.select);this.refreshTable();});
    if($('#select-all'))$('#select-all').onchange=e=>{this.visible.forEach(a=>e.target.checked?this.selected.add(a.host):this.selected.delete(a.host));this.refreshTable();};
    if($('#select-all'))$('#select-all').indeterminate=this.visible.some(a=>this.selected.has(a.host))&&!this.visible.every(a=>this.selected.has(a.host));
    $$('[data-detail]').forEach(el=>el.onclick=()=>this.detail(el.dataset.detail));
    $$('[data-menu]').forEach(el=>el.onclick=()=>this.deviceMenu(el.dataset.menu));
    if($('#clear-filters'))$('#clear-filters').onclick=()=>{this.query='';this.status='all';this.vendor='all';this.group='all';this.pageIndex=1;this.render();};
    if($('#empty-add'))$('#empty-add').onclick=()=>this.assetModal();
    if($('#enter-demo'))$('#enter-demo').onclick=()=>this.enterDemo();
    if($('#inspect-selected'))$('#inspect-selected').onclick=()=>this.startModal();
    if($('#delete-selected'))$('#delete-selected').onclick=()=>this.deleteModal([...this.selected]);
    if($('#clear-selection'))$('#clear-selection').onclick=()=>{this.selected.clear();this.refreshTable();};
  },
  modal(title,body,footer='',wide=false){
    const dialog=$('#modal');
    if(dialog.open)dialog.close();
    dialog.style.width=wide?'780px':'550px';
    $('#modal-content').innerHTML=`<div class="modal-header"><h2 id="modal-title">${esc(title)}</h2><button class="icon-button" data-close aria-label="关闭">${icon('close')}</button></div><div class="modal-body">${body}</div>${footer?`<div class="modal-footer">${footer}</div>`:''}`;
    $$('[data-close]',dialog).forEach(el=>el.onclick=()=>dialog.close());
    dialog.showModal();
    return dialog;
  },
  async submit(button,fn){
    if(button.disabled)return;
    const original=button.innerHTML;button.disabled=true;button.textContent='正在处理...';
    try{await fn();}catch(e){const el=$('#form-error');if(el){el.hidden=false;el.textContent=e.message;}else this.toast(e.message);}
    finally{button.disabled=false;button.innerHTML=original;}
  },
  assetModal(asset=null,mode='single'){
    if(this.running){this.toast('请等待巡检结束后修改资产');return;}
    const d=this.defaults,a=asset||{},editing=!!asset,cidr=mode==='cidr';
    const selectedVendor=editing?(a.vendor||''):d.vendor;
    this.modal(editing?'编辑设备':'添加设备',`${!editing?`<div class="modal-tabs"><button class="${!cidr?'active':''}" id="tab-single">单台设备</button><button class="${cidr?'active':''}" id="tab-cidr">网段 / 地址范围</button></div>`:''}<form id="asset-form"><div class="form-grid">${!cidr?`<label class="field"><span>设备名称</span><input name="name" placeholder="例如 HQ-CORE-SW01" maxlength="100" value="${esc(a.name)}"></label>`:''}<label class="field ${cidr?'full':''}"><span>${cidr?'网段 / 地址范围':'管理 IPv4 地址'} *</span><input name="${cidr?'range':'host'}" required placeholder="${cidr?'192.168.10.0/24':'192.168.10.1'}" value="${esc(a.host)}" ${editing?'autofocus':''}>${cidr?'<small>支持 192.168.1.0/24、192.168.1.1-10 或 192.168.1.1-192.168.1.10；单次最多 4096 个地址，自动跳过已有 IP。</small>':''}</label><label class="field"><span>设备厂商</span><select name="vendor"><option value="" ${selectedVendor===''?'selected':''}>未指定</option><option value="huawei" ${selectedVendor==='huawei'?'selected':''}>华为 / VRP</option><option value="hp_comware" ${selectedVendor==='hp_comware'?'selected':''}>H3C / Comware</option></select><small>可留空，登录后自动识别平台。</small></label><label class="field"><span>连接端口 *</span><input name="port" type="number" min="1" max="65535" required value="${a.port||d.port}"><small>先尝试 SSH，登录失败后在此端口尝试 Telnet。</small></label><label class="field"><span>用户名 ${editing?'':'*'}</span><input name="username" autocomplete="off" ${editing?'':'required'} value="${editing?'':esc(d.username)}" placeholder="${editing?'留空保留已保存用户名':'设备登录用户名'}"></label><label class="field"><span>密码 ${editing?'':'*'}</span><input name="password" type="password" autocomplete="new-password" ${editing?'':'required'} value="${editing?'':esc(d.password)}" placeholder="${editing?'留空保留已保存密码':'设备登录密码'}"></label><label class="field full"><span>设备分组</span><input name="group" maxlength="80" value="${esc(a.group||d.group)}" placeholder="例如 总部 · 核心网络"></label></div><div class="form-hint">${icon('lock')}凭据由当前 Windows 账户加密保存。默认先使用 SSH；登录失败后使用同端口 Telnet（明文传输）。${this.demo?'演示模式下的修改仅在内存中生效。':''}</div><div class="form-error" id="form-error" hidden></div></form>`,`<button class="button" data-close>取消</button><button class="button primary" id="save-asset">${icon('plus')}${editing?'保存修改':cidr?'添加范围':'添加设备'}</button>`);
    if($('#tab-single'))$('#tab-single').onclick=()=>this.assetModal(null,'single');
    if($('#tab-cidr'))$('#tab-cidr').onclick=()=>this.assetModal(null,'cidr');
    const save=$('#save-asset'),form=$('#asset-form');
    const fn=()=>{if(!form.reportValidity())return;this.submit(save,async()=>{
      const record=Object.fromEntries(new FormData(form));
      let result;
      if(cidr)result=await this.call('add_range',record);else result=await this.call('save_asset',record,a.host||null);
      $('#modal').close();await this.refresh();this.toast(cidr?`新增 ${result.added} 台设备，跳过 ${result.skipped} 个重复 IP`:editing?'设备已更新':'设备已添加');
    });};
    save.onclick=fn;form.onsubmit=e=>{e.preventDefault();fn();};
  },
  deviceMenu(host){
    const a=this.data.assets.find(a=>a.host===host);if(!a)return;
    this.modal(a.name,`<p class="dialog-note" style="margin:0 0 20px">${esc(a.host)} · ${vendorLabel(a.vendor)} · ${esc(a.group)}</p><div class="empty-actions" style="justify-content:flex-start"><button class="button" id="menu-detail">${icon('activity')}查看结果</button><button class="button" id="menu-edit">${icon('edit')}编辑设备</button><button class="button danger" id="menu-delete">${icon('trash')}删除设备</button></div>`);
    $('#menu-detail').onclick=()=>this.detail(host);$('#menu-edit').onclick=()=>this.assetModal(a);$('#menu-delete').onclick=()=>this.deleteModal([host]);
  },
  deleteModal(hosts){
    if(this.running){this.toast('请等待巡检结束后修改资产');return;}
    this.modal('删除所选设备',`<p style="font-size:13px">将从资产清单中删除 <strong>${hosts.length}</strong> 台设备。</p><p class="dialog-note">已有巡检报告与配置归档仍可在「报告与归档」中查看。</p><div class="form-error" id="form-error" hidden></div>`,`<button class="button" data-close>取消</button><button class="button danger" id="confirm-delete">${icon('trash')}确认删除</button>`);
    const b=$('#confirm-delete');b.onclick=()=>this.submit(b,async()=>{await this.call('delete_assets',hosts);hosts.forEach(h=>this.selected.delete(h));$('#modal').close();await this.refresh();this.toast('所选设备已删除');});
  },
  importModal(){
    if(this.running){this.toast('请等待巡检结束后导入资产');return;}
    this.modal('从 Excel 导入资产',`<div class="form-hint" style="margin-top:0">使用标准模板，一行一台设备。每台设备可配置独立用户名和密码；重复 IP 将自动跳过。</div><div class="empty-actions" style="justify-content:flex-start"><button class="button" id="import-template">${icon('download')}下载 Excel 模板</button><button class="button" id="import-cidr">${icon('network')}按网段 / 地址范围添加</button></div><p class="dialog-note">必需列：设备名称、IP地址、SSH端口、用户名、密码。<br>可选列：品牌、分组。品牌留空时登录后自动识别。SSH端口列同时用于 Telnet 回退。</p><div class="form-error" id="form-error" hidden></div>`,`<button class="button" data-close>取消</button><button class="button primary" id="choose-excel">${icon('upload')}选择 Excel 文件</button>`);
    $('#import-template').onclick=()=>this.downloadTemplate();$('#import-cidr').onclick=()=>this.assetModal(null,'cidr');
    const b=$('#choose-excel');b.onclick=()=>this.submit(b,async()=>{
      if(this.demo){this.toast('演示模式不读取本机凭据文件，请进入真实工作空间导入');return;}
      const r=await this.call('import_excel');if(r.cancelled)return;$('#modal').close();await this.refresh();this.toast(`新增 ${r.added} 台设备，跳过 ${r.skipped} 个重复 IP`);
    });
  },
  async downloadTemplate(){
    try{
      if(this.demo){this.toast('请进入真实工作空间下载标准 Excel 模板');return;}
      const r=await this.call('save_template');if(!r.cancelled)this.toast('Excel 模板已保存');
    }catch(e){this.toast(e.message);}
  },
  startModal(){
    if(this.running){this.navigate('tasks');return;}
    if(!this.data.assets.length){this.toast('先添加设备，再开始巡检');this.assetModal();return;}
    const hosts=this.selected.size?[...this.selected]:this.filtered().map(a=>a.host);
    if(!hosts.length){this.toast('当前筛选下没有设备可巡检');return;}
    const selectedAssets=this.data.assets.filter(a=>hosts.includes(a.host));
    const vendors=new Set(selectedAssets.map(a=>supportedVendor(a.vendor)?a.vendor:null).filter(Boolean));
    const shownVendors=vendors.size?[...vendors]:['huawei','hp_comware'];
    const commandSummary=shownVendors.map(v=>`<div class="command-review"><strong>${vendorLabel(v)}</strong><span>${(this.data.commands?.[v]||[]).filter(row=>row.enabled).map(row=>`<code>${esc(row.command)}</code>`).join('　')||'没有启用命令'}</span></div>`).join('');
    this.modal(this.demo?'开始演示巡检':'开始只读巡检',`<div class="detail-metrics" style="margin-top:0"><div class="detail-metric"><span>${this.selected.size?'所选设备':'当前筛选范围'}</span><strong>${hosts.length}<small style="font-size:13px;margin-left:6px">台</small></strong></div><div class="detail-metric"><span>平台识别</span><strong style="font-size:19px">登录后执行 display version</strong></div></div><form id="start-form"><label class="field"><span>并发设备数</span><input name="workers" id="run-workers" type="number" min="1" max="16" required value="${this.defaults.workers}"><small>建议 5–10 台，并发越高对网络与设备的负载越大。</small></label><label class="check-row"><input type="checkbox" id="collect-sn"><span>采集设备 SN</span><small>失败时仅记录为未识别，不影响其他结果</small></label></form><h3>本次启用命令</h3><div class="command-review-list">${commandSummary}</div><div class="form-hint">${icon('shield')}${this.demo?'这是模拟巡检，不建立 SSH 连接，也不生成真实配置归档。':'请人工核对以上命令；确认后先尝试 SSH，登录失败自动尝试同端口 Telnet（明文传输），在用户视图内采集状态与配置。'}</div><div class="form-error" id="form-error" hidden></div>`,`<button class="button" data-close>取消</button><button class="button primary" id="confirm-start">${icon('play')}${this.demo?'开始演示':'确认命令并开始巡检'}</button>`);
    const b=$('#confirm-start'),form=$('#start-form');const fn=()=>{if(!form.reportValidity())return;this.submit(b,async()=>{await this.call('start_run',hosts,Number($('#run-workers').value),this.data.commands,!!$('#collect-sn')?.checked,true);$('#modal').close();await this.refresh(false);this.navigate('tasks');});};
    b.onclick=fn;form.onsubmit=e=>{e.preventDefault();fn();};
  },
  async cancelTask(){try{await this.call('cancel_run');await this.refresh();this.toast('已停止派发新设备，等待当前会话结束');}catch(e){this.toast(e.message);}},
  async detail(host){
    const a=this.data.assets.find(a=>a.host===host);if(!a)return;
    if(!a.result){this.deviceMenuNoResult(a);return;}
    try{
      const result=await this.call('get_result',host),m=result.metrics||{};
      const hardware=['fanpower','fan','power'].flatMap(k=>m[k]?.units||[]);
      this.modal(a.name,`<div style="display:flex;align-items:center;justify-content:space-between;gap:12px"><span class="mono">${esc(a.host)} : ${a.port}${result.transport?` · ${esc(result.transport.toUpperCase())}`:''}</span>${pill(result.status)}</div><p class="dialog-note" style="margin-top:8px">${esc(a.group)} · ${vendorLabel(a.vendor)} · ${fullDate(result.collected)}</p>${result.error?`<p class="result-error">${esc(result.error)}</p>`:''}<div class="detail-metrics"><div class="detail-metric"><span>CPU 使用率</span><strong>${m.cpu==null?'未知':m.cpu+'%'}</strong></div><div class="detail-metric"><span>内存使用率</span><strong>${m.memory==null?'未知':m.memory+'%'}</strong></div></div><h2>风扇 / 电源状态</h2><p class="dialog-note" style="margin:10px 0 20px">${hardware.length?hardware.map(u=>`${esc(u.name)} · ${esc(u.state)}`).join('　 /　 '):'无法识别设备输出，需人工核实。'}</p><h2>命令输出${this.demo?'（示例）':''}</h2>${Object.entries(result.outputs||{}).map(([cmd,text])=>`<details class="output-details"><summary>${esc(cmd)}</summary><pre>${esc(text)}</pre></details>`).join('')||'<p class="dialog-note">未采集到命令输出。</p>'}`,'<button class="button" data-close>关闭</button>',true);
    }catch(e){this.toast(e.message);}
  },
  deviceMenuNoResult(a){
    this.modal(a.name,`<div class="empty-state" style="padding:15px 0"><span>${icon('server')}</span><h3>此设备尚未巡检</h3><p>${esc(a.host)} · ${esc(a.group)}<br>完成巡检后可查看运行指标及完整配置。</p></div>`,`<button class="button" data-close>关闭</button><button class="button" id="edit-uninspected">${icon('edit')}编辑设备</button>`);
    $('#edit-uninspected').onclick=()=>this.assetModal(a);
  },
  async loadReport(){
    const id=this.reportId,container=$('#report-view'),request=Symbol();this.reportRequest=request;
    try{
      const report=await this.call('get_report',id);
      if(this.reportRequest!==request||this.page!=='reports'||!container.isConnected)return;
      container.innerHTML=report.html;
      ReportView.mount($('.inspection-report',container),(host,run)=>this.call('get_result',host,run));
      const sample=$('[data-demo-sample]',container);if(sample)sample.onclick=()=>this.openReport('demo-run');
    }catch(error){if(this.reportRequest===request&&container.isConnected)container.innerHTML=`<p class="result-error">${esc(error.message)}</p>`;}
  },
  async openReport(id,folder=false){
    if(folder)return this.openReportFile(id,true);
    this.reportId=id;this.navigate('reports');$('#page-content').scrollIntoView({block:'start'});
  },
  async openReportFile(id,folder=false){
    if(this.demo){
      if(!folder){this.toast('演示模式不生成文件；完成真实巡检后可离线打开 HTML。');return;}
      this.modal('示例归档结构','<div class="task-logs" style="min-height:0">reports / 运行时间 /<br>　report.html<br>　results.json<br>　设备IP_current-configuration.txt</div><p class="dialog-note">这是演示内容；真实巡检结束后生成可独立打开的 HTML、JSON 和配置文本。</p>','<button class="button" data-close>关闭</button>');return;
    }
    try{await this.call('open_report',id,folder);}catch(e){this.toast(e.message);}
  },
  help(){this.modal('开始使用 Switch Inspector',`<div class="help-content"><h3 style="margin-top:0">1. 建立设备清单</h3><p>单台添加、输入 IPv4 网段，或使用 Excel 模板批量导入。重复 IP 会自动跳过。编辑设备时，凭据留空即可保留原值。</p><h3>2. 选择范围，开始巡检</h3><p>勾选设备后巡检所选；未勾选时巡检当前筛选范围。开始前可设置 1–16 台并发。任务页可查看实时日志或取消后续派发。</p><h3>3. 查看报告与完整配置</h3><p>在「报告与归档」打开 HTML 报告，或进入归档目录获取 JSON 与逐设备配置文本。无法识别的指标会标为「待核实」。</p><h3>连接方式</h3><p>支持华为 VRP、H3C Comware，默认优先 SSH，连接或登录失败后在设备填写的同一端口尝试 Telnet（明文传输）。无需选择协议，支持模拟器控制台。登录后保持用户视图，按已确认的命令采集。</p></div>`,'<button class="button primary" data-close>知道了</button>',true);},
  closeWarning(){this.modal('巡检仍在进行',`<p style="font-size:13px">请等待任务完成，或先取消任务再关闭应用。</p><p class="dialog-note">当前设备会话会正常结束并释放连接，已采集结果会自动归档。</p>`,'<button class="button primary" data-close>返回任务</button>');this.navigate('tasks');},
  toast(message){const el=$('#toast');el.textContent=message;el.classList.add('show');clearTimeout(this.toastTimer);this.toastTimer=setTimeout(()=>el.classList.remove('show'),4200);},
  enterDemo(){if(this.running){this.toast('请等待巡检结束后切换工作空间');return;}this.demo=true;this.data=demoData();this.reportId=null;this.selected.clear();this.navigate('dashboard');},
  async exitDemo(){
    if(this.demoTimer){clearTimeout(this.demoTimer);this.demoTimer=null;}
    this.demo=false;this.selected.clear();
    if(window.pywebview?.api){await this.refresh(false);this.navigate('dashboard');}
    else{this.demo=true;this.toast('当前为浏览器预览，请启动桌面应用进入真实工作空间');}
  },
  async demoCall(method,...args){
    if(method==='snapshot')return this.data;
    if(method==='save_asset'){
      const [record,original]=args;
      if(!this.validIP(record.host))throw new Error('请输入有效的 IPv4 地址');
      if(this.data.assets.some(a=>a.host===record.host&&a.host!==original))throw new Error('该 IP 已存在');
      const row={...record,port:Number(record.port),group:record.group||'未分组'};delete row.password;delete row.username;
      const index=this.data.assets.findIndex(a=>a.host===original);
      if(index<0)this.data.assets.push(row);else this.data.assets[index]=row;
      return {ok:true};
    }
    if(method==='delete_assets'){this.data.assets=this.data.assets.filter(a=>!args[0].includes(a.host));return {ok:true};}
    if(method==='add_cidr'||method==='add_range'){
      const r=args[0],value=String(r.range??r.cidr??'').trim(),toInt=ip=>ip.split('.').reduce((a,n)=>a*256+Number(n),0);
      let first,last;
      if(value.includes('/')){
        const [ip,bits,...extra]=value.split('/'),prefix=Number(bits);
        if(!this.validIP(ip)||bits===undefined||extra.length||!/^\d+$/.test(bits)||prefix<0||prefix>32)throw new Error('请输入有效的 IPv4 CIDR');
        const size=2**(32-prefix),network=Math.floor(toInt(ip)/size)*size;
        first=network+(prefix>=31?0:1);last=network+size-(prefix>=31?1:2);
      }else{
        const parts=value.split('-').map(p=>p.trim());let [start,end]=parts;
        if(parts.length!==2)throw new Error('请输入 CIDR、简写或完整起止 IPv4 地址');
        if(/^\d+$/.test(end))end=start.slice(0,start.lastIndexOf('.')+1)+end;
        if(!this.validIP(start)||!this.validIP(end))throw new Error('起止地址必须为有效 IPv4 地址');
        first=toInt(start);last=toInt(end);
      }
      if(first>last)throw new Error('起始地址不能大于结束地址');
      const count=last-first+1;if(count>4096)throw new Error('单次添加上限为 4096 个地址');
      const existing=new Set(this.data.assets.map(a=>a.host));let added=0;
      for(let v=first;v<=last;v++){
        const host=[Math.floor(v/2**24)%256,Math.floor(v/2**16)%256,Math.floor(v/256)%256,v%256].join('.');
        if(!existing.has(host)){this.data.assets.push({host,name:host,vendor:r.vendor,port:Number(r.port),group:r.group||'未分组'});existing.add(host);added++;}
      }return {ok:true,added,skipped:count-added};
    }
    if(method==='get_report'){
      if(args[0]==='demo-run')return window.DemoReport;
      return {html:'<section class="card settings-card"><h2>演示任务记录</h2><p>本次为界面操作演示，未连接设备、未生成分析归档。可切换到示例任务查看完整的分析报告。</p><button class="button" data-demo-sample>查看示例分析报告</button></section>'};
    }
    if(method==='get_result'){
      const a=this.data.assets.find(a=>a.host===args[0]),r=a?.result;if(!r)throw new Error('此设备尚未巡检');
      return {...r,outputs:r.status==='fail'?{}:{'display cpu-usage':`[演示输出]\nCPU usage: ${r.metrics.cpu}%`,'display current-configuration':`# 示例配置，非真实设备数据\n#\nsysname ${a.name}\n#\nreturn`}};
    }
    if(method==='save_commands'){
      const [vendor,commands]=args;
      if(!['huawei','hp_comware'].includes(vendor))throw new Error('不支持的设备平台');
      const rows=commands.map(row=>({command:String(row.command||'').trim(),enabled:!!row.enabled}));
      if(!rows.length||rows.some(row=>!/^\s*(display|show)\s+\S/i.test(row.command)||/[\r\n;|`]/.test(row.command)))throw new Error('命令必须是单行 display 或 show 命令');
      this.data.commands[vendor]=rows;return {ok:true,commands:rows};
    }
    if(method==='reset_commands'){
      const defaults=demoDefaults;
      const rows=defaults[args[0]].map(command=>({command,enabled:true}));this.data.commands[args[0]]=rows;return {ok:true,commands:rows};
    }
    if(method==='start_run'){
      if(this.running)throw new Error('已有巡检正在运行');
      const [hosts,workers]=args;
      if(!Number.isInteger(workers)||workers<1||workers>16)throw new Error('并发数必须为 1–16 的整数');
      this.data.run={id:'demo-'+Date.now(),started:nowISO(),state:'running',total:hosts.length,completed:0,workers,results:[],logs:[],active:hosts.slice(0,workers),consoles:Array.from({length:Math.min(workers,hosts.length)},(_,i)=>({slot:i+1,status:'idle',host:'',name:'',command:'',output:'',updated:''}))};
      const r=this.data.run,queue=[...hosts];
      const next=()=>{
        const host=queue.shift(),a=this.data.assets.find(a=>a.host===host);
        if(a){const slot=r.consoles[r.completed%r.consoles.length];slot.host=a.host;slot.name=a.name;slot.status='running';slot.command='display version';slot.output='Huawei Versatile Routing Platform\\n[演示] 正在读取设备输出…';slot.updated=nowISO();const result=a.result||{host:a.host,name:a.name,vendor:a.vendor,status:'ok',metrics:{cpu:12,memory:35,fanpower:{found:true,units:[{name:'FAN1',state:'Normal'}]}}};result.collected=nowISO();a.result=result;r.results.push({...result});r.completed++;slot.command='display current-configuration';slot.output+='\\n[演示] 配置采集完成';slot.status='done';slot.updated=nowISO();r.logs.push({time:shortTime(nowISO()),host,status:result.status,message:'[演示] 模拟状态与配置采集完成'});}
        r.active=queue.slice(0,workers);
        if(!queue.length||r.state==='cancelling'){
          r.state=r.state==='cancelling'?'cancelled':'done';r.finished=nowISO();r.active=[];
          this.data.history.unshift({id:r.id,started:r.started,state:r.state,count:r.completed,total:r.total,ok:r.results.filter(a=>a.status==='ok').length,warn:r.results.filter(a=>a.status==='warn').length,fail:r.results.filter(a=>a.status==='fail').length,results:[...r.results]});
          this.demoTimer=null;
        }else this.demoTimer=setTimeout(next,650);
        if(this.page!=='settings'&&!$('#modal').open)this.render();
      };
      this.demoTimer=setTimeout(next,650);return {ok:true};
    }
    if(method==='cancel_run'){if(this.data.run.state==='running')this.data.run.state='cancelling';return {ok:true};}
    return {cancelled:true};
  },
  validIP(ip){return /^\d+\.\d+\.\d+\.\d+$/.test(ip)&&ip.split('.').every(n=>Number(n)<=255&&(n==='0'||!n.startsWith('0')));},
  async init(){
    if(this.initialized)return;
    this.initialized=true;hydrate();
    $$('.nav-item').forEach(el=>el.onclick=()=>this.navigate(el.dataset.nav));
    $('.brand').onclick=e=>{e.preventDefault();this.navigate('dashboard');};
    $('#heading-secondary').onclick=()=>this.page==='reports'?this.refresh():this.page==='settings'?this.help():this.importModal();
    $('#start-button').onclick=()=>this.startModal();$('#exit-demo').onclick=()=>this.exitDemo();$('#help-button').onclick=()=>this.help();
    $('#safety-link').onclick=()=>this.modal('只读巡检规则',this.rulesMarkup(),'<button class="button primary" data-close>知道了</button>',true);
    $('#about-button').onclick=()=>this.modal('Switch Inspector 2.0',`<div class="help-content"><p>面向华为 VRP / H3C Comware 的 Windows 只读巡检工作台。</p><p>资产管理 · 批量采集 · 状态分析 · 配置归档</p><p>当前状态：${this.demo?'演示模式':'本地工作空间'}<br>真实设备兼容性需在目标型号与固件上验证。</p><button class="button" id="switch-demo">${icon('flask')}${this.demo?'进入我的工作空间':'体验演示工作空间'}</button></div>`,'<button class="button" data-close>关闭</button>')&&($('#switch-demo').onclick=()=>{$('#modal').close();this.demo?this.exitDemo():this.enterDemo();});
    $('#data-info').onclick=()=>this.modal('本机工作空间',`<div class="help-content"><p>资产凭据由当前 Windows 账户加密。更换 Windows 账户或电脑后，需要重新添加连接凭据。</p><p>数据与报告目录：</p><div class="form-hint" style="overflow-wrap:anywhere">${esc(this.data.data_dir||'启动桌面应用后可查看')}</div><p>配置归档可能包含设备敏感配置，请限制报告目录的访问权限。</p></div>`,'<button class="button" data-close>关闭</button>');
    document.addEventListener('keydown',e=>{
      if(e.key==='/'&&!['INPUT','TEXTAREA','SELECT'].includes(document.activeElement.tagName)&&!$('#modal').open){const el=$('#asset-search');if(el){e.preventDefault();el.focus();}}
      if((e.ctrlKey||e.metaKey)&&e.key==='Enter'&&!$('#modal').open){e.preventDefault();this.startModal();}
    });
    $('#modal').addEventListener('click',e=>{if(e.target===$('#modal')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
    if(this.demo)this.data=demoData();else await this.refresh(false);
    this.navigate(location.hash.slice(1)||'dashboard');
    setInterval(async()=>{
      if(this.demo||!window.pywebview?.api||$('#modal').open)return;
      const wasRunning=this.running;
      await this.refresh(false);
      if(wasRunning||this.running){
        if(this.page!=='settings')this.render();
        if(wasRunning&&!this.running)this.toast(this.data.run.state==='error'?'报告保存失败，请检查任务详情':this.data.run.state==='cancelled'?'任务已取消，已采集结果完成归档':'巡检完成，报告与配置已归档');
      }
    },1100);
  },
};
window.app=app;
window.addEventListener('pywebviewready',()=>app.init());
if(app.demo)app.init();
else setTimeout(()=>{if(!app.initialized&&!window.pywebview?.api){app.demo=true;app.init();}},1500);


