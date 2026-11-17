const rankingBackButton = document.querySelector("[data-ranking-back]");

if (rankingBackButton) {
  rankingBackButton.addEventListener("click", () => {
    const fallbackUrl = rankingBackButton.dataset.fallbackUrl || "/";

    if (window.history.length > 1) {
      window.history.back();
      return;
    }

    window.location.assign(fallbackUrl);
  });
}
