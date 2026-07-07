// Магазин Aura: каталог, поиск, категории, корзина, оформление, лояльность, заказы.
"use strict";

const el = (id) => document.getElementById(id);
const USER = "demo-user";
let activeCat = null;
let query = new URLSearchParams(location.search).get("q") || "";

const catIcon = {
  "уходовая косметика": "🧴", "декоративная косметика": "💄", "гаджеты": "📱",
  "спортпит": "💪", "витамины и БАДы": "💊", "пептиды": "🧬", "biohacking": "🔬",
  "функциональные напитки": "🍵", "healthy food": "🥗", "лабораторная диагностика": "🧪",
  "wellness check-up": "🩺",
};

function sortProducts(products) {
  const mode = el("sort") ? el("sort").value : "popular";
  const arr = [...products];
  if (mode === "cheap") arr.sort((a, b) => a.price_rub - b.price_rub);
  else if (mode === "expensive") arr.sort((a, b) => b.price_rub - a.price_rub);
  else if (mode === "discount") {
    const d = (p) => (p.old_price_rub ? 1 - p.price_rub / p.old_price_rub : 0);
    arr.sort((a, b) => d(b) - d(a));
  } else {
    // «Популярные»: сначала хиты и скидки, затем по рейтингу.
    const w = (p) => (p.hit ? 2 : 0) + (p.old_price_rub ? 1 : 0) + ratingFor(p).rating;
    arr.sort((a, b) => w(b) - w(a));
  }
  return arr;
}

function renderSkeletons(n = 8) {
  el("grid").innerHTML = Array.from({ length: n }, () => `
    <div class="skel">
      <div class="ph tile"></div>
      <div class="ph line short"></div>
      <div class="ph line"></div>
      <div class="ph line short"></div>
    </div>`).join("");
}

async function loadProducts() {
  renderSkeletons();
  var url = "/api/shop/products?";
  if (activeCat) url += "category=" + encodeURIComponent(activeCat) + "&";
  if (query) url += "q=" + encodeURIComponent(query);
  const res = await fetch(url);
  const data = await res.json();
  renderCats(data.categories);
  renderGrid(sortProducts(data.products));
}

function renderCats(categories) {
  const box = el("cats");
  const all = [{ v: null, label: "Все" }].concat(
    categories.map((c) => ({ v: c, label: (catIcon[c] || "") + " " + c })));
  box.innerHTML = all.map((c) =>
    `<button class="ghost" data-cat="${c.v ?? ""}"
      style="${c.v === activeCat ? "background:var(--ink);color:var(--on-ink)" : ""}">${c.label}</button>`
  ).join("");
  box.querySelectorAll("button").forEach((b) =>
    b.addEventListener("click", () => { activeCat = b.dataset.cat || null; loadProducts(); }));
}

function ratingFor(p) {
  // Детерминированный демо-рейтинг по id (пока нет реальных отзывов).
  let h = 0;
  for (const ch of p.id) h = (h * 31 + ch.charCodeAt(0)) % 997;
  const rating = 4.5 + (h % 5) / 10;           // 4.5–4.9
  const reviews = 3 + (h % 40);                 // 3–42
  return { rating, reviews };
}

function renderGrid(products) {
  if (!products.length) { el("grid").innerHTML = `<p class="summary">Ничего не найдено.</p>`; return; }
  el("grid").innerHTML = products.map((p) => {
    const { rating, reviews } = ratingFor(p);
    const stars = "★".repeat(Math.round(rating)) + "☆".repeat(5 - Math.round(rating));
    const freeShip = p.price_rub >= 3500 ? `<span class="badge-free">Бесплатная доставка</span>` : "";
    const disc = p.old_price_rub && p.old_price_rub > p.price_rub
      ? Math.round((1 - p.price_rub / p.old_price_rub) * 100) : 0;
    const cornerBadge = disc ? `<span class="badge-disc">−${disc}%</span>`
      : (p.hit ? `<span class="badge-hit">Хит</span>` : "");
    const oldPrice = disc
      ? `<span class="old-price">${p.old_price_rub.toLocaleString("ru-RU")} ₽</span>` : "";
    return `
    <div class="pcard">
      <div class="ptile">${cornerBadge}${freeShip}${catIcon[p.category] || "🌿"}
        <button class="addbtn" data-add="${p.id}" title="${p.is_service ? "Записаться" : "В корзину"}">+</button>
      </div>
      <span class="cat">${p.brand}</span>
      <h3>${p.name}</h3>
      <div class="price">${p.price_rub.toLocaleString("ru-RU")} ₽${oldPrice}</div>
      <div class="stars">${stars}<span class="cnt">(${reviews})</span></div>
    </div>`;
  }).join("");
  el("grid").querySelectorAll("[data-add]").forEach((b) =>
    b.addEventListener("click", async () => {
      await addToCart(b.dataset.add);
      // Микро-анимация успеха: «+» превращается в «✓» на секунду.
      b.textContent = "✓"; b.classList.add("added");
      setTimeout(() => { b.textContent = "+"; b.classList.remove("added"); }, 900);
    }));
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
     <p class="summary" style="text-align:right;font-size:12px">Бесплатная доставка от 3 500 ₽ (ПВЗ)</p>
     <button class="primary" id="openCheckout" style="width:100%">Оформить заказ</button>`;
  el("cart").querySelectorAll("button[data-rm]").forEach((b) =>
    b.addEventListener("click", () => removeFromCart(b.dataset.rm)));
  el("openCheckout").addEventListener("click", openCheckoutModal);
}

async function openCheckoutModal() {
  el("checkoutModal").classList.remove("hidden");
  const res = await fetch("/api/shop/delivery?user_id=" + USER);
  const data = await res.json();
  el("co-method").innerHTML = data.options.map((o) =>
    `<option value="${o.method}">${o.title} — ${o.fee_rub ? o.fee_rub + " ₽" : "бесплатно"} · ~${o.eta_days} дн.</option>`
  ).join("");
}

async function submitCheckout() {
  const addr = el("co-address").value.trim();
  if (!addr) { alert("Укажите адрес доставки"); return; }
  const fd = new FormData();
  fd.append("user_id", USER); fd.append("address", addr);
  fd.append("name", el("co-name").value); fd.append("phone", el("co-phone").value);
  fd.append("delivery_method", el("co-method").value);
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
el("q").value = query;
el("q").addEventListener("input", (e) => {
  clearTimeout(searchTimer);
  query = e.target.value;
  searchTimer = setTimeout(loadProducts, 250);
});
el("sort").addEventListener("change", loadProducts);
el("co-submit").addEventListener("click", submitCheckout);
el("co-cancel").addEventListener("click", () => el("checkoutModal").classList.add("hidden"));

loadProducts();
loadCart();
loadLoyalty();
loadOrders();
