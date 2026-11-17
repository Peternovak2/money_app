const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");

function executarModo(sidebarDesativada) {
  const documento = { activeElement: null, listeners: {}, addEventListener(nome, fn) { this.listeners[nome] = fn; } };
  function elemento() {
    return {
      attrs: {}, dataset: {}, listeners: {},
      setAttribute(nome, valor) { this.attrs[nome] = valor; },
      getAttribute(nome) { return this.attrs[nome]; },
      addEventListener(nome, fn) { this.listeners[nome] = fn; },
      focus() { documento.activeElement = this; },
    };
  }
  const botao = elemento();
  botao.setAttribute("aria-expanded", "false");
  const lateral = elemento();
  const primeiroLink = elemento();
  const destino = elemento();
  const menu = elemento();
  menu.querySelector = () => primeiroLink;
  menu.contains = (el) => el === primeiroLink;
  botao.contains = (el) => el === botao;
  documento.getElementById = (id) => id === "sidebarToggle" ? lateral : elemento();
  documento.querySelector = (seletor) => ({
    "[data-home-menu-toggle]": botao,
    "[data-home-menu]": menu,
    "#mercado": destino,
  }[seletor]);
  documento.body = { classList: { contains: () => sidebarDesativada } };
  let mudouViewport;
  const janela = { matchMedia: () => ({ addEventListener: (_, fn) => { mudouViewport = fn; } }) };
  const script = fs.readFileSync("app/static/js/home.js", "utf8");
  vm.runInNewContext(script.slice(0, script.indexOf("function atualizarSecaoAtiva")), {
    document: documento, window: janela,
  });

  botao.listeners.click();
  assert.equal(menu.dataset.open, "true");
  assert.equal(documento.activeElement, primeiroLink);
  documento.listeners.keydown({ key: "Escape" });
  assert.equal(menu.dataset.open, "false");
  assert.equal(documento.activeElement, botao);

  botao.listeners.click();
  mudouViewport({ matches: true });
  assert.equal(menu.dataset.open, "false");
  assert.equal(documento.activeElement, sidebarDesativada ? botao : primeiroLink);
  botao.focus();
  mudouViewport({ matches: true });
  assert.equal(documento.activeElement, sidebarDesativada ? botao : lateral);

  botao.listeners.click();
  menu.listeners.click({ target: { closest: () => ({ hash: "#mercado" }) } });
  assert.equal(menu.dataset.open, "false");
  assert.equal(documento.activeElement, destino);

  botao.listeners.click();
  documento.listeners.pointerdown({ target: {} });
  assert.equal(menu.dataset.open, "false");
  assert.equal(documento.activeElement, botao);
}

executarModo(true);
executarModo(false);
console.log("Navegação preservada nos modos com e sem sidebar.");
