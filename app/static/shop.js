// Магазин Aura: каталог, поиск, категории, корзина, оформление, лояльность, заказы.
"use strict";

const el = (id) => document.getElementById(id);
const USER = "demo-user";
let activeCat = null;
let query = "";

const catIcon = {
  "уходовая косметика": "🧴", "декоративная косметика": "💄", "гаджеты": "📱",
  "спортпит": "💪", "витамины и БАДы": "💊", "пептиды": "🧬", "biohacking": "🔬",
  "функциональные напитки": "🍵", "healthy food": "🥗", "лабораторная диагностика": "🧪",
  "wellness check-up": "🩺",
};

async function loadProducts() {
  var url = "/api/shop/products?";
  if (activeCat) url += "category=" + encodeURIComponent(activeCat) + "&";
  if (query) url += "q=" + encodeURIComponent(query);
  const res = await fetch(url);
  const data = await res.json();
  renderCats(data.categories);
  renderGrid(data.products);
}

function renderCats(categories) {
  const box = el("cats");
  const all = [{ v: null, label: "Все" }].concat(
    categories.map((c) => ({ v: c, label: (catIcon[c] || "") + " " + c })));
  box.innerHTML = all.map((c) =>
    `<button class="ghost" data-cat="${c.v ?? ""}"
      style="${c.v === activeCat ? "background:var(--brand);color:#fff" : ""}">${c.label}</button>`
  ).join("");
  box.querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => { activeCat = b.dataset.cat || null; loadProducts(); }));
}

function renderGrid(products) {
  if (!products.length) { el("grid").innerHTML = `<p class="summary">Ничего не найдено.</p>`; return; }
  el("grid").innerHTML = products.map((p) => `
    <div class="pcard">
      <span class="cat">${catIcon[p.category] || ""} ${p.category}${p.is_service ? " · услуга" : ""}</span>
      <h3 style="margin:6px 0">${p.name}</h3>
      <p class="summary" style="flex:1;margin:0 0 8px;font-size:13px">${p.brand} · ${p.description}</p>
      <div class="price">${p.price_rub.toLocaleString("ru-RU")} ₽</div>
      <button class="ghost" data-add="${p.id}">${p.is_service ? "Записаться" : "В корзину"}</button>
    </div>`).join("");
  el("grid").querySelectorAll("button[data-add]").forEach((b) =>
    b.addEventListener("click", () => addToCart(b.dataset.add)));
}

async function addToCart(productId) {
  const fd = new FormData();
  fd.append("user_id", USER); fd.append("product_id", productId); fd.append("qty", "1");
  const res = await fetch("/api/shop/cart/add", { method: "POST", body: fd });
  renderCart(await res.json());
}

async function removeFromCart(productId) {
  const fd = new FormData();
  fd.append("user_id", USER); fd.append("product_id", productId);
  const res = await fetch("/api/shop/cart/remove", { method: "POST", body: fd });
  renderCart(await res.json());
}

async function loadCart() {
  const res = await fetch("/api/shop/cart?user_id=" + USER);
  renderCart(await res.json());
}

function renderCart(cart) {
  if (!cart.items.length) { el("cart").innerHTML = `<p class="summary">Корзина пуста.</p>`; return; }
  el("cart").innerHTML =
    cart.items.map((it) => `
      <div class="trend">
        <span class="name">${it.product.name} × ${it.qty}</span>
        <span class="score">${it.line_rub.toLocaleString("ru-RU")} ₽</span>
        <button class="pill down" data-rm="${it.product.id}" style="border:none;cursor:pointer">убрать</button>
      </div>`).join("") +
    `<p style="text-align:right;font-weight:700;font-size:18px;margin-top:10px">
       Итого: ${cart.total_rub.toLocaleString("ru-RU")} ₽</p>
     <p class="summary" style="text-align:right;font-size:12px">Бесплатная доставка от 5 000 ₽</p>
     <button class="primary" id="openCheckout" style="width:100%">Оформить заказ</button>`;
  el("cart").querySelectorAll("button[data-rm]").forEach((b) =>
    b.addEventListener("click", () => removeFromCart(b.dataset.rm)));
  el("openCheckout").addEventListener("click", () => el("checkoutModal").classList.remove("hidden"));
}

async function submitCheckout() {
  const addr = el("co-address").value.trim();
  if (!addr) { alert("Укажите адрес доставки"); return; }
  const fd = new FormData();
  fd.append("user_id", USER); fd.append("address", addr);
  fd.append("name", el("co-name").value); fd.append("phone", el("co-phone").value);
  const res = await fetch("/api/shop/checkout", { method: "POST", body: fd });
  if (!res.ok) { alert("Не удалось оформить заказ"); return; }
  const o = await res.json();
  el("checkoutModal").classList.add("hidden");
  alert(`Заказ ${o.order_id} оформлен на ${o.total_rub.toLocaleString("ru-RU")} ₽.\nНачислено баллов: ${o.points_earned}`);
  loadCart(); loadOrders(); loadLoyalty();
}

async function loadLoyalty() {
  const res = await fetch("/api/shop/loyalty?user_id=" + USER);
  const l = await res.json();
  el("loyalty").textContent = `${l.tier} · ${l.points} баллов · кешбэк ${Math.round(l.cashback_rate * 100)}%`;
}

async function loadOrders() {
  const res = await fetch("/api/shop/orders?user_id=" + USER);
  const list = await res.json();
  if (!list.length) { el("orders").innerHTML = `<p class="summary">Заказов пока нет.</p>`; return; }
  el("orders").innerHTML = list.map((o) => `
    <div class="trend">
      <span class="name">Заказ ${o.order_id} · ${new Date(o.created_at).toLocaleDateString("ru-RU")}</span>
      <span class="score">${o.total_rub.toLocaleString("ru-RU")} ₽</span>
      <span class="pill new">${o.status}</span>
    </div>`).join("");
}

let searchTimer = null;
el("q").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  query = e.target.value;
  searchTimer = setTimeout(loadProducts, 250);
});
el("co-submit").addEventListener("click", submitCheckout);
el("co-cancel").addEventListener("click", () => el("checkoutModal").classList.add("hidden"));

loadProducts();
loadCart();
loadLoyalty();
loadOrders();
