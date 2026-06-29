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

  el("result").classList.remove("hidden");
}

async function analyze() {
  if (!selectedFile) return;
  el("result").classList.add("hidden");
  el("loading").classList.remove("hidden");
  el("go").disabled = true;
  try {
    const res = await fetch("/api/analyze", { method: "POST", body: collectForm() });
    if (!res.ok) throw new Error("Ошибка анализа: " + res.status);
    const data = await res.json();
    renderResult(data);
  } catch (e) {
    alert(e.message);
  } finally {
    el("loading").classList.add("hidden");
    el("go").disabled = false;
  }
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
el("go").addEventListener("click", analyze);
el("downloadPdf").addEventListener("click", downloadPdf);
