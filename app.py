import streamlit as st
from streamlit import rerun
from agent import ShoppingAgent
from utils import load_products, fetch_product_by_id
import os
import json

st.set_page_config(layout="wide", page_title="AI Personal Shopper — Hyper-Personalized")

# ---------------------------------------------------------
# Premium Shopping Theme CSS + 3D Sparkle Headline
# ---------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Poppins', sans-serif;
    color: #f4f6fb;
}

/* App background */
body {
    background: linear-gradient(135deg, #0f172a, #111827, #020617);
    background-attachment: fixed;
}

/* Main content container */
section.main > div {
    background: rgba(255, 255, 255, 0.02);
    padding: 2rem;
    border-radius: 18px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617, #020617);
    border-right: 1px solid rgba(255,255,255,0.08);
}

/* ---------------------------------------------------
   🔥 3D SPARKLING HEADLINE
--------------------------------------------------- */

.hero-wrapper {
    perspective: 1200px;
    text-align: center;
    margin-bottom: 2.5rem;
    position: relative;
}

.hero-title {
    font-size: 44px;
    font-weight: 800;
    letter-spacing: 0.5px;
    background: linear-gradient(
        120deg,
        #fde68a,
        #fb7185,
        #38bdf8,
        #a78bfa
    );
    background-size: 300% 300%;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;

    transform-style: preserve-3d;
    animation:
        float3d 6s ease-in-out infinite,
        gradientShift 8s ease infinite;
    position: relative;
}

/* Glow layer */
.hero-title::after {
    content: attr(data-text);
    position: absolute;
    inset: 0;
    background: linear-gradient(90deg, #facc15, #fb7185, #38bdf8);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    filter: blur(18px);
    opacity: 0.65;
    z-index: -1;
}

/* Sparkles */
.sparkle {
    position: absolute;
    width: 6px;
    height: 6px;
    background: radial-gradient(circle, #fff, transparent 70%);
    border-radius: 50%;
    animation: sparkle 3s linear infinite;
    opacity: 0.8;
}

.sparkle:nth-child(1) { top: -10px; left: 20%; animation-delay: 0s; }
.sparkle:nth-child(2) { top: 10px; left: 80%; animation-delay: 0.5s; }
.sparkle:nth-child(3) { top: 60%; left: -10px; animation-delay: 1s; }
.sparkle:nth-child(4) { top: 70%; left: 95%; animation-delay: 1.5s; }
.sparkle:nth-child(5) { top: 100%; left: 40%; animation-delay: 2s; }

/* Animations */
@keyframes float3d {
    0% {
        transform: rotateX(0deg) rotateY(0deg) translateZ(0);
    }
    50% {
        transform: rotateX(6deg) rotateY(-6deg) translateZ(18px);
    }
    100% {
        transform: rotateX(0deg) rotateY(0deg) translateZ(0);
    }
}

@keyframes gradientShift {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes sparkle {
    0% {
        transform: scale(0.3);
        opacity: 0;
    }
    50% {
        opacity: 1;
    }
    100% {
        transform: scale(1.6);
        opacity: 0;
    }
}

/* Buttons */
.stButton > button {
    background: linear-gradient(135deg, #facc15, #fb7185);
    color: #020617;
    font-weight: 600;
    border-radius: 10px;
    padding: 0.55rem 1rem;
    border: none;
    transition: all 0.25s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: 0 8px 22px rgba(250,204,21,0.35);
}

/* Cards */
.float-card {
    background: rgba(255,255,255,0.04);
    border-radius: 18px;
    padding: 1rem;
    margin-bottom: 1.5rem;
    transition: all 0.3s ease;
    border: 1px solid rgba(255,255,255,0.08);
}

.float-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 14px 32px rgba(0,0,0,0.6);
}
</style>

<div class="hero-wrapper">
    <div class="hero-title" data-text="🛍️ AI Hyper-Personalized Shopping Assistant">
        🛍️ AI Hyper-Personalized Shopping Assistant
    </div>

</div>
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
# Main Layout
# -----------------------
col1, col2 = st.columns([2, 3])

with col1:
    st.header("💬 Chat with Your Shopper")
    for role, text in st.session_state.history:
        st.markdown(f"**{'You' if role=='user' else 'Assistant'}:** {text}")

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
        st.session_state.history.append(("assistant", "✨ Your curated lookbook is ready — scroll right!"))
        rerun()

with col2:
    st.header("👗 Curated Lookbook")
    lookbook = st.session_state.get("last_lookbook", {})

    if lookbook:
        items_raw = lookbook.get("lookbook", [])
        items = []
        for it in items_raw:
            pid = it.get("product_id") or it.get("id")
            product = fetch_product_by_id(pid)
            if product:
                price = float(product.get("price", 0))
                if budget_min <= price <= budget_max:
                    items.append((it, product))

        cols = st.columns(2)
        for i, (it, product) in enumerate(items):
            with cols[i % 2]:
                st.markdown('<div class="float-card">', unsafe_allow_html=True)
                st.image(get_image_path(product), width=260)
                st.markdown(f"**{product['title']}**")
                st.write(f"${product['price']} • {product.get('category','N/A')}")
                st.write(it.get("reason", ""))
                if st.button("Add to cart", key=f"add_{product['id']}"):
                    st.session_state.cart.append(product)
                    st.success("Added to cart!")
                st.markdown('</div>', unsafe_allow_html=True)
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
