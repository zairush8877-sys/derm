// Личный кабинет: профиль, сканы, баллы, заказы, подписка, уведомления.
"use strict";

const el = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
  ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

// Без входа кабинет не показываем.
if (!localStorage.getItem("aura_token")) window.location = "/auth";

async function j(url, opts) {
  const res = await fetch(url, opts);
  if (res.status === 401) { window.location = "/auth"; throw new Error("401"); }
  return res;
}

async function loadProfile() {
  const res = await j("/api/auth/me");
  const u = await res.json();
  el("who").textContent = (u.name ? u.name + " · " : "") + u.phone;
}

async function loadStats() {
  const [bal, loy] = await Promise.all([
    j("/api/billing/balance").then((r) => r.json()),
    j("/api/shop/loyalty").then((r) => r.json()),
  ]);
  el("stBalance").textContent = bal.balance;
  el("stPoints").textContent = loy.points;
  el("stTier").textContent = loy.tier;
  // Пакеты сканов, если баланс на нуле.
  if (bal.balance === 0) {
    el("packs").innerHTML = Object.entries(bal.packs).map(([pack, count]) =>
      `<button class="ghost" data-pack="${esc(pack)}">Купить ${count} скан(ов)</button>`).join("");
    el("packs").classList.remove("hidden");
    el("packs").querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => buyPack(b.dataset.pack)));
  }
}

async function buyPack(pack) {
  const fd = new FormData();
  fd.append("pack", pack);
  const res = await j("/api/billing/checkout", { method: "POST", body: fd });
  const data = await res.json();
  window.location = data.confirmation_url;
}

async function loadScans() {
  const scans = await j("/api/scans").then((r) => r.json());
  if (!scans.length) { el("scans").innerHTML = `<p class="summary">Сканов пока нет — сделайте первый бесплатно.</p>`; return; }
  el("scans").innerHTML = scans.slice(-5).reverse().map((s) => {
    const top = [...s.analysis.concerns].sort((a, b) => b.score - a.score)[0];
    return `<div class="trend">
      <span class="name">${new Date(s.created_at).toLocaleDateString("ru-RU")} · кожа: ${esc(s.analysis.skin_type)}</span>
      <span class="pill flat">${esc(top.name)} ${top.score}/100</span>
    </div>`;
  }).join("");
}

async function loadOrders() {
  const orders = await j("/api/shop/orders").then((r) => r.json());
  if (!orders.length) { el("orders").innerHTML = `<p class="summary">Заказов пока нет.</p>`; return; }
  el("orders").innerHTML = orders.slice(0, 5).map((o) => `
    <div class="trend">
      <span class="name">${new Date(o.created_at).toLocaleDateString("ru-RU")} · ${esc(o.order_id)}</span>
      <span class="score">${o.total_rub.toLocaleString("ru-RU")} ₽</span>
      <span class="pill new">${esc(o.status)}</span>
    </div>`).join("");
}

async function loadSub() {
  const res = await fetch("/api/subscription/current");
  if (res.status === 404) {
    el("sub").innerHTML = `<p class="summary">Подписки нет. Персональный уход, который обновляется
      каждые 30 дней под сезон.</p><a class="sec-link" href="/subscription">Оформить →</a>`;
    return;
  }
  const d = await res.json();
  el("sub").innerHTML = `
    <div class="trend"><span class="name">Сезон</span><span class="pill up">${esc(d.protocol.season || "—")}</span></div>
    <div class="trend"><span class="name">Следующее обновление</span>
      <span class="score">${new Date(d.next_update).toLocaleDateString("ru-RU")}</span></div>
    <a class="sec-link" href="/subscription">Открыть протокол →</a>`;
}

async function loadNotifs() {
  const d = await j("/api/notifications").then((r) => r.json());
  if (!d.items.length) { el("notifs").innerHTML = `<p class="summary">Уведомлений нет.</p>`; return; }
  el("notifs").innerHTML = d.items.slice(0, 8).map((n) => `
    <div class="notif ${n.read ? "" : "unread"}">
      <div class="t">${esc(n.title)}</div>
      <div class="b">${esc(n.body)}</div>
    </div>`).join("");
}

el("markRead").addEventListener("click", async () => {
  await j("/api/notifications/read", { method: "POST", body: new FormData() });
  loadNotifs();
});
el("logout").addEventListener("click", () => {
  localStorage.removeItem("aura_token");
  localStorage.removeItem("aura_name");
  window.location = "/";
});

loadProfile();
loadStats();
loadScans();
loadOrders();
loadSub();
loadNotifs();

// ===== Мой профиль (ФИО, пол, дата рождения, город) =====
async function loadMyProfile() {
  const res = await j("/api/auth/profile");
  const p = await res.json();
  el("prLast").value = p.last_name || "";
  el("prFirst").value = p.first_name || "";
  el("prMiddle").value = p.middle_name || "";
  el("prCity").value = p.city || "";
  el("prGender").value = p.gender || "";
  el("prBirth").value = p.birth_date || "";
  renderProfileState(p);
  if (location.hash === "#profile") {
    document.getElementById("profile").scrollIntoView({ behavior: "smooth" });
  }
}

function renderProfileState(p) {
  if (p.complete) {
    el("profMissing").textContent = "заполнен";
    el("profBonus").textContent = "";
  } else {
    el("profMissing").textContent = "осталось: " + p.missing_required.join(", ");
    el("profBonus").textContent =
      "Заполните профиль полностью — начислим " + p.bonus_points + " баллов (1 балл = 1 ₽).";
  }
}

async function saveMyProfile() {
  const fd = new FormData();
  fd.append("last_name", el("prLast").value);
  fd.append("first_name", el("prFirst").value);
  fd.append("middle_name", el("prMiddle").value);
  fd.append("gender", el("prGender").value);
  fd.append("birth_date", el("prBirth").value);
  fd.append("city", el("prCity").value);
  const res = await j("/api/auth/profile", { method: "POST", body: fd });
  const p = await res.json();
  if (!res.ok) { alert(p.detail || "Не получилось сохранить"); return; }
  renderProfileState(p);
  if (p.bonus_granted_now) {
    alert("Спасибо! Профиль заполнен — начислили " + p.bonus_points + " баллов 🎉");
    loadStats();
  } else {
    el("profBonus").textContent = "Сохранено ✓";
  }
  localStorage.setItem("aura_name", el("prFirst").value || localStorage.getItem("aura_name"));
}

el("profSave").addEventListener("click", saveMyProfile);
loadMyProfile();
