import streamlit as st
from streamlit import rerun
from agent import ShoppingAgent
from utils import load_products, fetch_product_by_id
import os
import json

st.set_page_config(layout="wide", page_title="AI Personal Shopper — Hyper-Personalized")

# ---------------------------------------------------------
# Fancy Animated Background + UI
# ---------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@600;800&display=swap');

body {
    background: linear-gradient(135deg, #0a0f24, #081229, #0b0f2e, #0a1f3e);
    background-size: 400% 400%;
    animation: bgMove 15s ease infinite;
}

@keyframes bgMove {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

h1 {
    text-align: center;
    font-family: 'Poppins', sans-serif;
    font-size: 45px;
    font-weight: 800;
    background: linear-gradient(90deg, #ff00c8, #00eaff, #ff9d00, #00ff6a);
    background-size: 400%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: textGlow 5s infinite linear;
}

@keyframes textGlow {
    0% {background-position: 0%;}
    50% {background-position: 100%;}
    100% {background-position: 0%;}
}

.float-card {
    transition: 0.3s;
    transform: perspective(800px) rotateX(5deg) rotateY(-5deg);
}
.float-card:hover {
    transform: perspective(800px) rotateX(0deg) rotateY(0deg) scale(1.05);
    box-shadow: 0px 12px 35px rgba(255, 0, 200, 0.35);
}

img {
    border-radius: 15px !important;
    transition: transform .5s ease, box-shadow .3s ease;
}
img:hover {
    transform: scale(1.08) rotateX(7deg);
    box-shadow: 0px 10px 25px rgba(0, 255, 255, 0.4);
}
</style>

<h1>⚡ AI Hyper-Personalized Shopping Assistant ⚡</h1>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# Initialization
# ---------------------------------------------------------
if "agent" not in st.session_state:
    emb_method = "openai" if os.getenv("OPENAI_API_KEY") else "local"
    st.session_state.agent = ShoppingAgent(
        index_path_openai="product_index_openai.faiss",
        index_path_local="product_index_local.faiss",
        meta_db="products_meta.db",
        emb_method=emb_method
    )

st.session_state.setdefault("history", [])
st.session_state.setdefault("cart", [])
st.session_state.setdefault("orders", [])
st.session_state.setdefault("last_lookbook", {})

products_df = load_products("sample_data/products.csv")

# ---------------------------------------------------------
# Sidebar — Preferences + Cart
# ---------------------------------------------------------
with st.sidebar:
    st.title("🎯 Preferences")

    # Detect changes in preferences
    def preference_changed():
        st.session_state.refresh_lookbook = True

    occasion = st.selectbox("Occasion", ["wedding", "party", "office", "casual", "travel"],
                            index=0, key="pref_occasion", on_change=preference_changed)
    temp = st.selectbox("Weather", ["warm", "mild", "chilly", "cold"],
                        index=2, key="pref_weather", on_change=preference_changed)
    size = st.selectbox("Size", ["XS", "S", "M", "L", "XL"],
                        index=2, key="pref_size", on_change=preference_changed)
    budget_min, budget_max = st.slider("Budget range (USD)", 20, 1000, (50, 300),
                                      key="pref_budget", on_change=preference_changed)

    st.markdown("---")
    st.subheader("🛒 Cart")
    if st.session_state.cart:
        for i, item in enumerate(st.session_state.cart):
            st.markdown(f"**{item['title']}** — ${item['price']}")
            if st.button(f"Remove {i}", key=f"remove_{i}"):
                st.session_state.cart.pop(i)
                rerun()
        st.markdown(f"**Total:** ${sum([c['price'] for c in st.session_state.cart]):.2f}")
        if st.button("Checkout"):
            st.session_state.show_checkout = True
    else:
        st.write("Cart is empty")

    st.markdown("---")
    st.subheader("📦 Order History")
    for o in st.session_state.orders[::-1]:
        st.write(f"Order #{o['order_id']} — ${o['total']:.2f}")

# ---------------------------------------------------------
# Generate Lookbook automatically if preferences changed
# ---------------------------------------------------------
if st.session_state.get("refresh_lookbook", False) and st.session_state.get("history"):
    last_user_query = st.session_state.history[-1][1] if st.session_state.history else "Outfit recommendation"
    query = (
        f"{last_user_query}. Occasion: {occasion}. Weather: {temp}. "
        f"Budget between {budget_min}-{budget_max}. Size: {size}."
    )
    agent = st.session_state.agent
    retrieved, sims = agent.retrieve(query, k=12)

    # Apply budget filter
    filtered = []
    for item in retrieved:
        p = fetch_product_by_id(item["id"])
        if p and budget_min <= float(p.get("price", 0)) <= budget_max:
            filtered.append(item)

    parsed = agent.generate_lookbook(
        user_request=query,
        retrieved_products=filtered,
        chat_history=[m for _, m in st.session_state.history]
    )

    st.session_state.last_lookbook = parsed
    st.session_state.refresh_lookbook = False
    rerun()

# ---------------------------------------------------------
# Fixed Image Loader
# ---------------------------------------------------------
def get_image_path(product):
    path = (product.get("image_url") or product.get("image_path") or "").strip()
    if not path:
        return "https://via.placeholder.com/260x300?text=No+Image"
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return os.path.join(os.getcwd(), path)

# -----------------------
# Main Layout: Left - Chat
# -----------------------
col1, col2 = st.columns([2, 3])
with col1:
    st.header("💬 Chat with Your Shopper")
    for role, text in st.session_state.history:
        if role == "user":
            st.markdown(f"**You:** {text}")
        else:
            st.markdown(f"**Assistant:** {text}")

    user_input = st.text_input(
        "Tell me what you need (e.g. 'Outfit for chilly outdoor wedding')",
        key="input"
    )

    if st.button("Send"):
        st.session_state.history.append(("user", user_input))
        query = (
            f"{user_input}. Occasion: {occasion}. Weather: {temp}. "
            f"Budget between {budget_min}-{budget_max}. Size: {size}."
        )
        agent = st.session_state.agent
        retrieved, sims = agent.retrieve(query, k=12)

        # Apply budget filter
        filtered = []
        for item in retrieved:
            p = fetch_product_by_id(item["id"])
            if p and budget_min <= float(p.get("price", 0)) <= budget_max:
                filtered.append(item)

        parsed = agent.generate_lookbook(
            user_request=query,
            retrieved_products=filtered,
            chat_history=[m for _, m in st.session_state.history]
        )

        st.session_state.last_lookbook = parsed
        st.session_state.history.append(("assistant", "✨ Your curated 3D lookbook is ready — scroll right!"))
        rerun()

# -----------------------
# Main Layout: Right - Lookbook
# -----------------------
with col2:
    st.header("👗 Curated Lookbook")
    lookbook = st.session_state.get("last_lookbook", {})

    if lookbook:
        items_raw = lookbook.get("lookbook", [])
        items = []
        for it in items_raw:
            pid = it.get("product_id") or it.get("id")
            product = fetch_product_by_id(pid)
            if not product:
                continue
            price = float(product.get("price", 0))
            if budget_min <= price <= budget_max:
                items.append(it)

        if not items:
            st.write("No items found inside your selected budget range.")
        else:
            lookbook_products = []
            for it in items:
                pid = it.get("product_id") or it.get("id")
                product = fetch_product_by_id(pid)
                if product:
                    product["image_path"] = get_image_path(product)
                    lookbook_products.append((it, product))

            cols = st.columns(2)
            for i, (it, product) in enumerate(lookbook_products):
                col = cols[i % 2]
                with col:
                    st.markdown('<div class="float-card">', unsafe_allow_html=True)
                    st.image(product.get("image_path"), width=260)
                    st.markdown(f"**{product.get('title', 'No Title')}**")
                    st.write(f"${product.get('price', '0.00')} • {product.get('category', 'N/A')}")
                    st.write(it.get("reason", ""))
                    st.markdown("</div>", unsafe_allow_html=True)
                    if st.button("Add to cart", key=f"add_{product.get('id', i)}"):
                        st.session_state.cart.append(product)
                        st.success("Added to cart!")
                    st.markdown('</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.subheader("✨ Styling Notes")
        st.write(lookbook.get("styling_notes", ""))
        st.subheader("🧩 Complementary Items")
        for c in lookbook.get("complementary_items", []):
            st.write(f"- {c.get('title')} — {c.get('reason', '')}")
        st.markdown("---")
        st.subheader("🧾 Checkout Instructions")
        st.write(lookbook.get("checkout_instructions", ""))
    else:
        st.write("Ask for an outfit on the left!")

# -----------------------
# Checkout
# -----------------------
if st.session_state.get("show_checkout"):
    st.sidebar.markdown("## 🧾 Checkout")
    name = st.sidebar.text_input("Name")
    email = st.sidebar.text_input("Email")
    addr = st.sidebar.text_area("Shipping Address")
    if st.sidebar.button("Place Order"):
        order_id = len(st.session_state.orders) + 1
        total = sum([c["price"] for c in st.session_state.cart])
        st.session_state.orders.append({
            "order_id": order_id,
            "items": st.session_state.cart.copy(),
            "total": total,
            "name": name,
            "email": email,
            "address": addr
        })
        st.session_state.cart = []
        st.session_state.show_checkout = False
        st.sidebar.success(f"Order #{order_id} placed!")

# -----------------------
# Returns Section
# -----------------------
st.sidebar.markdown("### Returns Section")
if "return_messages" not in st.session_state:
    st.session_state.return_messages = []

if st.sidebar.button("Initiate Return"):
    st.session_state.show_return_items = True

if st.session_state.get("show_return_items"):
    has_orders = False
    for order_idx, order in enumerate(st.session_state.orders):
        if order["items"]:
            has_orders = True
            st.sidebar.markdown(f"**Order #{order_idx + 1} (Total: ${order['total']:.2f})**")
            for item_idx, item in enumerate(order["items"]):
                if st.sidebar.button(
                    f"Return {item['title']} — ${item['price']}",
                    key=f"return_{order_idx}_{item_idx}"
                ):
                    refund_amount = item["price"]
                    order["items"].pop(item_idx)
                    order["total"] -= refund_amount
                    if len(order["items"]) == 0:
                        st.session_state.orders.pop(order_idx)
                    st.session_state.return_messages.append(
                        f"Return initiated for {item['title']} (${refund_amount:.2f})"
                    )
                    rerun()
    if not has_orders:
        st.sidebar.write("No orders/items to return.")
        st.session_state.show_return_items = False

if st.session_state.return_messages:
    st.sidebar.markdown("### Return Status")
    for msg in st.session_state.return_messages:
        st.sidebar.success(msg)

# -----------------------
# Post-purchase Recommendations
# -----------------------
if st.sidebar.button("Recommend for last order"):
    if st.session_state.orders:
        last = st.session_state.orders[-1]
        recs = st.session_state.agent.post_purchase_recommendations(
            last["items"], top_n=4
        )
        st.sidebar.write("Recommended:")
        for r in recs:
            st.sidebar.write(f"- {r['title']} — ${r['price']}")
    else:
        st.sidebar.write("No orders yet.")
