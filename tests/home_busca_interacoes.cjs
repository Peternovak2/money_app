const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fonte = fs.readFileSync('app/static/js/home.js', 'utf8');
const script = fonte.slice(0, fonte.indexOf('function definirMenuAberto'))
  + fonte.slice(fonte.indexOf('const categoriasBusca'), fonte.indexOf('/* ====================================================================='));
function iniciar() {
  const documento = { activeElement: null, listeners: {}, addEventListener(n, f) { this.listeners[n] = f; } };
  class Elemento {
    constructor(tag = 'div') { Object.assign(this, { tag, children: [], attrs: {}, dataset: {}, listeners: {}, hidden: false, value: '', textContent: '' }); }
    setAttribute(n, v) { this.attrs[n] = v; }
    removeAttribute(n) { delete this.attrs[n]; }
    addEventListener(n, f) { (this.listeners[n] ||= []).push(f); }
    emitir(n, dados = {}) {
      const evento = { target: this, preventDefault() { this.prevented = true; }, ...dados };
      for (const fn of this.listeners[n] || []) fn(evento);
      return evento;
    }
    append(...elementos) {
      for (const el of elementos) {
        if (el.tag === 'fragment') this.append(...el.children);
        else { el.parentElement = this; this.children.push(el); }
      }
    }
    replaceChildren(...els) { this.children = []; this.append(...els); }
    contains(el) { return el === this || this.children.some(filho => filho.contains(el)); }
    querySelectorAll() {
      return this.children.flatMap(el => [...(el.attrs.role === 'option' ? [el] : []), ...el.querySelectorAll()]);
    }
    focus() { documento.activeElement = this; this.emitir('focus'); }
    scrollIntoView() {}
    remove() { this.parentElement.children = this.parentElement.children.filter(el => el !== this); }
  }
  const ids = Object.fromEntries(['formBusca', 'tickerInput', 'painelSugestoes', 'sugestoesAtivos',
    'mensagemSugestoes', 'buscaStatus', 'fecharBusca', 'tituloBusca'].map(id => [id, new Elemento()]));
  ids.painelSugestoes.hidden = true;
  const categorias = ['todos', 'acao'].map(searchCategory => Object.assign(new Elemento('button'), { dataset: { searchCategory } }));
  ids.formBusca.append(ids.tickerInput, ids.painelSugestoes);
  ids.painelSugestoes.append(ids.fecharBusca, ...categorias, ids.sugestoesAtivos);
  documento.getElementById = id => ids[id] || null;
  documento.querySelector = () => null;
  documento.querySelectorAll = () => categorias;
  documento.createElement = tag => new Elemento(tag);
  documento.createDocumentFragment = () => new Elemento('fragment');
  const pedidos = [];
  const timers = new Map(); let timer = 0;
  const janela = { location: { href: '' }, addEventListener() {},
    setTimeout(fn) { timers.set(++timer, fn); return timer; }, clearTimeout(id) { timers.delete(id); } };
  const contexto = vm.createContext({ document: documento, window: janela, URL, URLSearchParams, AbortController, Date,
    fetch(url, opcoes) { return new Promise(resolve => pedidos.push({ url, opcoes, resolve })); } });
  vm.runInContext(script, contexto);
  return { ids, categorias, documento, pedidos, janela, contexto,
    digitar(valor) { ids.tickerInput.value = valor; ids.tickerInput.emitir('input'); },
    executarTimers() { for (const [id, fn] of timers) { timers.delete(id); fn(); } },
    timers,
  };
}
const acoes = [
  { ticker: 'PETR4', nome: 'Petrobras PN', tipo: 'acao', logo_url: 'https://icons.brapi.dev/icons/PETR4.svg' },
  { ticker: 'PETR3', nome: 'Petrobras ON', tipo: 'acao' },
  { ticker: 'VALE3', nome: 'Vale ON', tipo: 'acao', logo_url: 'https://evil.example/logo.svg' },
];
async function responder(pedido, dados = acoes, ok = true) {
  pedido.resolve({ ok, status: ok ? 200 : 503, json: async () => dados });
  await new Promise(resolve => setImmediate(resolve));
}
(async () => {
  let app = iniciar(); let { ids } = app;
  ids.tickerInput.emitir('click'); assert.equal(ids.painelSugestoes.hidden, false);
  assert.match(app.pedidos[0].url, /descoberta/);
  await responder(app.pedidos[0]);
  assert.equal(ids.tickerInput.attrs['aria-expanded'], 'true');
  assert.equal(ids.sugestoesAtivos.children.length, 3);
  assert.equal(ids.sugestoesAtivos.children[0].children[0].children[0].src, acoes[0].logo_url);
  assert.equal(ids.sugestoesAtivos.children[2].children[0].children.length, 0);
  const img = ids.sugestoesAtivos.children[0].children[0].children[0]; img.emitir('error');
  assert.equal(ids.sugestoesAtivos.children[0].children[0].children.length, 0);
  ids.tickerInput.emitir('keydown', { key: 'ArrowUp' });
  assert.equal(ids.tickerInput.attrs['aria-activedescendant'], 'sugestao-ativo-2');
  ids.tickerInput.emitir('keydown', { key: 'ArrowDown' });
  assert.equal(ids.tickerInput.attrs['aria-activedescendant'], 'sugestao-ativo-0');
  assert.ok(!ids.tickerInput.emitir('keydown', { key: 'Tab' }).prevented);
  ids.tickerInput.emitir('keydown', { key: 'ArrowDown' });
  ids.tickerInput.emitir('keydown', { key: 'Enter' });
  assert.equal(app.janela.location.href, '/ativo/PETR4');
  ids.tickerInput.emitir('click'); assert.equal(app.pedidos.length, 1); // Cache de descoberta.
  ids.formBusca.emitir('focusout', { relatedTarget: null }); assert.equal(ids.painelSugestoes.hidden, false);
  ids.sugestoesAtivos.children[1].emitir('click'); assert.equal(app.janela.location.href, '/ativo/PETR3');

  app = iniciar(); ids = app.ids;
  app.digitar('P'); app.digitar('PETR'); assert.equal(app.timers.size, 1);
  app.executarTimers(); const antigo = app.pedidos.at(-1);
  ids.tickerInput.emitir('keydown', { key: 'Escape' });
  assert.ok(antigo.opcoes.signal.aborted);
  await responder(antigo); assert.equal(ids.painelSugestoes.hidden, true);
  app.digitar('VALE'); app.executarTimers(); const fora = app.pedidos.at(-1);
  app.documento.listeners.pointerdown({ target: {} });
  await responder(fora); assert.equal(ids.painelSugestoes.hidden, true);
  app.digitar('PETR'); app.executarTimers(); const atrasado = app.pedidos.at(-1);
  app.digitar('VALE'); app.executarTimers(); const recente = app.pedidos.at(-1);
  await responder(recente, [acoes[2]]); await responder(atrasado);
  assert.equal(ids.sugestoesAtivos.children.length, 1);
  assert.equal(ids.sugestoesAtivos.children[0].children[1].children[0].textContent, 'VALE3');
  ids.formBusca.emitir('focusout', { relatedTarget: {} }); assert.equal(ids.painelSugestoes.hidden, true);

  app = iniciar(); ids = app.ids;
  app.digitar('Petrobras'); app.executarTimers(); await responder(app.pedidos.at(-1), acoes.slice(0, 2));
  ids.formBusca.emitir('submit'); assert.equal(app.janela.location.href, '');
  assert.match(ids.mensagemSugestoes.textContent, /Selecione/);
  app.categorias[1].emitir('click'); assert.match(app.pedidos.at(-1).url, /categoria=acao/);
  await responder(app.pedidos.at(-1), acoes.slice(0, 2));
  assert.equal(app.categorias[1].attrs['aria-pressed'], 'true');
  ids.formBusca.emitir('keydown', { key: 'Escape', target: app.categorias[1] });
  assert.equal(ids.painelSugestoes.hidden, true);
  app.digitar('PETR4'); ids.formBusca.emitir('submit');
  await responder(app.pedidos.at(-1), acoes.slice(0, 2));
  assert.equal(app.janela.location.href, '/ativo/PETR4');

  app = iniciar(); ids = app.ids;
  app.digitar('VALE'); app.executarTimers(); await responder(app.pedidos.at(-1), [], false);
  assert.equal(ids.painelSugestoes.dataset.state, 'error');
  ids.tickerInput.emitir('click'); await responder(app.pedidos.at(-1), []);
  assert.equal(ids.painelSugestoes.dataset.state, 'empty');
  ids.fecharBusca.emitir('click'); assert.equal(ids.painelSugestoes.hidden, true);
  for (const url of ['javascript:alert(1)', '//icons.brapi.dev/x.svg', 'https://icons.brapi.dev.evil.example/x.svg',
    'https://x@icons.brapi.dev/x.svg', 'https://icons.brapi.dev:444/x.svg']) assert.equal(app.contexto.logoPermitido(url), null);
  console.log('Busca: descoberta, cache, debounce, teclado, mouse, cancelamento, concorrência, categorias, ambiguidades, logos e estados OK.');
})().catch(erro => { console.error(erro); process.exitCode = 1; });
