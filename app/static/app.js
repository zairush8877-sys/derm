// Фронтенд демо-страницы анализа кожи.
"use strict";

let selectedFile = null;

const el = (id) => document.getElementById(id);

function severityClass(score) {
  if (score <= 33) return "var(--green)";
  if (score <= 66) return "var(--orange)";
  return "var(--red)";
}

function collectForm() {
  const fd = new FormData();
  fd.append("image", selectedFile);
  fd.append("user_id", el("user_id").value || "demo-user");
  if (el("age").value) fd.append("age", el("age").value);
  fd.append("sensitivity", el("sensitivity").checked);
  fd.append("pregnant", el("pregnant").checked);
  fd.append("sun_exposure", el("sun_exposure").value);
  fd.append("budget", el("budget").value);
  return fd;
}

function renderSteps(listEl, steps) {
  listEl.innerHTML = "";
  steps.forEach((s) => {
    const li = document.createElement("li");
    li.innerHTML = `<div><strong>${s.step}</strong> · <span class="cat">${s.category}</span></div>
                    <div class="why">${s.why}</div>`;
    listEl.appendChild(li);
  });
}

function renderResult(data) {
  const a = data.analysis;
  const p = data.protocol;

  el("skinType").textContent = "Тип кожи: " + a.skin_type;
  el("summary").textContent = a.summary;
  el("disclaimer").textContent = a.disclaimer;
  // Честность: если реальный AI недоступен и сработал демо-режим — предупреждаем.
  if ((a.model || "").includes("mock")) {
    el("summary").insertAdjacentHTML("beforebegin",
      `<p class="pill down" style="display:inline-block;margin-bottom:8px">⚠️ Демо-оценка:
       реальный AI сейчас недоступен, результат ориентировочный</p>`);
  }

  const concerns = el("concerns");
  concerns.innerHTML = "";
  a.concerns.slice().sort((x, y) => y.score - x.score).forEach((c) => {
    const div = document.createElement("div");
    div.className = "concern";
    div.innerHTML = `
      <div class="row"><span>${c.name}</span>
        <span class="score" style="color:${severityClass(c.score)}">${c.score}/100 · ${c.severity}</span></div>
      <div class="bar"><span style="width:${c.score}%;background:${severityClass(c.score)}"></span></div>`;
    concerns.appendChild(div);
  });

  renderSteps(el("am"), p.am_steps);
  renderSteps(el("pm"), p.pm_steps);

  const extra = el("extra");
  extra.innerHTML = "";
  if (p.weekly && p.weekly.length) {
    extra.innerHTML += `<h3>Раз в неделю</h3><ul class="steps">` +
      p.weekly.map((w) => `<li>${w}</li>`).join("") + `</ul>`;
  }
  if (p.lifestyle && p.lifestyle.length) {
    extra.innerHTML += `<h3>Образ жизни</h3><ul class="steps">` +
      p.lifestyle.map((w) => `<li>${w}</li>`).join("") + `</ul>`;
  }
  const next = new Date(p.next_review).toLocaleDateString("ru-RU");
  extra.innerHTML += `<p style="color:var(--brand);font-weight:600">Следующее обновление протокола: ${next}</p>`;

  renderRecommended(data.recommended);
  el("result").classList.remove("hidden");
}

async function analyze() {
  if (!selectedFile) return;
  el("result").classList.add("hidden");
  el("paywall").classList.add("hidden");
  el("loading").classList.remove("hidden");
  el("go").disabled = true;
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: collectForm() });
    if (res.status === 402) {
      const err = await res.json();
      el("paywallMsg").textContent = err.error || "Недостаточно кредитов для скана.";
      el("paywall").classList.remove("hidden");
      return;
    }
    if (!res.ok) throw new Error("Ошибка анализа: " + res.status);
    const data = await res.json();
    renderResult(data);
    if (typeof data.balance === "number") showBalance(data.balance);
  } catch (e) {
    alert(e.message);
  } finally {
    el("loading").classList.add("hidden");
    el("go").disabled = false;
  }
}

function showBalance(n) {
  el("balance").textContent = "Доступно сканов: " + n;
}

function renderRecommended(products) {
  const box = el("recommended");
  if (!products || !products.length) { box.innerHTML = ""; return; }
  box.innerHTML = "<h3>Рекомендуем из магазина</h3>" +
    products.map((p) =>
      `<div class="trend"><span class="name">${p.name} · <span style="color:var(--muted)">${p.brand}</span></span>
       <span class="score">${p.price_rub.toLocaleString("ru-RU")} ₽</span>
       <a class="pill new" href="/shop" style="text-decoration:none">в магазин</a></div>`
    ).join("");
}

async function loadBalance() {
  const user = el("user_id").value || "demo-user";
  try {
    const res = await fetch("/api/billing/balance?user_id=" + encodeURIComponent(user));
    const data = await res.json();
    showBalance(data.balance);
    const packs = el("packs");
    packs.innerHTML = Object.entries(data.packs).map(([pack, count]) =>
      `<button class="ghost" data-pack="${pack}">Купить ${count} скан(ов)</button>`
    ).join("");
    packs.querySelectorAll("button").forEach((b) =>
      b.addEventListener("click", () => buyPack(b.dataset.pack)));
  } catch { /* ignore */ }
}

async function buyPack(pack) {
  const fd = new FormData();
  fd.append("user_id", el("user_id").value || "demo-user");
  fd.append("pack", pack);
  const res = await fetch("/api/billing/checkout", { method: "POST", body: fd });
  const data = await res.json();
  // Демо-провайдер: переходим на страницу подтверждения (начислит кредиты и вернёт назад).
  window.location = data.confirmation_url;
}

async function downloadPdf() {
  if (!selectedFile) return;
  const fd = collectForm();
  fd.delete("user_id");
  const res = await fetch("/api/report", { method: "POST", body: fd });
  if (!res.ok) { alert("Не удалось сформировать PDF"); return; }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = "derm-report.pdf"; a.click();
  URL.revokeObjectURL(url);
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

async function loadMode() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    el("mode").textContent = "Режим: " + data.mode;
  } catch { el("mode").textContent = ""; }
}

initDropzone();
loadMode();
loadBalance();
el("go").addEventListener("click", analyze);
el("downloadPdf").addEventListener("click", downloadPdf);
