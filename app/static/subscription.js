// DTC-подписка на «живой» протокол.
"use strict";

const el = (id) => document.getElementById(id);
const USER = "demo-user";

function renderSteps(id, steps) {
  el(id).innerHTML = steps.map((s) =>
    `<li><div><strong>${s.step}</strong> · <span class="cat">${s.category}</span></div>
     <div class="why">${s.why}</div></li>`).join("");
}

function renderProtocol(data) {
  const p = data.protocol;
  el("season").textContent = "сезон: " + (p.season || "—");
  el("meta").textContent = "Обновлён: " + new Date(data.updated_at).toLocaleDateString("ru-RU") +
    " · Следующее обновление: " + new Date(data.next_update).toLocaleDateString("ru-RU") +
    (data.refreshed_now ? " · только что обновлён" : "");
  renderSteps("am", p.am_steps);
  renderSteps("pm", p.pm_steps);
  const extra = el("extra");
  extra.innerHTML = "";
  if (p.weekly && p.weekly.length)
    extra.innerHTML += "<h3>Раз в неделю</h3><ul class='steps'>" + p.weekly.map((w) => `<li>${w}</li>`).join("") + "</ul>";
  if (p.lifestyle && p.lifestyle.length)
    extra.innerHTML += "<h3>Образ жизни</h3><ul class='steps'>" + p.lifestyle.map((w) => `<li>${w}</li>`).join("") + "</ul>";
  el("current").classList.remove("hidden");
}

function form() {
  const fd = new FormData();
  fd.append("user_id", USER);
  if (el("age").value) fd.append("age", el("age").value);
  fd.append("skin_type", el("skin_type").value);
  fd.append("hormonal_phase", el("hormonal_phase").value);
  fd.append("sun_exposure", el("sun_exposure").value);
  fd.append("sensitivity", el("sensitivity").checked);
  fd.append("pregnant", el("pregnant").checked);
  return fd;
}

async function subscribe() {
  const res = await fetch("/api/subscription/subscribe", { method: "POST", body: form() });
  const data = await res.json();
  // Приводим к формату current.
  loadCurrent();
}

async function loadCurrent(force) {
  const res = await fetch("/api/subscription/current?user_id=" + USER + (force ? "&force=true" : ""));
  if (res.status === 404) { el("current").classList.add("hidden"); return; }
  renderProtocol(await res.json());
}

async function cancel() {
  const fd = new FormData(); fd.append("user_id", USER);
  await fetch("/api/subscription/cancel", { method: "POST", body: fd });
  el("current").classList.add("hidden");
}

el("subscribe").addEventListener("click", subscribe);
el("refresh").addEventListener("click", () => loadCurrent(true));
el("cancel").addEventListener("click", cancel);
loadCurrent();
