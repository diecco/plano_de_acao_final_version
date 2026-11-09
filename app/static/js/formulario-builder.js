(() => {
  const root = document.querySelector('[data-form-builder]');
  if (!root) return;
  const hidden = document.getElementById('estrutura_json');
  const host = root.querySelector('[data-fields]');
  const add = root.querySelector('[data-add-field]');
  const counter = root.querySelector('[data-field-count]');
  const types = [['text','Texto curto'],['textarea','Texto longo'],['date','Data'],['time','Hora'],['number','Número'],['choice','Seleção de uma opção'],['person','Uma pessoa'],['people','Várias pessoas'],['sector','Setor / Área']];
  const widths = [['3','25%'],['4','33%'],['6','50%'],['8','66%'],['9','75%'],['12','100%']];
  let fields = [];
  try { fields = JSON.parse(hidden.value || '[]'); } catch (_) {}
  if (!Array.isArray(fields)) fields = [];
  const ref = () => `campo_${Date.now()}_${Math.random().toString(36).slice(2,9)}`;
  const el = (tag, cls, text) => { const n=document.createElement(tag); if(cls)n.className=cls; if(text!==undefined)n.textContent=text; return n; };
  const input = (value, cb) => { const n=el('input','form-control'); n.value=value||''; n.maxLength=200; n.addEventListener('input',()=>cb(n.value)); return n; };
  const select = (opts,value,cb) => { const n=el('select','form-select'); opts.forEach(([v,t])=>{const o=el('option','',t);o.value=v;n.append(o)});n.value=value;n.addEventListener('change',()=>cb(n.value));return n; };
  const field = (label,control) => { const d=el('div','form-builder-control'); d.append(el('label','form-label',label),control); return d; };
  const sync=()=>{hidden.value=JSON.stringify(fields);counter.textContent=`${fields.length} de 100 campos`;};
  function render(){
    host.innerHTML='';
    fields.forEach((f,i)=>{
      const card=el('div','card border-0 shadow-sm mb-3'); const body=el('div','card-body');
      const row=el('div','row g-3 align-items-end');
      const cType=el('div','col-12 col-lg-3'); cType.append(field('Tipo do campo',select(types,f.type||'text',v=>{f.type=v;sync();render()})));
      const cLabel=el('div','col-12 col-lg-5'); cLabel.append(field('Nome do campo',input(f.label,v=>{f.label=v;sync()})));
      const cWidth=el('div','col-8 col-lg-2'); cWidth.append(field('Largura',select(widths,String(f.width||4),v=>{f.width=Number(v);sync()})));
      const actions=el('div','col-4 col-lg-2 d-flex justify-content-end gap-2');
      [['↑',-1],['↓',1]].forEach(([t,d])=>{const b=el('button','btn btn-outline-secondary btn-sm',t);b.type='button';b.disabled=(d<0&&i===0)||(d>0&&i===fields.length-1);b.onclick=()=>{[fields[i],fields[i+d]]=[fields[i+d],fields[i]];sync();render()};actions.append(b)});
      const del=el('button','btn btn-outline-danger btn-sm','×');del.type='button';del.onclick=()=>{fields.splice(i,1);sync();render()};actions.append(del);
      row.append(cType,cLabel,cWidth,actions);body.append(row);
      const rules=el('div','d-flex flex-wrap gap-4 mt-3');
      [['required','Resposta obrigatória'],['listable','Exibir na listagem'],['filterable','Usar como filtro']].forEach(([key,label])=>{const l=el('label','form-check');const x=el('input','form-check-input');x.type='checkbox';x.checked=!!f[key];x.onchange=()=>{f[key]=x.checked;sync()};l.append(x,document.createTextNode(` ${label}`));rules.append(l)}); body.append(rules);
      if(f.type==='choice'){const a=el('textarea','form-control mt-3');a.rows=3;a.placeholder='Uma alternativa por linha';a.value=(f.options||[]).join('\n');a.oninput=()=>{f.options=a.value.split('\n').map(v=>v.trim()).filter(Boolean);sync()};body.append(a)}
      card.append(body);host.append(card);
    }); sync();
  }
  add.addEventListener('click',()=>{if(fields.length>=100)return;fields.push({ref:ref(),label:'',type:'text',width:4,required:true,listable:true,filterable:false,options:[]});render()});
  document.getElementById('formBuilderForm')?.addEventListener('submit',e=>{if(!fields.length||fields.some(f=>!String(f.label||'').trim())){e.preventDefault();alert('Inclua ao menos um campo e informe o nome de todos eles.')}});
  render();
})();
