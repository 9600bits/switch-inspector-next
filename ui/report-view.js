/* Shared by the desktop report and standalone, offline HTML. */
(function(global){
  'use strict';
  const escape = value => String(value ?? '').replace(/[&<>"']/g,ch=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[ch]));
  function rawMarkup(outputs){
    return Object.entries(outputs||{}).map(([cmd,value])=>`<details class="report-output"><summary>${escape(cmd)}</summary><pre>${escape(value)}</pre></details>`).join('')||'<p>未采集到命令输出。</p>';
  }
  function mount(root,loader){
    if(!root||root.dataset.mounted)return;
    root.dataset.mounted='true';
    const one=s=>root.querySelector(s),all=s=>[...root.querySelectorAll(s)];
    const rows=all('.report-summary tbody tr');
    function filter(){
      const query=one('[data-report-search]').value.trim().toLowerCase();
      const status=one('[data-report-filter="status"]').value,group=one('[data-report-filter="group"]').value;
      let count=0;
      rows.forEach(row=>{row.hidden=!!((query&&!row.dataset.reportQuery.includes(query))||(status&&row.dataset.reportStatus!==status)||(group&&row.dataset.reportGroup!==group));if(!row.hidden)count++;});
      one('[data-report-count]').textContent=`显示 ${count} / ${rows.length} 台`;
      one('[data-report-empty]').hidden=count!==0;
    }
    one('[data-report-search]').addEventListener('input',filter);
    all('[data-report-filter]').forEach(el=>el.addEventListener('change',filter));
    all('[data-report-jump]').forEach(button=>button.addEventListener('click',()=>{
      const detail=all('.report-device').find(el=>el.id===button.dataset.reportJump);
      if(detail){detail.open=true;detail.scrollIntoView({block:'start'});detail.querySelector('summary').focus();}
    }));
    if(loader)all('.report-device').forEach(detail=>{
      const holder=detail.querySelector('.report-raw');
      async function load(){
        if(!detail.open||holder.dataset.loaded==='true'||holder.dataset.loading==='true')return;
        holder.dataset.loading='true';holder.textContent='正在加载完整输出…';
        try{
          const result=await loader(detail.dataset.reportHost,root.dataset.runId);
          if(result.error&&!result.outputs)throw new Error(result.error);
          holder.innerHTML=rawMarkup(result.outputs);holder.dataset.loaded='true';
        }catch(error){
          holder.innerHTML=`<p>${escape(error.message||'读取失败')}</p><button type="button" class="report-retry">重试加载</button>`;
          holder.querySelector('button').onclick=load;
        }finally{holder.dataset.loading='false';}
      }
      detail.addEventListener('toggle',load);
    });
    filter();
  }
  global.ReportView={mount,rawMarkup};
})(window);
