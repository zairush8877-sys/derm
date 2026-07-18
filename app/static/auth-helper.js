// Aura site-helper: токен аккаунта во всех запросах + общий каркас дизайна
// (бегущая строка офферов, логотип-бар, плавающая кнопка ассистента).
// Подключается ДО скрипта страницы.
(function () {
  "use strict";
  const token = localStorage.getItem("aura_token");

  // Тема (день/ночь): применяем сразу, до отрисовки — без «мигания».
  const savedTheme = localStorage.getItem("aura_theme");
  if (savedTheme === "dark" ||
      (!savedTheme && window.matchMedia("(prefers-color-scheme: dark)").matches)) {
    document.documentElement.dataset.theme = "dark";
  }

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

    // Линейные SVG-иконки вместо эмодзи (наследуют цвет темы).
    const svg = (d) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><${d}/></svg>`;
    const ICONS = {
      moon: svg('path d="M21 12.8A9 9 0 1 1 11.2 3a7 7 0 0 0 9.8 9.8z"'),
      sun: svg('circle cx="12" cy="12" r="4"></circle><path d="M12 2v2M12 20v2M4.9 4.9l1.4 1.4M17.7 17.7l1.4 1.4M2 12h2M20 12h2M4.9 19.1l1.4-1.4M17.7 6.3l1.4-1.4"'),
      user: svg('path d="M20 21a8 8 0 0 0-16 0"></path><circle cx="12" cy="7" r="4"></circle'),
      bag: svg('path d="M6.5 7.5h11L18.5 21h-13l1-13.5z"></path><path d="M9 10V6.5a3 3 0 0 1 6 0V10"'),
      chat: svg('path d="M21 11.5a8.5 8.5 0 0 1-8.5 8.5c-1.2 0-2.4-.25-3.4-.7L4 20.5l1.2-4.1A8.5 8.5 0 1 1 21 11.5z"'),
    };

    // 2) Логотип-бар: aura. по центру, профиль и корзина справа.
    const bar = document.createElement("div");
    bar.className = "logobar";
    const profileHref = token ? "/account" : "/auth";
    const isDark = () => document.documentElement.dataset.theme === "dark";
    bar.innerHTML =
      `<a class="logo" href="/">aura</a>` +
      `<span class="icons">` +
      `<a class="theme-toggle" id="themeToggle" title="Тема: день/ночь">${isDark() ? ICONS.sun : ICONS.moon}</a>` +
      `<a href="${profileHref}" title="${token ? (localStorage.getItem("aura_name") || "Профиль") : "Войти"}">${ICONS.user}</a>` +
      `<a href="/shop#cartCard" title="Корзина">${ICONS.bag}</a>` +
      `</span>`;
    document.body.insertBefore(bar, ticker.nextSibling);
    document.getElementById("themeToggle").addEventListener("click", () => {
      const dark = !isDark();
      if (dark) document.documentElement.dataset.theme = "dark";
      else delete document.documentElement.dataset.theme;
      localStorage.setItem("aura_theme", dark ? "dark" : "light");
      document.getElementById("themeToggle").innerHTML = dark ? ICONS.sun : ICONS.moon;
    });

    // 3) Плавающая кнопка ассистента (кроме самой страницы ассистента).
    if (!location.pathname.startsWith("/assistant")) {
      const fab = document.createElement("a");
      fab.className = "fab";
      fab.href = "/assistant";
      fab.title = "Спросить Aura";
      fab.innerHTML = ICONS.chat;
      document.body.appendChild(fab);
    }

    // 4) Ссылка Войти/Профиль в навигации.
    const nav = document.querySelector("nav.tabs");
    if (nav) {
      const a = document.createElement("a");
      a.href = token ? "/account" : "/auth";
      a.textContent = token ? (localStorage.getItem("aura_name") || "Кабинет") : "Войти";
      nav.appendChild(a);
    }
    const authLink = document.getElementById("authLink");
    if (authLink && token) authLink.parentElement.classList.add("hidden");

    // 5) Появление карточек при скролле (прогрессивно: без JS всё видно сразу).
    if ("IntersectionObserver" in window &&
        !window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      const io = new IntersectionObserver((entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
        });
      }, { threshold: 0.08 });
      const animate = (els) => els.forEach((n, i) => {
        n.classList.add("reveal");
        n.style.transitionDelay = Math.min(i % 6, 4) * 60 + "ms";  // лёгкий каскад
        io.observe(n);
        // Страховка: что бы ни случилось, элемент не остаётся невидимым.
        setTimeout(() => n.classList.add("in"), 1500);
      });
      animate([...document.querySelectorAll(".card, .pcard")]);
      // Динамически добавленные карточки (магазин, кабинет) тоже анимируем.
      const mo = new MutationObserver((muts) => {
        const fresh = [];
        muts.forEach((m) => m.addedNodes.forEach((n) => {
          if (n.nodeType !== 1) return;
          if (n.matches && n.matches(".card, .pcard")) fresh.push(n);
          if (n.querySelectorAll) fresh.push(...n.querySelectorAll(".card, .pcard"));
        }));
        if (fresh.length) animate(fresh.filter((n) => !n.classList.contains("reveal")));
      });
      mo.observe(document.body, { childList: true, subtree: true });
    }
  });
})();
