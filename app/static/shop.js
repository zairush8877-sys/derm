// Магазин: каталог, категории, корзина.
"use strict";

const el = (id) => document.getElementById(id);
const USER = "demo-user";
let activeCat = null;

const catIcon = { "гаджеты": "📱", "спортпит": "💪", "уходовая косметика": "🧴" };

async function loadProducts() {
  const url = "/api/shop/products" + (activeCat ? "?category=" + encodeURIComponent(activeCat) : "");
  const res = await fetch(url);
  const data = await res.json();
  renderCats(data.categories);
  renderGrid(data.products);
}

function renderCats(categories) {
  const box = el("cats");
  const all = [{ v: null, label: "Все" }].concat(categories.map((c) => ({ v: c, label: catIcon[c] + " " + c })));
  box.innerHTML = all.map((c) =>
    `<button class="ghost ${c.v === activeCat ? "" : ""}" data-cat="${c.v ?? ""}"
      style="${c.v === activeCat ? "background:var(--brand);color:#fff" : ""}">${c.label}</button>`
  ).join("");
  box.querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => { activeCat = b.dataset.cat || null; loadProducts(); }));
}

function renderGrid(products) {
  el("grid").innerHTML = products.map((p) => `
    <div class="card">
      <div style="display:flex;justify-content:space-between;gap:12px;align-items:flex-start">
        <div>
          <span class="cat">${catIcon[p.category] || ""} ${p.category}</span>
          <h2 style="margin:4px 0">${p.name}</h2>
          <p class="summary" style="margin:0 0 6px">${p.brand} · ${p.description}</p>
        </div>
        <div style="text-align:right;white-space:nowrap">
          <div class="score" style="font-size:18px">${p.price_rub.toLocaleString("ru-RU")} ₽</div>
          <button class="ghost" data-add="${p.id}">В корзину</button>
        </div>
      </div>
    </div>`).join("");
  el("grid").querySelectorAll("button[data-add]").forEach((b) =>
    b.addEventListener("click", () => addToCart(b.dataset.add)));
}

async function addToCart(productId) {
  const fd = new FormData();
  fd.append("user_id", USER);
  fd.append("product_id", productId);
  fd.append("qty", "1");
  const res = await fetch("/api/shop/cart/add", { method: "POST", body: fd });
  renderCart(await res.json());
}

async function removeFromCart(productId) {
  const fd = new FormData();
  fd.append("user_id", USER);
  fd.append("product_id", productId);
  const res = await fetch("/api/shop/cart/remove", { method: "POST", body: fd });
  renderCart(await res.json());
}

async function loadCart() {
  const res = await fetch("/api/shop/cart?user_id=" + USER);
  renderCart(await res.json());
}

function renderCart(cart) {
  if (!cart.items.length) {
    el("cart").innerHTML = `<p class="summary">Корзина пуста.</p>`;
    return;
  }
  el("cart").innerHTML =
    cart.items.map((it) => `
      <div class="trend">
        <span class="name">${it.product.name} × ${it.qty}</span>
        <span class="score">${it.line_rub.toLocaleString("ru-RU")} ₽</span>
        <button class="pill down" data-rm="${it.product.id}" style="border:none;cursor:pointer">убрать</button>
      </div>`).join("") +
    `<p style="text-align:right;font-weight:700;font-size:18px;margin-top:10px">
       Итого: ${cart.total_rub.toLocaleString("ru-RU")} ₽</p>
     <button class="primary" style="width:100%">Оформить заказ</button>`;
  el("cart").querySelectorAll("button[data-rm]").forEach((b) =>
    b.addEventListener("click", () => removeFromCart(b.dataset.rm)));
}

loadProducts();
loadCart();
