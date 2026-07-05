// Дашборд AI-трекера: динамика кожи во времени.
"use strict";

const el = (id) => document.getElementById(id);

function pillFor(direction) {
  switch (direction) {
    case "улучшение": return { cls: "up", text: "▼ улучшение" };
    case "ухудшение": return { cls: "down", text: "▲ ухудшение" };
    case "новая": return { cls: "new", text: "новая" };
    default: return { cls: "flat", text: "без изменений" };
  }
}

function renderTrends(summary) {
  el("overall").textContent = summary.overall;
  el("count").textContent = "Всего сканов: " + summary.scans_count;
  el("summary").classList.remove("hidden");

  if (!summary.trends.length) {
    el("empty").classList.remove("hidden");
    el("trends").classList.add("hidden");
    return;
  }
  el("empty").classList.add("hidden");

  const list = el("trendList");
  list.innerHTML = "";
  summary.trends.slice().sort((a, b) => b.current - a.current).forEach((t) => {
    const p = pillFor(t.direction);
    const delta = t.delta === null || t.delta === undefined ? "" :
      ` (${t.delta > 0 ? "+" : ""}${t.delta})`;
    const div = document.createElement("div");
    div.className = "trend";
    div.innerHTML = `<span class="name">${t.name}</span>
      <span class="score">${t.current}/100${delta}</span>
      <span class="pill ${p.cls}">${p.text}</span>`;
    list.appendChild(div);
  });
  el("trends").classList.remove("hidden");
}

function drawChart(scans) {
  if (scans.length < 1) return;
  const canvas = el("canvas");
  const ctx = canvas.getContext("2d");
  ctx.clearRect(0, 0, canvas.width, canvas.height);

  const pad = 36;
  const W = canvas.width - pad * 2;
  const H = canvas.height - pad * 2;

  // Средний балл проблем по каждому скану.
  const points = scans.map((s) => {
    const arr = s.analysis.concerns;
    const avg = arr.reduce((acc, c) => acc + c.score, 0) / arr.length;
    return avg;
  });

  // Оси
  ctx.strokeStyle = "#d7dbe6";
  ctx.beginPath();
  ctx.moveTo(pad, pad); ctx.lineTo(pad, pad + H); ctx.lineTo(pad + W, pad + H);
  ctx.stroke();
  ctx.fillStyle = "#6e6e78";
  ctx.font = "11px sans-serif";
  ctx.fillText("100", 8, pad + 4);
  ctx.fillText("0", 20, pad + H);
  ctx.fillText("сканы →", pad + W - 50, pad + H + 22);

  // Линия среднего балла
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 2;
  ctx.beginPath();
  const n = Math.max(points.length - 1, 1);
  points.forEach((v, i) => {
    const x = pad + (W * i) / n;
    const y = pad + H - (H * v) / 100;
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.stroke();

  ctx.fillStyle = "#2563eb";
  points.forEach((v, i) => {
    const x = pad + (W * i) / n;
    const y = pad + H - (H * v) / 100;
    ctx.beginPath(); ctx.arc(x, y, 3.5, 0, Math.PI * 2); ctx.fill();
  });

  el("chart").classList.remove("hidden");
}

async function load() {
  const user = el("user_id").value || "demo-user";
  try {
    const [trendsRes, scansRes] = await Promise.all([
      fetch("/api/trends?user_id=" + encodeURIComponent(user)),
      fetch("/api/scans?user_id=" + encodeURIComponent(user)),
    ]);
    const summary = await trendsRes.json();
    const scans = await scansRes.json();
    renderTrends(summary);
    if (scans.length) drawChart(scans);
    else { el("chart").classList.add("hidden"); el("empty").classList.remove("hidden"); }
  } catch (e) {
    alert("Не удалось загрузить динамику: " + e.message);
  }
}

el("load").addEventListener("click", load);
load();
