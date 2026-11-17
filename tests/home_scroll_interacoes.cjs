const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const script = fs.readFileSync('app/static/js/home-scroll.js', 'utf8');
function elemento(top = 1000) {
  const classes = new Set();
  const props = new Map();
  return {
    top, foco: false, ancora: false, filhos: [], vazio: false,
    classList: { add: (...xs) => xs.forEach(x => classes.add(x)), remove: (...xs) => xs.forEach(x => classes.delete(x)), contains: x => classes.has(x) },
    style: { setProperty: (k,v) => props.set(k,v), removeProperty: k => props.delete(k) }, props,
    getBoundingClientRect() { return {top: this.top, bottom: this.top + 300}; },
    matches() { return this.foco || this.ancora; },
    querySelector(s) { return s === ':target' ? (this.ancora ? {} : null) : (this.vazio ? {} : null); },
    querySelectorAll() { return this.filhos; },
    closest() { return this; },
  };
}
function iniciar({ reduzido=false, semObserver=false, falha=false } = {}) {
  const listeners = {}, timers = new Map();
  const secoes = [elemento(0), elemento(), elemento(), elemento(), elemento()];
  secoes[1].filhos = [elemento(), elemento()];
  secoes[1].vazio = true; // Um painel vazio nao pode impedir a secao inteira.
  const movimento = {matches: reduzido, addEventListener: (_,cb) => listeners.motion=cb};
  let observer;
  class Observer {
    constructor(callback, options) { Object.assign(this,{callback,options,observadas:[],retiradas:[]}); observer=this; }
    observe(s) { if (falha) throw Error('observer'); this.observadas.push(s); }
    unobserve(s) { this.retiradas.push(s); }
    disconnect() { this.desconectado=true; }
    entrar(s, visivel=true) { if (!this.desconectado) this.callback([{target:s,isIntersecting:visivel}]); }
  }
  let id=0;
  const janela = {
    innerHeight:800, matchMedia:()=>movimento,
    addEventListener:(k,cb)=>listeners[k]=cb,
    setTimeout: cb => {timers.set(++id,cb);return id;}, clearTimeout:k=>timers.delete(k),
    setInterval:cb=>{listeners.vigia=cb;return 99;}, clearInterval:()=>{listeners.vigia=null;},
  };
  if (!semObserver) janela.IntersectionObserver=Observer;
  vm.runInNewContext(script, {window:janela,IntersectionObserver:Observer,document:{
    querySelectorAll:()=>secoes, addEventListener:(k,cb)=>listeners[k]=cb,
  }});
  return {secoes,observer,listeners,movimento,timers};
}
for (const opcoes of [{reduzido:true},{semObserver:true},{falha:true}]) {
  const {secoes,observer}=iniciar(opcoes);
  assert.ok(secoes.every(s=>!s.classList.contains('home-scroll-pending')));
  if (opcoes.falha) assert.ok(observer.desconectado);
}
{
  const {secoes,observer,listeners,timers}=iniciar();
  assert.equal(observer.options.rootMargin,'0px 0px -24px 0px');
  assert.equal(observer.observadas.length,4);
  assert.ok(!secoes[0].classList.contains('home-scroll-pending')); // Inicial imediato.
  const s=secoes[1];
  assert.ok(s.classList.contains('home-scroll-pending'));
  assert.equal(s.filhos[0].props.get('--reveal-delay'),'100ms');
  assert.equal(s.filhos[1].props.get('--reveal-delay'),'200ms');
  observer.entrar(s,false);
  assert.ok(s.classList.contains('home-scroll-pending'));
  observer.entrar(s);
  assert.ok(!s.classList.contains('home-scroll-pending'));
  assert.ok(s.classList.contains('home-scroll-entering'));
  for (const cb of [...timers.values()]) cb();
  assert.ok(!s.classList.contains('home-scroll-entering'));
  assert.ok(s.filhos.every(x=>!x.classList.contains('home-scroll-child')));
  observer.entrar(s);
  assert.ok(!s.classList.contains('home-scroll-entering')); // So uma vez.
  listeners.focusin({target:secoes[2]});
  assert.ok(!secoes[2].classList.contains('home-scroll-pending'));
  secoes[3].ancora=true;
  listeners.hashchange();
  assert.ok(!secoes[3].classList.contains('home-scroll-pending'));
  secoes[4].top=600;
  listeners.vigia(); // Recuperacao se observer nao disparar.
  assert.ok(secoes[4].classList.contains('home-scroll-entering'));
}
{
  const {secoes,observer,listeners,movimento}=iniciar();
  movimento.matches=true;
  listeners.motion({matches:true});
  assert.ok(observer.desconectado);
  assert.ok(secoes.every(s=>!s.classList.contains('home-scroll-pending')));
}
console.log('Reveal: entrada na viewport, sequencia, uma vez, foco, ancora, vazio, reduced-motion e recuperacao OK.');
