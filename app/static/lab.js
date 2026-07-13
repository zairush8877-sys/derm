// Лаборатория: панели анализов + заявка на запись.
"use strict";

const el = (id) => document.getElementById(id);
const fmt = (n) => new Intl.NumberFormat("ru-RU").format(n) + " ₽";

function authHeaders() {
  const token = localStorage.getItem("aura_token");
  return token ? { Authorization: "Bearer " + token } : {};
}

let PANELS = [];
let SELECTED = null;

const STATUS_RU = {
  new: "новая — ждёт звонка менеджера",
  confirmed: "подтверждена",
  done: "выполнена",
  canceled: "отменена",
};

async function loadPanels() {
  const res = await fetch("/api/lab/panels");
  const data = await res.json();
  PANELS = data.panels;
  el("disclaimer").textContent = data.disclaimer;
  el("panels").innerHTML = PANELS.map((p) => `
    <div class="card lab-card${p.popular ? " lab-popular" : ""}">
      ${p.popular ? '<span class="badge">популярно</span>' : ""}
      <h3>${p.name}</h3>
      <p class="muted">${p.tagline}</p>
      <ul class="steps lab-marks">${p.biomarkers.map((b) => `<li>${b}</li>`).join("")}</ul>
      <p class="lab-meta">готовность ~${p.days} дн. · ${p.fasting ? "натощак" : "без подготовки"}</p>
      <div class="lab-price">
        ${p.old_price_rub ? `<s>${fmt(p.old_price_rub)}</s> ` : ""}<strong>${fmt(p.price_rub)}</strong>
      </div>
      <button class="primary" data-panel="${p.id}">Записаться</button>
    </div>`).join("");
  document.querySelectorAll("#panels button[data-panel]").forEach((b) =>
    b.addEventListener("click", () => openForm(b.dataset.panel)));
}

function openForm(panelId) {
  SELECTED = PANELS.find((p) => p.id === panelId);
  if (!SELECTED) return;
  el("bf-panel").textContent = SELECTED.name;
  el("bf-price").textContent = fmt(SELECTED.price_rub);
  el("bookform").classList.remove("hidden");
  el("bookform").scrollIntoView({ behavior: "smooth", block: "center" });
}

async function submitBooking() {
  if (!SELECTED) return;
  const fd = new FormData();
  fd.append("panel_id", SELECTED.id);
  fd.append("city", el("bf-city").value);
  fd.append("phone", el("bf-phone").value);
  fd.append("preferred_date", el("bf-date").value);
  fd.append("comment", el("bf-comment").value);
  const res = await fetch("/api/lab/book", { method: "POST", body: fd, headers: authHeaders() });
  const data = await res.json();
  if (!res.ok) { alert(data.error || "Не получилось отправить заявку"); return; }
  el("bookform").classList.add("hidden");
  alert("Заявка принята! Менеджер позвонит, чтобы подтвердить запись.");
  loadBookings();
}

async function cancelBooking(id) {
  if (!confirm("Отменить заявку?")) return;
  const fd = new FormData();
  fd.append("booking_id", id);
  const res = await fetch("/api/lab/cancel", { method: "POST", body: fd, headers: authHeaders() });
  if (res.ok) loadBookings();
}

async function loadBookings() {
  const res = await fetch("/api/lab/bookings", { headers: authHeaders() });
  const data = await res.json();
  const list = data.bookings || [];
  if (!list.length) { el("mybookings").classList.add("hidden"); return; }
  el("mybookings").classList.remove("hidden");
  el("bookings-list").innerHTML = list.map((b) => `
    <div class="lab-booking">
      <div><strong>${b.panel_name}</strong> · ${b.city}
        ${b.preferred_date ? " · " + b.preferred_date : ""}</div>
      <div class="muted">статус: ${STATUS_RU[b.status] || b.status}
        · заявка от ${new Date(b.created_at).toLocaleDateString("ru-RU")}</div>
      ${b.status === "new" || b.status === "confirmed"
        ? `<button class="ghost" data-cancel="${b.id}">Отменить</button>` : ""}
    </div>`).join("");
  document.querySelectorAll("#bookings-list button[data-cancel]").forEach((btn) =>
    btn.addEventListener("click", () => cancelBooking(btn.dataset.cancel)));
}

el("bf-submit").addEventListener("click", submitBooking);
el("bf-close").addEventListener("click", () => el("bookform").classList.add("hidden"));

loadPanels();
loadBookings();
