// Админ-панель: сводка (read-only).
"use strict";

const el = (id) => document.getElementById(id);

function kpi(title, value) {
  return `<div class="pcard"><span class="cat">${title}</span>
    <div class="price">${value}</div></div>`;
}

async function load() {
  const res = await fetch("/api/admin/overview", { headers: { "X-Admin-Token": el("token").value } });
  if (res.status === 401) { alert("Неверный админ-токен"); return; }
  const d = await res.json();
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
    el("recent").innerHTML = d.recent_orders.map((o) => `
      <div class="trend">
        <span class="name">${o.id} · ${o.user_id}</span>
        <span class="score">${Number(o.total_rub).toLocaleString("ru-RU")} ₽</span>
        <span class="pill new">${o.status}</span>
      </div>`).join("");
  } else {
    el("recent").innerHTML = `<p class="summary">Заказов пока нет.</p>`;
  }
  el("recentCard").classList.remove("hidden");
}

el("load").addEventListener("click", load);
load();
