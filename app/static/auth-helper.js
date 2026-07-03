// Aura auth-helper: добавляет токен аккаунта ко всем запросам страницы
// и показывает имя пользователя в навигации. Подключается ДО скрипта страницы.
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
    const nav = document.querySelector("nav.tabs");
    if (!nav) return;
    const a = document.createElement("a");
    if (token) {
      a.href = "/auth";
      a.textContent = "👤 " + (localStorage.getItem("aura_name") || "Профиль");
    } else {
      a.href = "/auth";
      a.textContent = "Войти";
    }
    nav.appendChild(a);
    // На главной прячем дублирующую ссылку входа, если уже вошли.
    const authLink = document.getElementById("authLink");
    if (authLink && token) authLink.parentElement.classList.add("hidden");
  });
})();
