// Админ-панель: сводка, статусы заказов, автоматизации.
"use strict";

const el = (id) => document.getElementById(id);
let statusFlow = [];

// Экранирование пользовательских строк перед вставкой в innerHTML.
const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function headers() {
  return { "X-Admin-Token": el("token").value };
}

function kpi(title, value) {
  return `<div class="pcard"><span class="cat">${title}</span>
    <div class="price">${value}</div></div>`;
}

async function load() {
  if (!el("token").value) return;  // не дёргаем API без токена
  let res;
  try {
    res = await fetch("/api/admin/overview", { headers: headers() });
  } catch {
    alert("Сеть недоступна"); return;
  }
  if (res.status === 401) { alert("Неверный админ-токен"); return; }
  if (!res.ok) { alert("Ошибка сервера: " + res.status); return; }
  const d = await res.json();
  statusFlow = d.status_flow || [];
  el("kpis").innerHTML = [
    kpi("Заказов", d.orders.count),
    kpi("Выручка, ₽", d.orders.revenue_rub.toLocaleString("ru-RU")),
    kpi("Активных подписок", d.subscriptions_active),
    kpi("B2B-клиентов", d.b2b.clients),
    kpi("B2B вызовов API", d.b2b.api_calls),
    kpi("Сканов кожи", d.ai.skin_scans),
    kpi("Сканов еды", d.ai.food_scans),
  ].join("");

  if (d.recent_orders.length) {
    el("recent").innerHTML = d.recent_orders.map((o) => {
      const idx = statusFlow.indexOf(o.status);
      const next = idx >= 0 && idx < statusFlow.length - 1 ? statusFlow[idx + 1] : null;
      const btn = next
        ? `<button class="ghost" style="margin:0" data-oid="${esc(o.id)}" data-next="${next}">→ ${next}</button>`
        : "";
      const trackBtn = (o.status === "собирается" || o.status === "отправлен")
        ? `<button class="ghost" style="margin:0" data-track="${esc(o.id)}" title="Вписать трек-номер СДЭК">📦 трек</button>`
        : "";
      return `
      <div class="trend">
        <span class="name">${esc(o.id)} · ${esc(o.user_id)}</span>
        <span class="score">${Number(o.total_rub).toLocaleString("ru-RU")} ₽</span>
        <span class="pill new">${esc(o.status)}</span>
        ${btn}${trackBtn}
      </div>`;
    }).join("");
    el("recent").querySelectorAll("[data-oid]").forEach((b) =>
      b.addEventListener("click", () => advance(b.dataset.oid, b.dataset.next)));
    el("recent").querySelectorAll("[data-track]").forEach((b) =>
      b.addEventListener("click", () => setTrack(b.dataset.track)));
  } else {
    el("recent").innerHTML = `<p class="summary">Заказов пока нет.</p>`;
  }
  el("recentCard").classList.remove("hidden");
  loadAutomation();
}

let advancing = false;
async function advance(orderId, status) {
  if (advancing) return;  // защита от двойного клика
  advancing = true;
  const fd = new FormData();
  fd.append("order_id", orderId);
  fd.append("status", status);
  try {
    const res = await fetch("/api/admin/order-status", { method: "POST", body: fd, headers: headers() });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      alert(err.detail || "Не удалось сменить статус"); return;
    }
    load();
  } finally {
    advancing = false;
  }
}

async function setTrack(orderId) {
  const track = prompt("Трек-номер СДЭК для заказа " + orderId + ":");
  if (!track || !track.trim()) return;
  const fd = new FormData();
  fd.append("order_id", orderId);
  fd.append("track", track.trim());
  const res = await fetch("/api/admin/order-track", { method: "POST", body: fd, headers: headers() });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || "Не удалось сохранить трек"); return;
  }
  alert("Трек сохранён — покупатель получил ссылку отслеживания.");
}

async function loadAutomation() {
  const res = await fetch("/api/admin/automation", { headers: headers() });
  if (!res.ok) return;
  const data = await res.json();
  el("autoRuns").innerHTML = data.runs.length
    ? data.runs.map((r) => `
      <div class="trend">
        <span class="name">${esc(r.job)}</span>
        <span class="score">${esc(r.detail)}</span>
        <span class="pill flat">${new Date(r.created_at).toLocaleString("ru-RU")}</span>
      </div>`).join("")
    : `<p class="summary">Запусков ещё не было. Планировщик выполняет задачи раз в час автоматически.</p>`;
}

async function runJobs() {
  el("runJobs").disabled = true;
  try {
    const res = await fetch("/api/admin/run-jobs", { method: "POST", headers: headers() });
    if (res.status === 401) { alert("Неверный админ-токен"); return; }
    if (!res.ok) { alert("Ошибка запуска: " + res.status); return; }
    const results = await res.json();
    alert("Выполнено:\n" + Object.entries(results).map(([k, v]) => `${k}: ${v}`).join("\n"));
    loadAutomation();
  } catch {
    alert("Сеть недоступна");
  } finally {
    el("runJobs").disabled = false;  // всегда разблокируем (в т.ч. при ошибке сети)
  }
}

async function aiTest() {
  el("aiTest").disabled = true;
  el("aiTest").textContent = "Проверяем…";
  try {
    const res = await fetch("/api/admin/ai-test", { method: "POST", headers: headers() });
    if (res.status === 401) { alert("Неверный админ-токен"); return; }
    const r = await res.json();
    alert((r.ok ? "✅ Реальный AI работает!" : "❌ AI не подключён") +
      "\nКлюч: " + (r.key_present ? "задан" : "НЕ задан") +
      "\nЧат: " + (r.chat || "—") +
      "\nVision: " + (r.vision || "—") +
      (r.hint ? "\n\n" + r.hint : ""));
  } catch { alert("Сеть недоступна"); }
  finally { el("aiTest").disabled = false; el("aiTest").textContent = "🤖 Проверить AI"; }
}

el("aiTest").addEventListener("click", aiTest);
el("load").addEventListener("click", load);
el("runJobs").addEventListener("click", runJobs);
// Автозагрузка только если токен уже введён (например, сохранён браузером).
if (el("token").value) load();
