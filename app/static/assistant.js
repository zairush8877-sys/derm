// Wellness-ассистент: чат с историей.
"use strict";

const el = (id) => document.getElementById(id);
const history = [];

const SUGGESTIONS = ["Как улучшить сон?", "Что от акне?", "Какие витамины сдать?", "Набор мышечной массы"];

function addMsg(role, text) {
  const div = document.createElement("div");
  div.className = "msg " + (role === "user" ? "user" : "bot");
  div.textContent = text;
  el("chat").appendChild(div);
  el("chat").scrollTop = el("chat").scrollHeight;
}

async function send(text) {
  const message = text || el("msg").value.trim();
  if (!message) return;
  el("msg").value = "";
  addMsg("user", message);
  history.push({ role: "user", content: message });
  const typing = document.createElement("div");
  typing.className = "msg bot"; typing.textContent = "…";
  el("chat").appendChild(typing);
  try {
    const res = await fetch("/api/assistant/chat", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, history }),
    });
    const data = await res.json();
    typing.remove();
    addMsg("bot", data.reply);
    history.push({ role: "assistant", content: data.reply });
  } catch (e) {
    typing.textContent = "Ошибка: " + e.message;
  }
}

function renderChips() {
  el("chips").innerHTML = SUGGESTIONS.map((s) =>
    `<button class="ghost" data-s="${s}">${s}</button>`).join("");
  el("chips").querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => send(b.dataset.s)));
}

el("send").addEventListener("click", () => send());
el("msg").addEventListener("keydown", (e) => { if (e.key === "Enter") send(); });
renderChips();
addMsg("bot", "Здравствуйте! Я wellness-ассистент Aura. Чем помочь — кожа, питание, сон, энергия?");
