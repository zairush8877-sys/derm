// Aura site-helper: токен аккаунта во всех запросах + общий каркас дизайна
// (бегущая строка офферов, логотип-бар, плавающая кнопка ассистента).
// Подключается ДО скрипта страницы.
(function () {
  "use strict";
  const token = localStorage.getItem("aura_token");

  if (token) {
    const orig = window.fetch.bind(window);
    window.fetch = (url, opts = {}) => {
      opts.headers = Object.assign({}, opts.headers, { Authorization: "Bearer " + token });
      return orig(url, opts);
    };
  }

  document.addEventListener("DOMContentLoaded", () => {
    // 1) Бегущая строка с офферами (стиль healf).
    const offers = [
      "Первый AI-скан — бесплатно",
      "Бесплатная доставка от 3 500 ₽",
      "Кешбэк баллами до 12%",
      "Пакет 20 сканов −20%",
    ];
    const ticker = document.createElement("div");
    ticker.className = "ticker";
    const items = offers.map((o) => `<span>• ${o}</span>`).join("");
    ticker.innerHTML = `<div class="track">${items}${items}</div>`;
    document.body.insertBefore(ticker, document.body.firstChild);

    // 2) Логотип-бар: aura. по центру, профиль и корзина справа.
    const bar = document.createElement("div");
    bar.className = "logobar";
    const profileHref = "/auth";
    const profileIcon = token ? "👤" : "👤";
    bar.innerHTML =
      `<span style="width:70px"></span>` +
      `<a class="logo" href="/">aura</a>` +
      `<span class="icons">` +
      `<a href="${profileHref}" title="${token ? (localStorage.getItem("aura_name") || "Профиль") : "Войти"}">${profileIcon}</a>` +
      `<a href="/shop#cartCard" title="Корзина">🛍</a>` +
      `</span>`;
    document.body.insertBefore(bar, ticker.nextSibling);

    // 3) Плавающая кнопка ассистента (кроме самой страницы ассистента).
    if (!location.pathname.startsWith("/assistant")) {
      const fab = document.createElement("a");
      fab.className = "fab";
      fab.href = "/assistant";
      fab.title = "Спросить Aura";
      fab.textContent = "💬";
      document.body.appendChild(fab);
    }

    // 4) Ссылка Войти/Профиль в навигации.
    const nav = document.querySelector("nav.tabs");
    if (nav) {
      const a = document.createElement("a");
      a.href = "/auth";
      a.textContent = token ? "👤 " + (localStorage.getItem("aura_name") || "Профиль") : "Войти";
      nav.appendChild(a);
    }
    const authLink = document.getElementById("authLink");
    if (authLink && token) authLink.parentElement.classList.add("hidden");
  });
})();
