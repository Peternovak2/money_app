const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fonte = fs.readFileSync('app/static/js/home.js', 'utf8');
const script = fonte.slice(fonte.indexOf('(function () {', fonte.indexOf('Dashboard:')));
function elemento(dataset = {}) {
  const classes = new Set();
  return {
    children: [], append(...items) { this.children.push(...items); },
    dataset, value: '', textContent: '', attrs: {}, listeners: {},
    classList: { add: x => classes.add(x), toggle(x, valor) { valor ? classes.add(x) : classes.delete(x); } },
    setAttribute(nome, valor) { this.attrs[nome] = valor; },
    removeAttribute(nome) { delete this.attrs[nome]; },
    focus() { elementoAtivo = this; },
    scrollIntoView(opcoes) { this.rolagem = opcoes; },
    addEventListener(nome, callback) { this.listeners[nome] = callback; },
    click() { return this.listeners.click(); },
    remove() { this.removido = true; },
    contains(alvo) { return alvo === this; },
  };
}
function criarCard(dataset) {
  const card = elemento(dataset);
  card.valor = elemento(); card.variacao = elemento(); card.direcao = elemento();
  card.badge = elemento(); card.ticker = elemento(); card.nome = elemento();
  card.querySelector = seletor => seletor === '[data-index-value]' ? card.valor
    : seletor === '[data-index-direction]' ? card.direcao
    : seletor === '.index-summary__badge' ? card.badge
    : seletor === '.index-summary__ticker' ? card.ticker
    : seletor === '.sr-only' ? card.nome : card.variacao;
  card.cloneNode = () => criarCard({...card.dataset});
  return card;
}
let cards = [['^BVSP', 'Ibovespa', 'IBOV'], ['^GSPC', 'S&P 500', 'SPX'], ['^NDX', 'Nasdaq 100', 'NDX']]
  .map(([indexSymbol, indexName, indexTicker]) => criarCard({indexSymbol, indexName, indexTicker}));
if (process.env.INDEX_MODE) cards = cards.slice(0,1);
const periodos = ['1mo', '6mo', '1y'].map(ibovPeriodo => elemento({ ibovPeriodo }));
const controles = [-1, 1].map(indicesScroll => elemento({ indicesScroll }));
const ids = Object.fromEntries(['dashboard-index-icon', 'dashboard-index-monogram', 'dashboard-ibov-body', 'dashboard-ibov-canvas', 'dashboard-ibov-status',
  'dashboard-ibov-price', 'dashboard-ibov-change', 'dashboard-ibov-period-label',
  'dashboard-ibov-timestamp', 'indice-ibov-contexto', 'dashboard-titulo', 'indices-carousel'].map(id => [id, elemento()]));
let elementoAtivo = null;
const armazenamento = new Map();
if (process.env.INDEX_MODE === 'restore') armazenamento.set('money-app.indices.v1', JSON.stringify(['^DJI','invalid','^DJI','^BVSP','^GDAXI']));
const observadores = [];
class Observer {
  constructor(callback) { this.callback = callback; observadores.push(this); }
  observe(alvo) { this.alvo = alvo; }
}
const carousel = ids['indices-carousel'];
const adicionados = [];
carousel.append = wrapper => adicionados.push(wrapper.children[0]);
const eventosDocumento = {};
for (const id of ['indices-add-toggle', 'indices-add-panel', 'indices-picker-search',
  'indices-picker-close', 'indices-picker-empty', 'indices-picker-status']) ids[id] = elemento();
ids['indices-add-panel'].hidden = true;
const opcoes = [['^BVSP', 'Ibovespa', 'IBOV'], ['^DJI', 'Dow Jones', 'DJI'],
  ['^GDAXI', 'DAX', 'DAX'], ['', 'Dólar / USD-BRL', 'USD-BRL']].map(([indexOption, optionName, optionTicker]) => {
  const opcao = elemento({indexOption, optionName, optionTicker, optionBadge: optionTicker});
  opcao.acao = elemento();
  opcao.querySelector = () => opcao.acao;
  return opcao;
});
ids['indices-add-panel'].querySelectorAll = () => opcoes;
ids['indices-add-panel'].contains = alvo => [ids['indices-add-panel'], ids['indices-picker-search'],
  ids['indices-picker-close'], ...opcoes].includes(alvo);
Object.assign(carousel, { scrollLeft: 0, clientWidth: 300, scrollWidth: 900,
  focus() { this.recebeuFoco = true; elementoAtivo = this; },
  scrollBy(opcoes) { this.ultimaRolagem = opcoes; } });
const nome = elemento();
const imagem = elemento();
const pendentes = [];
const grafico = { clear() { this.opcoes = null; }, setOption(opcoes) { this.opcoes = opcoes; }, resize() { this.redimensionamentos = (this.redimensionamentos || 0) + 1; } };
let reduzido = false;
vm.runInNewContext(script, {
  console, Intl, URLSearchParams, AbortController, getComputedStyle: () => ({ fontFamily: 'sans-serif' }),
  requestAnimationFrame: callback => callback(), ResizeObserver: Observer,
  window: { localStorage: {getItem:k=>{if(process.env.INDEX_MODE==='blocked') throw Error('blocked');return armazenamento.get(k);},setItem:(k,v)=>armazenamento.set(k,v)}, ResizeObserver: Observer, echarts: { init: () => grafico }, addEventListener() {}, matchMedia: () => ({ matches: reduzido }) },
  document: {
    readyState: 'complete', body: {}, createElement: () => elemento(),
    get activeElement() { return elementoAtivo; },
    getElementById: id => ids[id], querySelector: () => nome,
    addEventListener: (nome, callback) => eventosDocumento[nome] = callback,
    querySelectorAll: seletor => seletor === '[data-index-symbol]' ? cards
      : seletor === '[data-ibov-periodo]' ? periodos
      : seletor === '[data-indices-scroll]' ? controles : [imagem],
  },
  fetch(url, opcoes) { return new Promise(resolve => pendentes.push({ url, opcoes, resolve })); },
});
const pontos = [100, 120].map((close, i) => ({ close, time: `2026-11-0${i + 1}` }));
async function responder(req, simbolo, valores = pontos, ok = true) {
  req.resolve({ ok, status: ok ? 200 : 502, json: async () => ({ ticker: simbolo, pontos: valores }) });
  await new Promise(resolve => setImmediate(resolve));
}
const atual = () => pendentes.at(-1);
(async () => {
  if (process.env.INDEX_MODE) {
    const restaurados = process.env.INDEX_MODE === 'restore';
    assert.equal(adicionados.length, restaurados ? 2 : 0);
    assert.equal(pendentes.length, restaurados ? 3 : 1);
    if (restaurados) assert.deepEqual(adicionados.map(c=>c.dataset.indexSymbol), ['^DJI','^GDAXI']);
    assert.match(atual().url, /%5EBVSP/);
    console.log('Preferencias: estado inicial, restauracao, ordem, duplicatas e armazenamento bloqueado OK.');
    return;
  }

  imagem.listeners.error(); assert.equal(imagem.removido, true);
  assert.match(atual().url, /%5EBVSP.*6mo/);
  await responder(atual(), '^BVSP');
  assert.equal(ids['dashboard-ibov-price'].textContent, '120,00');
  assert.equal(grafico.opcoes.series[0].name, 'Ibovespa');
  assert.equal(ids['dashboard-titulo'].textContent, 'Ibovespa');
  assert.equal(nome.textContent, 'IBOV');
  assert.equal(ids['dashboard-ibov-change'].textContent, '+20,00%');
  assert.equal(cards[0].variacao.textContent, '+20,00%');
  assert.equal(cards[0].direcao.textContent, '↗');
  assert.match(cards[0].title, /6 meses/);
  assert.equal(ids['dashboard-ibov-period-label'].textContent, '6 meses');
  assert.equal(ids['dashboard-ibov-timestamp'].textContent, 'Fechamento · 02/11/2026');
  await responder(pendentes[0], '^GSPC', [], false);
  assert.match(cards[1].variacao.textContent, /indisponível/);
  assert.equal(controles[0].hidden, true);
  assert.equal(controles[1].hidden, false);
  carousel.scrollLeft = 5; carousel.listeners.scroll();
  assert.equal(controles[0].hidden, false);
  carousel.scrollLeft = 600; elementoAtivo = controles[1]; carousel.listeners.scroll();
  assert.equal(controles[1].hidden, true);
  assert.equal(carousel.recebeuFoco, true);
  carousel.clientWidth = 900;
  observadores.find(o => o.alvo === carousel).callback();
  assert.ok(controles.every(controle => controle.hidden));
  carousel.clientWidth = 300; carousel.scrollLeft = 0; carousel.listeners.scroll();
  const mudarFoco = (key, target) => {
    const evento = { key, target, preventDefault() { this.cancelado = true; } };
    carousel.listeners.keydown(evento);
    assert.equal(evento.cancelado, true);
  };
  const pedidosAntesDoTeclado = pendentes.length;
  mudarFoco('ArrowRight', cards[0]);
  assert.equal(elementoAtivo, cards[1]);
  assert.equal(cards[1].attrs.tabindex, '0');
  assert.equal(pendentes.length, pedidosAntesDoTeclado); // Foco não seleciona nem consulta.
  mudarFoco('End', cards[1]); assert.equal(elementoAtivo, cards[2]);
  mudarFoco('Home', cards[2]); assert.equal(elementoAtivo, cards[0]);
  mudarFoco('ArrowLeft', cards[0]); assert.equal(elementoAtivo, cards[2]);
  assert.equal(cards[2].rolagem.behavior, 'smooth');
  reduzido = true;
  mudarFoco('Home', cards[2]); assert.equal(cards[0].rolagem.behavior, 'auto');
  reduzido = false;
  const antes = grafico.redimensionamentos;
  observadores.find(o => o.alvo === ids['dashboard-ibov-body']).callback();
  assert.equal(grafico.redimensionamentos, antes + 1);
  assert.equal(controles[0].disabled, true);
  assert.equal(controles[1].disabled, false);
  controles[1].click(); assert.equal(carousel.ultimaRolagem.behavior, 'smooth');
  assert.ok(carousel.ultimaRolagem.left > 0 && carousel.ultimaRolagem.left < 240);
  reduzido = true; controles[1].click(); assert.equal(carousel.ultimaRolagem.behavior, 'auto');
  cards[1].click(); const antigo = atual();
  assert.equal(ids['dashboard-ibov-price'].textContent, '—');
  assert.equal(grafico.opcoes, null);
  assert.equal(nome.textContent, 'SPX');
  assert.equal(ids['dashboard-titulo'].textContent, 'S&P 500');
  assert.equal(ids['dashboard-index-monogram'].textContent, 'SPX');
  assert.equal(ids['dashboard-index-icon'].dataset.headerIndex, '^GSPC');
  cards[2].click(); const novo = atual();
  assert.ok(antigo.opcoes.signal.aborted);
  await responder(novo, '^NDX', pontos.map(p => ({ ...p, close: p.close * 2 })));
  assert.equal(ids['dashboard-ibov-price'].textContent, '240,00');
  await responder(antigo, '^GSPC'); // Mesmo ignorando abort, a resposta antiga não pode vencer.
  assert.equal(ids['dashboard-ibov-price'].textContent, '240,00');
  assert.equal(ids['dashboard-titulo'].textContent, 'Nasdaq 100');
  assert.equal(cards[2].attrs['aria-pressed'], 'true');
  assert.equal(cards[1].attrs['aria-pressed'], 'false');
  periodos[2].click(); assert.match(atual().url, /%5ENDX.*1y/);
  assert.equal(ids['dashboard-ibov-period-label'].textContent, '1 ano');
  await responder(atual(), '^NDX', [], false);
  assert.equal(ids['dashboard-ibov-body'].dataset.estado, 'erro');
  assert.equal(ids['dashboard-ibov-price'].textContent, '—');
  cards[0].click(); assert.equal(ids['dashboard-index-icon'].dataset.headerIndex, '^BVSP'); assert.match(atual().url, /%5EBVSP.*1y/);
  await responder(atual(), '^BVSP', []);
  assert.equal(ids['dashboard-ibov-body'].dataset.estado, 'vazio');
  cards[0].click(); await responder(atual(), '^GSPC');
  assert.equal(ids['dashboard-ibov-body'].dataset.estado, 'erro'); // Identidade inconsistente.
  cards[0].click(); await responder(atual(), '^BVSP', [pontos[0]]);
  assert.equal(ids['dashboard-ibov-body'].dataset.estado, 'sucesso');
  assert.equal(ids['dashboard-ibov-price'].textContent, '100,00');
  assert.equal(ids['dashboard-ibov-change'].textContent, '');
  // Uma consulta paralela indisponível não interfere no gráfico selecionado.
  await responder(pendentes[0], '^GSPC', [], false);
  assert.equal(ids['dashboard-ibov-body'].dataset.estado, 'sucesso');
  await responder(pendentes[1], '^NDX');
  assert.match(cards[2].variacao.textContent, /indisponível/);
  assert.equal(ids['dashboard-ibov-price'].textContent, '100,00');
  // Painel: abrir, buscar, navegar, adicionar e reutilizar o gráfico real.
  const abrir = ids['indices-add-toggle'];
  const painel = ids['indices-add-panel'];
  const busca = ids['indices-picker-search'];
  assert.equal(abrir.hidden, false);
  abrir.click();
  assert.equal(abrir.attrs['aria-expanded'], 'true');
  assert.equal(elementoAtivo, busca);
  assert.ok(opcoes[0].disabled);
  assert.match(opcoes[0].acao.textContent, /Já adicionado/);
  assert.ok(opcoes[3].disabled);
  busca.value = 'DOLAR'; busca.listeners.input();
  assert.equal(opcoes[3].hidden, false); // Busca sem acentos.
  assert.ok(opcoes.slice(0, 3).every(opcao => opcao.hidden));
  busca.value = 'inexistente'; busca.listeners.input();
  assert.equal(ids['indices-picker-empty'].hidden, false);
  busca.value = ''; busca.listeners.input();
  painel.listeners.keydown({key:'ArrowDown', preventDefault(){}});
  assert.equal(elementoAtivo, opcoes[1]);
  painel.listeners.keydown({key:'ArrowDown', preventDefault(){}});
  assert.equal(elementoAtivo, opcoes[2]);
  painel.listeners.keydown({key:'Escape', preventDefault(){}});
  assert.equal(painel.hidden, true);
  assert.equal(elementoAtivo, abrir);
  abrir.click();
  const antesAdicionar = pendentes.length;
  opcoes[1].click();
  assert.equal(adicionados.length, 1);
  const novoCard = adicionados[0];
  assert.equal(novoCard.dataset.indexSymbol, '^DJI');
  assert.equal(novoCard.nome.textContent, 'Dow Jones');
  assert.equal(novoCard.ticker.textContent, 'DJI');
  assert.equal(elementoAtivo, novoCard);
  assert.equal(painel.hidden, true);
  assert.equal(abrir.attrs['aria-expanded'], 'false');
  assert.equal(pendentes.length, antesAdicionar + 1);
  assert.match(atual().url, /%5EDJI.*1y/); // Mantém período selecionado.
  await responder(atual(), '^DJI');
  assert.equal(ids['dashboard-titulo'].textContent, 'Dow Jones');
  assert.equal(grafico.opcoes.series[0].name, 'Dow Jones');
  assert.equal(novoCard.attrs['aria-pressed'], 'true');
  assert.equal(novoCard.variacao.textContent, '+20,00%');
  abrir.click();
  assert.equal(adicionados.length, 1); // Sem duplicatas nem outra consulta.
  assert.equal(pendentes.length, antesAdicionar + 1);
  eventosDocumento.click({target:{}});
  assert.equal(painel.hidden, true);
  abrir.click(); eventosDocumento.focusin({target:{}});
  assert.equal(painel.hidden, true);
  abrir.click(); ids['indices-picker-close'].click();
  assert.equal(elementoAtivo, abrir);
  mudarFoco('End', cards[0]);
  assert.equal(elementoAtivo, novoCard); // Novo índice participa do teclado.
  periodos[0].click();
  assert.match(atual().url, /%5EDJI.*1mo/);
  await responder(atual(), '^DJI', [], false);
  assert.equal(ids['dashboard-ibov-body'].dataset.estado, 'erro');
  cards[0].click(); await responder(atual(), '^BVSP');
  novoCard.click();
  assert.match(atual().url, /%5EDJI.*1mo/); // Listener registrado no card adicionado.
  await responder(atual(), '^DJI');
  abrir.click(); opcoes[2].click();
  assert.equal(adicionados.length, 2);
  assert.match(atual().url, /%5EGDAXI.*1mo/);
  await responder(atual(), '^GDAXI');
  assert.equal(ids['dashboard-titulo'].textContent, 'DAX');
  assert.equal(novoCard.attrs['aria-pressed'], 'false');
  assert.equal(adicionados[1].attrs['aria-pressed'], 'true');
  assert.ok(JSON.parse(armazenamento.get('money-app.indices.v1')).includes('^GDAXI'));
  const pedidosAntesRemover = pendentes.length;
  let propagacaoBloqueada = false;
  adicionados[1].indiceWrapper.children[1].listeners.click({preventDefault(){},stopPropagation(){propagacaoBloqueada=true;}});
  assert.equal(propagacaoBloqueada, true);
  assert.equal(pendentes.length, pedidosAntesRemover + 1);
  assert.equal(adicionados[1].indiceWrapper.removido, true);
  assert.equal(adicionados[1].removido, true);
  assert.match(atual().url, /%5EBVSP/);
  assert.ok(!JSON.parse(armazenamento.get('money-app.indices.v1')).includes('^GDAXI'));
  assert.equal(opcoes[0].disabled, true);
  const pedidosAntesInativo = pendentes.length;
  novoCard.indiceWrapper.children[1].listeners.click({preventDefault(){},stopPropagation(){}});
  assert.equal(pendentes.length, pedidosAntesInativo);
  assert.ok(!JSON.parse(armazenamento.get('money-app.indices.v1')).includes('^DJI'));
  assert.equal(cards[0].indiceWrapper, undefined);
  assert.equal(novoCard.indiceWrapper.children[1].attrs['aria-label'], 'Remover DJI');
  abrir.click(); assert.equal(opcoes[1].disabled, false);
  console.log('Índices: seleção, períodos, cancelamento, respostas antigas, falhas, vazio, identidade, carrossel e movimento reduzido OK.');
})().catch(erro => { console.error(erro); process.exitCode = 1; });
