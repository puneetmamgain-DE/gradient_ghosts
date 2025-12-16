
import streamlit as st
from streamlit import rerun
from agent import ShoppingAgent
from utils import load_products, fetch_product_by_id, SizeConverter, RewardSystem, PolicyManager
import os
from datetime import datetime

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Vestra — Intelligent Shopping")

# ---------------------------------------------------------
# Module 1: Advanced 3D Styling & High Contrast UI
# ---------------------------------------------------------
st.markdown("""
<style>
/* Import Fonts */
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&family=Rajdhani:wght@500;700&display=swap');

/* --- ANIMATIONS --- */

/* 1. Global Background Gradient Flow */
@keyframes gradient-animation {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

/* 2. Chat Button Float */
@keyframes float {
    0% { transform: translateY(0px) scale(1); box-shadow: 0 5px 15px rgba(124, 58, 237, 0.4); }
    50% { transform: translateY(-6px) scale(1.02); box-shadow: 0 25px 40px rgba(124, 58, 237, 0.6); }
    100% { transform: translateY(0px) scale(1); box-shadow: 0 5px 15px rgba(124, 58, 237, 0.4); }
}

/* 3. VESTRA LOGO 3D MOTION */
@keyframes logo-3d-move {
    0% {
        transform: perspective(1000px) rotateX(10deg) rotateY(-5deg) translateY(0);
        text-shadow: 0 5px 0 #4c1d95, 0 10px 20px rgba(0,0,0,0.5);
    }
    50% {
        transform: perspective(1000px) rotateX(0deg) rotateY(5deg) translateY(-10px);
        text-shadow: 0 15px 0 #4c1d95, 0 20px 40px rgba(0,0,0,0.7);
    }
    100% {
        transform: perspective(1000px) rotateX(10deg) rotateY(-5deg) translateY(0);
        text-shadow: 0 5px 0 #4c1d95, 0 10px 20px rgba(0,0,0,0.5);
    }
}

@keyframes shine-flow {
    0% { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
}

/* --- GLOBAL BACKGROUND --- */
.stApp {
    background: linear-gradient(-45deg, #020617, #0f172a, #1e1b4b, #312e81);
    background-size: 400% 400%;
    animation: gradient-animation 15s ease infinite;
    color: #e2e8f0;
}

/* --- LOGO STYLING --- */
.vestra-3d-logo {
    font-family: 'Orbitron', sans-serif;
    font-size: 72px;
    font-weight: 900;
    text-align: center;
    /* Gradient Texture */
    background: linear-gradient(90deg, #ffffff, #818cf8, #ffffff);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    /* Animations */
    animation: logo-3d-move 6s ease-in-out infinite alternate, shine-flow 4s linear infinite;
    margin-bottom: 0.2rem;
    letter-spacing: 4px;
    display: inline-block;
}

/* ------------------------------------------------------- */
/* SIDEBAR VISIBILITY FIXES                                */
/* ------------------------------------------------------- */

[data-testid="stSidebar"] {
    background-color: rgba(10, 10, 25, 0.95);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #e0e7ff !important;
    font-family: 'Rajdhani', sans-serif;
    letter-spacing: 1px;
    text-shadow: 0 0 5px rgba(129, 140, 248, 0.5);
}

/* Dropdown Boxes */
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: #1e293b !important;
    color: white !important;
    border: 1px solid rgba(129, 140, 248, 0.5) !important;
    border-radius: 8px !important;
}

/* Text INSIDE Dropdown */
[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #ffffff !important;
    font-weight: 500;
}

/* Dropdown Menu List */
ul[data-baseweb="menu"] {
    background-color: #0f172a !important;
    border: 1px solid #6366f1 !important;
}
li[data-baseweb="option"] { color: #f8fafc !important; }
li[data-baseweb="option"][aria-selected="true"] { background-color: #4338ca !important; }

/* Sidebar Buttons */
[data-testid="stSidebar"] button {
    background: linear-gradient(90deg, #4f46e5, #7c3aed);
    color: white !important;
    font-weight: 700 !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 8px;
    box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    margin-top: 5px; margin-bottom: 5px;
    transition: transform 0.2s;
}
[data-testid="stSidebar"] button:hover {
    transform: scale(1.02);
    box-shadow: 0 0 15px rgba(124, 58, 237, 0.6);
}

[data-testid="stSidebar"] label { color: #cbd5e1 !important; font-weight: 600; }
[data-testid="stSidebar"] .stMarkdown p { color: #94a3b8 !important; }

/* ------------------------------------------------------- */
/* MAIN CONTENT STYLES                                     */
/* ------------------------------------------------------- */

.product-card {
    background: rgba(255, 255, 255, 0.05);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 16px;
    padding: 20px;
    backdrop-filter: blur(10px);
    transition: transform 0.4s, border-color 0.3s;
}
.product-card:hover {
    transform: translateY(-10px);
    border-color: #818cf8;
    box-shadow: 0 20px 50px rgba(0,0,0,0.5);
}

[data-testid="stPopover"] > button {
    background: linear-gradient(135deg, #6d28d9, #8b5cf6);
    color: white;
    border-radius: 50px;
    padding: 12px 28px;
    font-family: 'Orbitron', sans-serif;
    font-weight: 700;
    animation: float 4s ease-in-out infinite;
    border: 1px solid rgba(255,255,255,0.3);
}

.chat-header {
    background: linear-gradient(90deg, #4c1d95, #6d28d9);
    padding: 20px;
    border-radius: 12px 12px 0 0;
    color: white;
    display: flex; align-items: center; gap: 15px;
    margin: -1rem -1rem 1rem -1rem;
}
.ai-avatar {
    width: 40px; height: 40px;
    background: radial-gradient(circle at 30% 30%, #a78bfa, #4c1d95);
    border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-size: 20px;
}

/* CHAT BUBBLES (High Contrast) */
.chat-bubble-user {
    background: #3b82f6; 
    color: white !important; 
    padding: 12px;
    border-radius: 18px 18px 2px 18px; 
    margin-bottom: 10px;
    float: right; 
    clear: both; 
    max-width: 85%;
    font-weight: 500;
}

.chat-bubble-bot {
    background-color: #334155;
    color: #ffffff !important;
    padding: 12px 18px;
    border-radius: 18px 18px 18px 2px;
    margin-bottom: 10px;
    float: left;
    clear: both;
    max-width: 85%;
    font-weight: 500;
    border: 1px solid rgba(255,255,255,0.1);
}

</style>

<div style="text-align: center; perspective: 1000px;">
    <div class="vestra-3d-logo">VESTRA</div>
    <div style="font-family: 'Rajdhani'; font-size: 20px; color: #94a3b8; letter-spacing: 6px; text-transform: uppercase;">
        Next-Gen Intelligent Commerce
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
        emb_method=emb_method
    )

st.session_state.setdefault("history", [("assistant", "Hi! I'm Kai. How can I help you style today?")])
st.session_state.setdefault("cart", [])
st.session_state.setdefault("orders", [])
st.session_state.setdefault("last_lookbook", {})
st.session_state.setdefault("reward_points", 200)
st.session_state.setdefault("location", "US")

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    # 1. Regions & Settings
    st.header("🌐 Region & Settings")
    st.caption("Auto-detecting locale and currency")

    selected_loc = st.selectbox("Select Region", ["US", "EU", "UK", "JP"], index=0, key="region_select")
    st.session_state.location = selected_loc

    # Rewards UI
    st.markdown("---")
    st.header("💎 Rewards")
    st.metric("Loyalty XP", f"{st.session_state.reward_points}", delta=10)
    st.progress(min(st.session_state.reward_points / 1000, 1.0))

    # 2. Context Engine
    st.markdown("---")
    st.header("🎯 Context Engine")
    st.caption("Customize your styling parameters")


    def preference_changed():
        st.session_state.refresh_lookbook = True


    occasion = st.selectbox("Occasion", ["Wedding", "Office", "Casual", "Gym", "Date Night", "Cyberpunk Party"],
                            index=2, on_change=preference_changed)
    weather = st.selectbox("Weather", ["Sunny", "Rainy", "Cold", "Snow"], index=0, on_change=preference_changed)
    base_size = st.selectbox("Your Size", ["XS", "S", "M", "L", "XL"], index=2, on_change=preference_changed)

    local_size_display = SizeConverter.convert(base_size, st.session_state.location)
    st.info(f"Shopping Size: {local_size_display}")

    budget_min, budget_max = st.slider("Budget", 20, 1000, (50, 500), on_change=preference_changed)

    # Cart Section
    st.markdown("---")
    st.header(f"🛒 Cart ({len(st.session_state.cart)})")
    if st.session_state.cart:
        if st.button("💳 Checkout Now", type="primary", use_container_width=True):
            st.session_state.show_checkout = True
        for i, item in enumerate(st.session_state.cart):
            if st.button(f"Remove {item['title'][:10]}...", key=f"rm_{i}"):
                st.session_state.cart.pop(i)
                rerun()
    else:
        st.caption("Cart is empty")

    # 3. Return & Predict Buttons
    st.markdown("---")
    st.header("⚡ Actions")

    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button("🔄 Return Item", use_container_width=True):
            st.session_state.show_return_items = True
    with col_act2:
        if st.button("🔮 Predict Buy", use_container_width=True):
            st.session_state.run_prediction = True

# ---------------------------------------------------------
# Logic Processing (Lookbook Generation)
# ---------------------------------------------------------
if st.session_state.get("refresh_lookbook", False) and st.session_state.history:
    last_query = st.session_state.history[-1][1] if st.session_state.history[-1][0] == 'user' else "Recommendations"
    full_context = f"{last_query}. Context: {occasion}, {weather} weather, {st.session_state.location} region."
    agent = st.session_state.agent
    retrieved, _ = agent.retrieve(full_context, k=8)
    filtered = [p for p in retrieved if p and budget_min <= p.get("price", 0) <= budget_max]
    parsed = agent.generate_lookbook(full_context, filtered, st.session_state.history, raw_input=last_query)
    st.session_state.last_lookbook = parsed
    st.session_state.refresh_lookbook = False
    rerun()

# ---------------------------------------------------------
# Main Layout
# ---------------------------------------------------------
col_spacer, col_trigger = st.columns([5, 1])

# --- CHAT POPOVER ---
with col_trigger:
    with st.popover("💬 CHAT WITH KAI", use_container_width=True):
        st.markdown("""
            <div class="chat-header">
                <div class="ai-avatar">🤖</div>
                <div>
                    <div style="font-weight: 700; font-size: 16px;">KAI v2.0</div>
                    <div style="font-size: 11px; color: #a5b4fc;">Online</div>
                </div>
            </div>
        """, unsafe_allow_html=True)

        chat_container = st.container(height=400)
        with chat_container:
            for role, text in st.session_state.history:
                css_class = "chat-bubble-user" if role == "user" else "chat-bubble-bot"
                st.markdown(f'<div class="{css_class}">{text}</div><div style="clear:both"></div>',
                            unsafe_allow_html=True)

        st.markdown("---")
        uploaded_chat_file = st.file_uploader("Attach", type=["png", "jpg"], key="chat_upload",
                                              label_visibility="collapsed")
        user_input = st.text_input("Message...", key="chat_input", label_visibility="collapsed",
                                   placeholder="Ask Kai for styling advice...")

        if st.button("Send", use_container_width=True):
            if user_input or uploaded_chat_file:
                msg_content = user_input if user_input else "Uploaded an image."
                if uploaded_chat_file: msg_content += f" [File: {uploaded_chat_file.name}]"
                st.session_state.history.append(("user", msg_content))

                context_query = f"{user_input}. User is in {st.session_state.location}. Weather: {weather}. Occasion: {occasion}."
                agent = st.session_state.agent
                retrieved, _ = agent.retrieve(context_query, k=15)
                parsed = agent.generate_lookbook(context_query, retrieved, st.session_state.history,
                                                 raw_input=msg_content)

                st.session_state.last_lookbook = parsed
                st.session_state.history.append(("assistant", parsed.get("chat_response", "Updated styles.")))
                rerun()

# --- PRODUCT GRID ---
st.markdown("### 👗 Curated Selection")
lookbook = st.session_state.get("last_lookbook", {})

if lookbook and "lookbook" in lookbook and len(lookbook["lookbook"]) > 0:
    grid_cols = st.columns(3)
    for idx, item in enumerate(lookbook["lookbook"]):
        pid = item.get("product_id") or item.get("id")
        product = fetch_product_by_id(pid)
        if product:
            with grid_cols[idx % 3]:
                st.markdown(f'<div class="product-card">', unsafe_allow_html=True)
                img_url = product['image_url'] if product[
                    'image_url'] else "https://via.placeholder.com/300x300?text=Vestra"
                st.image(img_url, use_container_width=True)
                st.markdown(f"<div style='font-weight:600; margin-bottom:5px;'>{product['title']}</div>",
                            unsafe_allow_html=True)
                st.caption(f"✨ {item.get('reason', 'AI Match')}")
                st.markdown(f"**${product['price']}**", unsafe_allow_html=True)
                if st.button("➕ Add", key=f"add_{pid}"):
                    st.session_state.cart.append(product)
                    st.session_state.reward_points += 5
                    st.toast(f"Added to cart!")
                st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Kai is analyzing current trends for you. Open the Chat to begin.")

# ---------------------------------------------------------
# Overlays (Checkout, Returns, Predictions)
# ---------------------------------------------------------

# PREDICTION OVERLAY
if st.session_state.get("run_prediction"):
    st.toast("Running AI Prediction Model...")
    if st.session_state.orders:
        recs = st.session_state.agent.post_purchase_recommendations(st.session_state.orders[-1]["items"], top_n=3)
        st.markdown("### 🔮 AI Predicted Next Purchase")
        p_cols = st.columns(3)
        for i, r in enumerate(recs):
            with p_cols[i]:
                st.info(f"Recommended: {r['title']}")
    else:
        st.warning("No purchase history found for predictions.")
    st.session_state.run_prediction = False

# RETURNS OVERLAY
if st.session_state.get("show_return_items"):
    st.markdown("### 🔄 Return Processing")
    if st.button("Close Return Menu"):
        st.session_state.show_return_items = False
        rerun()

    has_orders = False
    for order_idx, order in enumerate(st.session_state.orders):
        if order["items"]:
            has_orders = True
            st.write(f"**Order #{order['order_id']}**")
            for item_idx, item in enumerate(order["items"]):
                if st.button(f"Return {item['title']}", key=f"ret_{order_idx}_{item_idx}"):
                    eligible, msg = PolicyManager.check_return_eligibility(order.get("date"))
                    if eligible:
                        order["items"].pop(item_idx)
                        st.success(f"Return processed for {item['title']}")
                    else:
                        st.error(msg)
                    rerun()
    if not has_orders: st.write("No eligible items for return.")

# CHECKOUT OVERLAY (Updated Implementation)
if st.session_state.get("show_checkout"):
    st.sidebar.markdown("## 🧾 Secure Checkout")
    subtotal = sum([item['price'] for item in st.session_state.cart])

    shipping_method = st.sidebar.radio("Delivery Method", ["Standard", "Express", "Hyper-Drone"], index=0)
    shipping_cost = PolicyManager.get_shipping_cost(shipping_method)
    final_total = subtotal + shipping_cost

    st.sidebar.markdown(f"**Total:** :green[${final_total:.2f}]")

    with st.sidebar.form("checkout_form"):
        name = st.text_input("Name")
        email = st.text_input("Email")
        addr = st.text_area("Shipping Address")
        submitted = st.form_submit_button("Confirm Order")

        if submitted:
            order_id = len(st.session_state.orders) + 1
            pts = RewardSystem.calculate_points("purchase", amount=final_total)
            st.session_state.reward_points += pts
            st.session_state.orders.append({
                "order_id": order_id, "items": st.session_state.cart.copy(), "total": final_total,
                "name": name, "email": email, "address": addr, "date": datetime.now().date()
            })
            st.session_state.cart = []
            st.session_state.show_checkout = False
            st.success(f"Order #{order_id} confirmed! You earned {pts} XP.")
            rerun()