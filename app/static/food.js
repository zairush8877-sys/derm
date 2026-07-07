// AI-трекер еды: фото -> калории/БЖУ, дневник за день.
"use strict";

const el = (id) => document.getElementById(id);
const USER = "demo-user";
let selectedFile = null;

function macroRow(label, value, unit) {
  return `<span class="pill flat" style="margin-right:6px">${label}: ${value} ${unit}</span>`;
}

function renderResult(a) {
  el("summary").textContent = a.summary;
  el("disclaimer").textContent = a.disclaimer;
  // Честность: если реальный AI недоступен и сработал демо-режим — говорим об этом.
  const demoNote = (a.model || "").includes("mock")
    ? `<p class="pill down" style="display:inline-block;margin-bottom:10px">⚠️ Демо-оценка:
       реальный AI сейчас недоступен, цифры ориентировочные</p>` : "";
  const micros = (a.micros && a.micros.length)
    ? `<h3 style="margin:14px 0 8px">Витамины и минералы ≈</h3>` +
      a.micros.map((m) => `
        <div class="concern" style="margin:8px 0">
          <div class="row"><span>${m.name}${m.amount ? " · " + m.amount : ""}</span>
            <span class="score">${m.daily_pct}%</span></div>
          <div class="bar"><span style="width:${Math.min(100, m.daily_pct)}%;
            background:var(--accent)"></span></div>
        </div>`).join("") +
      `<p class="summary" style="font-size:12px">% от примерной дневной нормы взрослого</p>`
    : "";
  el("items").innerHTML = demoNote + a.items.map((it) => `
    <div class="trend">
      <span class="name">${it.name} · <span style="color:var(--muted)">${it.grams} г</span></span>
      <span class="score">${it.calories} ккал</span>
    </div>
    <div style="margin:2px 0 8px">
      ${macroRow("Б", it.protein, "г")}${macroRow("Ж", it.fat, "г")}${macroRow("У", it.carbs, "г")}
    </div>`).join("") +
    `<p style="text-align:right;font-weight:700">Всего: ${a.total_calories} ккал</p>` +
    micros;
  el("result").classList.remove("hidden");
}

async function analyze() {
  if (!selectedFile) return;
  el("result").classList.add("hidden");
  el("paywall").classList.add("hidden");
  el("loading").classList.remove("hidden");
  el("go").disabled = true;
  try {
    const fd = new FormData();
    fd.append("image", selectedFile);
    fd.append("user_id", USER);
    const res = await fetch("/api/food/analyze", { method: "POST", body: fd });
    if (res.status === 402) {
      const err = await res.json();
      el("paywallMsg").textContent = err.error || "Недостаточно кредитов.";
      el("paywall").classList.remove("hidden");
      return;
    }
    if (!res.ok) throw new Error("Ошибка: " + res.status);
    const data = await res.json();
    renderResult(data.analysis);
    showBalance(data.balance);
    loadDay();
  } catch (e) {
    alert(e.message);
  } finally {
    el("loading").classList.add("hidden");
    el("go").disabled = false;
  }
}

function showBalance(n) {
  if (typeof n === "number") el("balance").textContent = "Доступно сканов: " + n;
}

async function loadDay() {
  const res = await fetch("/api/food/day?user_id=" + USER);
  const d = await res.json();
  if (!d.entries) { el("day").innerHTML = `<p class="summary">Сегодня записей нет.</p>`; return; }
  el("day").innerHTML = `
    <div class="trend"><span class="name">Приёмов пищи</span><span class="score">${d.entries}</span></div>
    <div class="trend"><span class="name">Калории</span><span class="score">${d.total_calories} ккал</span></div>
    <div style="margin-top:8px">
      ${macroRow("Белки", d.total_protein, "г")}${macroRow("Жиры", d.total_fat, "г")}${macroRow("Углеводы", d.total_carbs, "г")}
    </div>`;
}

async function loadBalance() {
  try {
    const res = await fetch("/api/billing/balance?user_id=" + USER);
    const data = await res.json();
    showBalance(data.balance);
    el("packs").innerHTML = Object.entries(data.packs).map(([pack, count]) =>
      `<button class="ghost" data-pack="${pack}">Купить ${count} скан(ов)</button>`).join("");
    el("packs").querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => buyPack(b.dataset.pack)));
  } catch { /* ignore */ }
}

async function buyPack(pack) {
  const fd = new FormData();
  fd.append("user_id", USER);
  fd.append("pack", pack);
  const res = await fetch("/api/billing/checkout", { method: "POST", body: fd });
  const data = await res.json();
  window.location = data.confirmation_url;
}

function setFile(file) {
  if (!file || !file.type.startsWith("image/")) return;
  selectedFile = file;
  const img = el("preview");
  img.src = URL.createObjectURL(file);
  img.classList.remove("hidden");
  el("go").disabled = false;
}

function initDropzone() {
  const drop = el("drop");
  const input = el("file");
  drop.addEventListener("click", () => input.click());
  input.addEventListener("change", (e) => setFile(e.target.files[0]));
  ["dragover", "dragenter"].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.add("drag"); }));
  ["dragleave", "drop"].forEach((ev) =>
    drop.addEventListener(ev, (e) => { e.preventDefault(); drop.classList.remove("drag"); }));
  drop.addEventListener("drop", (e) => setFile(e.dataTransfer.files[0]));
}

initDropzone();
loadBalance();
loadDay();
el("go").addEventListener("click", analyze);
