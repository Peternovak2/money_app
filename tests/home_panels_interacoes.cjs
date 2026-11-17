const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fonte = fs.readFileSync('app/static/js/home-panels.js', 'utf8');
function el() {
  return {dataset:{},style:{},children:[],listeners:{},
    append(...xs){this.children.push(...xs);},replaceChildren(...xs){this.children=xs;},
    addEventListener(k,fn){this.listeners[k]=fn;},
    setAttribute(k,v){this[k]=v;},querySelectorAll(){return this.children.filter(x=>x.type==='button');}};
}
const ids = Object.fromEntries(['analise-acompanhamento','desempenho-setor','macro-usd','macro-futures',
  'macro-mini-chart','sector-results','sector-mini-chart','sector-detail','favorite-form','favorite-feedback',
  'favorite-ticker'].map(id=>[id,el()]));
ids['favorite-form'].dataset.csrf='csrf';
const charts=[];const pedidos=[];
const serie=[{data:'2026-10-01',valor:100},{data:'2026-10-30',valor:110}];
vm.runInNewContext(fonte, {
  Intl,AbortSignal,ResizeObserver:class{observe(){}},
  document:{readyState:'complete',getElementById:id=>ids[id],querySelectorAll:()=>[],createElement:()=>el()},
  window:{addEventListener(){},matchMedia:()=>({matches:true}),echarts:{graphic:{LinearGradient:class{}},init(){
    const c={setOption(o){this.option=o;},dispose(){},resize(){},isDisposed(){return false;}};charts.push(c);return c;
  }},location:{reload(){assert.fail('Falha HTTP não pode recarregar');}}},
  fetch:async(url,options)=>{
    pedidos.push({url,options});
    if(options?.method) return {ok:false,json:async()=>({detail:'Migração pendente'})};
    const dados=url.includes('macro') ? [
      {id:'BRL=X',nome:'USD/BRL',unidade:'BRL por USD',estado:'disponivel',valor:110,variacao:10,serie,inicio:'2026-10-01',referencia:'2026-10-30'},
      {id:'GC=F',nome:'Ouro',estado:'indisponivel',serie:[]}
    ] : [{id:'Finance',nome:'Financeiro',estado:'disponivel',variacao:10,serie,membros:['A1','A2'],fonte:'Teste'}];
    return {ok:true,json:async()=>dados};
  }
});
setImmediate(async()=>{
  try {
    assert.equal(pedidos.length,2);
    assert.equal(charts.length,1);
    assert.deepEqual(Array.from(charts[0].option.series[0].data),[100,110]);
    assert.equal(ids['desempenho-setor'].dataset.sectorState,'available');
    const sector=ids['sector-results'].children[1];
    assert.equal(sector['aria-pressed'],'true');
    assert.equal(sector.children[2].children[0].style.width,'50%');
    assert.ok(ids['macro-futures'].children[0].children.some(c=>c.textContent==='Indisponível'));
    ids['favorite-ticker'].value='PETR4';
    ids['favorite-form'].listeners.submit({preventDefault(){}});
    await new Promise(r=>setImmediate(r));
    assert.equal(pedidos[2].options.headers['X-CSRF-Token'],'csrf');
    assert.equal(ids['favorite-feedback'].textContent,'Migração pendente');
    console.log('Painéis: séries reais do contrato, escala, seleção, falha isolada e CSRF OK.');
  }catch(e){console.error(e);process.exitCode=1;}
});
