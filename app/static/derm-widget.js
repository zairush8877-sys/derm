/**
 * derm — встраиваемый виджет анализа кожи для сайтов брендов.
 *
 * Подключение на сайте бренда:
 *   <div id="derm-widget"></div>
 *   <script src="https://<ваш-derm-хост>/static/derm-widget.js"
 *           data-api-base="https://<ваш-derm-хост>"
 *           data-api-key="<API-ключ бренда>"
 *           data-target="#derm-widget"></script>
 *
 * Виджет обращается к B2B API (POST /v1/analyze) с заголовком X-API-Key.
 * dermatologist-validated · косметический анализ, не медицинский диагноз.
 */
(function () {
  "use strict";

  var script = document.currentScript;
  var API_BASE = (script && script.getAttribute("data-api-base")) || "";
  var API_KEY = (script && script.getAttribute("data-api-key")) || "";
  var TARGET = (script && script.getAttribute("data-target")) || "#derm-widget";
  var ACCENT = (script && script.getAttribute("data-accent")) || "#2563eb";

  var CONCERN_ORDER = null;

  function css() {
    return (
      ".dw-card{font-family:-apple-system,Segoe UI,Roboto,sans-serif;max-width:420px;border:1px solid #e6e8f0;" +
      "border-radius:14px;padding:18px;background:#fff;color:#1f2430}" +
      ".dw-drop{border:2px dashed #cbd2e6;border-radius:12px;padding:26px;text-align:center;color:#6e6e78;cursor:pointer}" +
      ".dw-btn{background:" + ACCENT + ";color:#fff;border:none;border-radius:10px;padding:11px 16px;" +
      "font-size:15px;font-weight:600;cursor:pointer;width:100%;margin-top:12px}" +
      ".dw-btn:disabled{opacity:.5}" +
      ".dw-row{display:flex;justify-content:space-between;font-size:14px;margin:8px 0 4px}" +
      ".dw-bar{height:8px;border-radius:99px;background:#eceff5;overflow:hidden}" +
      ".dw-bar>span{display:block;height:100%;border-radius:99px}" +
      ".dw-note{font-size:11px;color:#8a8a94;margin-top:12px}" +
      ".dw-type{display:inline-block;background:#eef3ff;color:" + ACCENT + ";padding:4px 10px;border-radius:99px;" +
      "font-weight:600;font-size:13px;margin-bottom:8px}"
    );
  }

  function color(score) {
    if (score <= 33) return "#16a34a";
    if (score <= 66) return "#d97706";
    return "#dc2626";
  }

  function el(tag, cls, html) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (html != null) e.innerHTML = html;
    return e;
  }

  function render(root) {
    var style = document.createElement("style");
    style.textContent = css();
    document.head.appendChild(style);

    var card = el("div", "dw-card");
    card.appendChild(el("div", null, "<strong>Анализ кожи</strong> — узнайте состояние кожи по фото"));
    var drop = el("div", "dw-drop", "Нажмите, чтобы выбрать фото лица");
    var input = document.createElement("input");
    input.type = "file"; input.accept = "image/*"; input.style.display = "none";
    var btn = el("button", "dw-btn", "Анализировать"); btn.disabled = true;
    var out = el("div");
    var note = el("div", "dw-note",
      "Косметический анализ кожи, не медицинский диагноз. Powered by derm.");

    var file = null;
    drop.onclick = function () { input.click(); };
    input.onchange = function (e) {
      file = e.target.files[0];
      if (file) { drop.textContent = "Выбрано: " + file.name; btn.disabled = false; }
    };
    btn.onclick = function () { analyze(file, btn, out); };

    card.appendChild(drop);
    card.appendChild(input);
    card.appendChild(btn);
    card.appendChild(out);
    card.appendChild(note);
    root.appendChild(card);
  }

  function analyze(file, btn, out) {
    if (!file) return;
    btn.disabled = true; btn.textContent = "Анализируем…"; out.innerHTML = "";
    var fd = new FormData();
    fd.append("image", file);
    fetch(API_BASE + "/v1/analyze", { method: "POST", headers: { "X-API-Key": API_KEY }, body: fd })
      .then(function (r) {
        if (r.status === 401) throw new Error("Неверный API-ключ бренда");
        if (r.status === 429) throw new Error("Превышен лимит тарифа");
        if (!r.ok) throw new Error("Ошибка анализа: " + r.status);
        return r.json();
      })
      .then(function (a) { showResult(a, out); })
      .catch(function (e) { out.innerHTML = '<p style="color:#dc2626">' + e.message + "</p>"; })
      .finally(function () { btn.disabled = false; btn.textContent = "Анализировать"; });
  }

  function showResult(a, out) {
    out.innerHTML = "";
    out.appendChild(el("div", "dw-type", "Тип кожи: " + a.skin_type));
    out.appendChild(el("p", null, a.summary));
    var concerns = a.concerns.slice().sort(function (x, y) { return y.score - x.score; });
    concerns.forEach(function (c) {
      out.appendChild(el("div", "dw-row",
        "<span>" + c.name + "</span><span style='color:" + color(c.score) + "'>" + c.score + "/100</span>"));
      var bar = el("div", "dw-bar");
      bar.appendChild(el("span", null, "")).setAttribute(
        "style", "width:" + c.score + "%;background:" + color(c.score));
      out.appendChild(bar);
    });
  }

  function boot() {
    var root = document.querySelector(TARGET);
    if (!root) { console.error("[derm-widget] target не найден:", TARGET); return; }
    if (!API_KEY) console.warn("[derm-widget] не задан data-api-key");
    render(root);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", boot);
  else boot();
})();
