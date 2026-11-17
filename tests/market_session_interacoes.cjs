const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const fonte = fs.readFileSync('app/static/js/market-session.js', 'utf8');
function iniciar() {
  const texto = { textContent: '' };
  const indicador = { dataset: {}, attrs: {}, querySelector: () => texto,
    setAttribute(nome, valor) { this.attrs[nome] = valor; } };
  const documento = { hidden: false, listeners: {}, getElementById: () => indicador,
    addEventListener(nome, callback) { this.listeners[nome] = callback; } };
  const timers = new Map(); let numero = 0;
  const janela = { listeners: {}, setTimeout(fn, delay) { timers.set(++numero, { fn, delay }); return numero; },
    clearTimeout(id) { timers.delete(id); }, addEventListener(nome, callback) { this.listeners[nome] = callback; } };
  const pedidos = [];
  vm.runInNewContext(fonte, { document: documento, window: janela, AbortController,
    fetch(url, opcoes) { assert.equal(url, '/api/mercado/sessao'); return new Promise(resolve => pedidos.push({ opcoes, resolve })); } });
  return { texto, indicador, documento, janela, timers, pedidos };
}
async function responder(pedido, status = 'aberto', ok = true, extra = {}) {
  pedido.resolve({ ok, json: async () => ({ status, referencia: '2026-11-12T10:00:00-03:00',
    escopo: 'sessao_regular_acoes_b3', atualizar_em: 60, ...extra }) });
  await new Promise(resolve => setImmediate(resolve));
}
(async () => {
  let app = iniciar();
  await responder(app.pedidos[0]);
  assert.equal(app.texto.textContent, 'Aberto');
  assert.equal(app.indicador.dataset.status, 'aberto');
  assert.match(app.indicador.attrs['aria-label'], /Sessão regular/);
  assert.equal([...app.timers.values()][0].delay, 60000);
  app.documento.hidden = true; app.documento.listeners.visibilitychange();
  assert.equal(app.timers.size, 0); assert.equal(app.texto.textContent, 'Status indisponível');
  app.documento.hidden = false; app.documento.listeners.visibilitychange();
  const antigo = app.pedidos.at(-1);
  app.documento.hidden = true; app.documento.listeners.visibilitychange();
  assert.ok(antigo.opcoes.signal.aborted);
  app.documento.hidden = false; app.documento.listeners.visibilitychange();
  await responder(app.pedidos.at(-1), 'fechado', true, { atualizar_em: 300 });
  await responder(antigo, 'aberto');
  assert.equal(app.texto.textContent, 'Fechado');
  assert.equal([...app.timers.values()][0].delay, 300000);
  app.janela.listeners.pagehide(); assert.equal(app.timers.size, 0);
  app.janela.listeners.pageshow({ persisted: true });
  await responder(app.pedidos.at(-1), 'leilao'); // Relógio/calendário não confirmam leilão.
  assert.equal(app.texto.textContent, 'Status indisponível');
  app = iniciar();
  [...app.timers.values()].find(timer => timer.delay === 8000).fn();
  assert.ok(app.pedidos[0].opcoes.signal.aborted);
  await responder(app.pedidos[0]);
  assert.equal(app.texto.textContent, 'Status indisponível');
  app = iniciar(); await responder(app.pedidos[0], 'aberto', false);
  assert.equal(app.texto.textContent, 'Status indisponível');
  app = iniciar(); await responder(app.pedidos[0], 'aberto', true, { escopo: 'outro_mercado' });
  assert.equal(app.texto.textContent, 'Status indisponível');
  console.log('Sessão: atualização, pausa, timeout, erro, escopo e respostas antigas OK.');
})().catch(erro => { console.error(erro); process.exitCode = 1; });
