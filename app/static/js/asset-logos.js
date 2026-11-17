(() => {
  document.querySelectorAll("[data-asset-logo]").forEach(imagem => {
    imagem.addEventListener("error", () => imagem.remove(), { once: true });
    if (imagem.complete && !imagem.naturalWidth) imagem.remove();
  });
})();
