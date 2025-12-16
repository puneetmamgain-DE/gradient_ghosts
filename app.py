import os
from datetime import datetime

import streamlit as st
from streamlit import rerun

from agent import ShoppingAgent
from utils import fetch_product_by_id, SizeConverter, RewardSystem, PolicyManager, WeatherService, \
    GoogleReviewService, encode_image, TrendService, MaterialAnalyzer, CartOptimizer, ReplenishmentService, \
    PriceLockService

# ---------------------------------------------------------
# Page Configuration
# ---------------------------------------------------------
st.set_page_config(layout="wide", page_title="Vestra — Intelligent Shopping")

# ---------------------------------------------------------
# Styling & UI
# ---------------------------------------------------------
st.markdown("""
<style>
@import url('[https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&family=Rajdhani:wght@500;700&display=swap](https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&family=Rajdhani:wght@500;700&display=swap)');

@keyframes gradient-animation {
    0% { background-position: 0% 50%; }
    50% { background-position: 100% 50%; }
    100% { background-position: 0% 50%; }
}

@keyframes float {
    0% { transform: translateY(0px) scale(1); box-shadow: 0 5px 15px rgba(124, 58, 237, 0.4); }
    50% { transform: translateY(-6px) scale(1.02); box-shadow: 0 25px 40px rgba(124, 58, 237, 0.6); }
    100% { transform: translateY(0px) scale(1); box-shadow: 0 5px 15px rgba(124, 58, 237, 0.4); }
}

@keyframes logo-3d-move {
    0% { transform: perspective(1000px) rotateX(10deg) rotateY(-5deg) translateY(0); text-shadow: 0 5px 0 #4c1d95, 0 10px 20px rgba(0,0,0,0.5); }
    50% { transform: perspective(1000px) rotateX(0deg) rotateY(5deg) translateY(-10px); text-shadow: 0 15px 0 #4c1d95, 0 20px 40px rgba(0,0,0,0.7); }
    100% { transform: perspective(1000px) rotateX(10deg) rotateY(-5deg) translateY(0); text-shadow: 0 5px 0 #4c1d95, 0 10px 20px rgba(0,0,0,0.5); }
}

@keyframes shine-flow {
    0% { background-position: 0% 50%; }
    100% { background-position: 200% 50%; }
}

.stApp {
    background: linear-gradient(-45deg, #020617, #0f172a, #1e1b4b, #312e81);
    background-size: 400% 400%;
    animation: gradient-animation 15s ease infinite;
    color: #e2e8f0;
}

.vestra-3d-logo {
    font-family: 'Orbitron', sans-serif;
    font-size: 72px;
    font-weight: 900;
    text-align: center;
    background: linear-gradient(90deg, #ffffff, #818cf8, #ffffff);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: logo-3d-move 6s ease-in-out infinite alternate, shine-flow 4s linear infinite;
    margin-bottom: 0.2rem;
    letter-spacing: 4px;
    display: inline-block;
}

[data-testid="stSidebar"] {
    background-color: rgba(10, 10, 25, 0.95);
    border-right: 1px solid rgba(255, 255, 255, 0.1);
}

[data-testid="stSidebar"] h1, [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 {
    color: #e0e7ff !important;
    font-family: 'Rajdhani', sans-serif;
}

[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: #1e293b !important;
    color: white !important;
    border: 1px solid rgba(129, 140, 248, 0.5) !important;
    border-radius: 8px !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: #ffffff !important;
}

[data-testid="stSidebar"] button {
    background: linear-gradient(90deg, #4f46e5, #7c3aed);
    color: white !important;
    font-weight: 700 !important;
    border: 1px solid rgba(255, 255, 255, 0.2) !important;
    border-radius: 8px;
    margin-top: 5px; margin-bottom: 5px;
}

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

.rating-badge {
    background: rgba(255, 215, 0, 0.2);
    border: 1px solid gold;
    color: gold;
    padding: 2px 8px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
    display: inline-block;
    margin-bottom: 5px;
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
.chat-bubble-user {
    background: #3b82f6; color: white !important; padding: 12px;
    border-radius: 18px 18px 2px 18px; margin-bottom: 10px; float: right; clear: both; max-width: 85%;
}
.chat-bubble-bot {
    background-color: #334155; color: #ffffff !important; padding: 12px 18px;
    border-radius: 18px 18px 18px 2px; margin-bottom: 10px; float: left; clear: both; max-width: 85%;
    border: 1px solid rgba(255,255,255,0.1);
}
.lock-badge {
    background: rgba(34, 197, 94, 0.2);
    border: 1px solid #22c55e;
    color: #22c55e;
    padding: 2px 6px;
    border-radius: 4px;
    font-size: 11px;
    margin-left: 5px;
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
if "weather_context" not in st.session_state:
    with st.spinner("Analyzing location and weather..."):
        st.session_state.weather_context = WeatherService.get_context()
        if st.session_state.weather_context["success"]:
            st.toast(
                f"Detected: {st.session_state.weather_context['city']}, {st.session_state.weather_context['condition']}")
        else:
            st.toast("Using default location settings.")

if "agent" not in st.session_state:
    emb_method = "openai" if os.getenv("OPENAI_API_KEY") else "local"
    st.session_state.agent = ShoppingAgent(
        index_path_openai="product_index_openai.faiss",
        index_path_local="product_index_local.faiss",
        emb_method=emb_method
    )

st.session_state.setdefault("history", [("assistant",
                                         "Hi! I'm Kai. Upload a selfie for skin tone matching or just tell me what you need! Your prices will be Intent-Locked.")])
st.session_state.setdefault("cart", [])
st.session_state.setdefault("orders", [])
st.session_state.setdefault("last_lookbook", {})
st.session_state.setdefault("reward_points", 200)
st.session_state.setdefault("location", "US")
st.session_state.setdefault("skin_profile", None)  # Store skin analysis result

# ---------------------------------------------------------
# Sidebar
# ---------------------------------------------------------
with st.sidebar:
    st.header("🌐 Region & Settings")

    detected_country = st.session_state.weather_context.get("country", "US")
    region_options = ["US", "EU", "UK", "JP"]
    default_region_idx = 0
    if detected_country in region_options:
        default_region_idx = region_options.index(detected_country)

    selected_loc = st.selectbox("Select Region", region_options, index=default_region_idx, key="region_select")
    st.session_state.location = selected_loc

    # UPDATED: Made visible and prominent using st.success
    st.success(f"📍 Detected: {st.session_state.weather_context.get('city', 'Bhubaneswar')}")

    st.markdown("---")
    st.header("💎 Rewards & Protection")
    st.metric("Loyalty XP", f"{st.session_state.reward_points}", delta=10)
    st.progress(min(st.session_state.reward_points / 1000, 1.0))

    # --- INTENT-LOCKED PRICING: AUTO-REFUND SCAN ---
    if st.button("🛡️ Scan for Price Drops", help="Intent-Locked Pricing: Check if prices fell after you bought."):
        with st.spinner("Checking global market prices..."):
            refund_amt, details = PriceLockService.calculate_protection_refund(st.session_state.orders)
            if refund_amt > 0:
                # Refund via XP
                xp_refund = int(refund_amt * 10)  # 1 USD = 10 XP
                st.session_state.reward_points += xp_refund
                st.success(f"💰 Refund Processed! ${refund_amt} credited as {xp_refund} XP.")
                for d in details:
                    st.caption(f"📉 {d}")
            else:
                st.info("No price drops detected. Your locked prices were the best.")

    st.markdown("---")
    st.header("🎯 Context Engine")


    def preference_changed():
        st.session_state.refresh_lookbook = True


    occasion = st.selectbox("Occasion", ["Wedding", "Office", "Casual", "Gym", "Date Night", "Cyberpunk Party"],
                            index=2, on_change=preference_changed)

    detected_condition = st.session_state.weather_context.get("condition", "Sunny")
    weather_options = ["Sunny", "Rainy", "Cold", "Snow", "Cloudy"]
    default_weather_idx = weather_options.index(detected_condition) if detected_condition in weather_options else 0
    weather = st.selectbox("Weather", weather_options, index=default_weather_idx, on_change=preference_changed)

    base_size = st.selectbox("Your Size", ["XS", "S", "M", "L", "XL"], index=2, on_change=preference_changed)
    local_size_display = SizeConverter.convert(base_size, st.session_state.location)
    st.info(f"Shopping Size: {local_size_display}")

    budget_min, budget_max = st.slider("Budget", 20, 1000, (50, 500), on_change=preference_changed)

    # Display Skin Profile in Sidebar if available
    if st.session_state.skin_profile:
        st.success(f"🎨 Skin Profile: {st.session_state.skin_profile[:30]}...")

    st.markdown("---")
    st.header(f"🛒 Cart ({len(st.session_state.cart)})")
    if st.session_state.cart:
        # Autonomous Cart Optimization: Check shipping
        cart_total = sum(i['price'] for i in st.session_state.cart)
        ship_gap = CartOptimizer.check_shipping_threshold(cart_total, 50.0)
        if ship_gap > 0:
            st.warning(f"Add ${ship_gap:.2f} more for Free Shipping!")
        else:
            st.success("Free Shipping Unlocked!")

        if st.button("💳 Checkout Now", type="primary", use_container_width=True):
            st.session_state.show_checkout = True
        for i, item in enumerate(st.session_state.cart):
            # Display Lock Status in Cart
            lock_msg = f"🔒 Locked @ ${item['price']}"
            st.markdown(f"**{item['title'][:15]}..** ({lock_msg})")
            if st.button(f"Remove {item['title'][:5]}..", key=f"rm_{i}"):
                st.session_state.cart.pop(i)
                rerun()
    else:
        st.caption("Cart is empty")

    st.markdown("---")
    st.header("⚡ Actions")
    col_act1, col_act2 = st.columns(2)
    with col_act1:
        if st.button("🔄 Return Item", use_container_width=True): st.session_state.show_return_items = True
    with col_act2:
        if st.button("🔮 Predict Buy", use_container_width=True): st.session_state.run_prediction = True

# ---------------------------------------------------------
# Logic Processing
# ---------------------------------------------------------
if st.session_state.get("refresh_lookbook", False) and st.session_state.history:
    last_query = st.session_state.history[-1][1] if st.session_state.history[-1][0] == 'user' else "Recommendations"
    # Augment query with skin profile if available
    skin_txt = f" Skin Tone Context: {st.session_state.skin_profile}" if st.session_state.skin_profile else ""
    # Inject Trend Logic
    season = st.session_state.weather_context.get("season", "Spring")
    active_trends = TrendService.get_trends(st.session_state.location, season)
    trend_txt = f" Current Trends in {st.session_state.location}: {', '.join(active_trends)}."

    full_context = f"{last_query}. Context: {occasion}, {weather} weather, {st.session_state.location} region.{skin_txt}{trend_txt}"

    agent = st.session_state.agent
    retrieved, _ = agent.retrieve(full_context, k=8)
    filtered = [p for p in retrieved if p and budget_min <= p.get("price", 0) <= budget_max]
    parsed = agent.generate_lookbook(full_context, filtered, st.session_state.history, raw_input=last_query,
                                     skin_analysis_result=st.session_state.skin_profile)
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
        uploaded_chat_file = st.file_uploader("Attach Photo for Skin Analysis", type=["png", "jpg", "jpeg"],
                                              key="chat_upload",
                                              label_visibility="visible")
        user_input = st.text_input("Message...", key="chat_input", label_visibility="collapsed",
                                   placeholder="Ask Kai for styling advice...")

        if st.button("Send", use_container_width=True):
            if user_input or uploaded_chat_file:
                agent = st.session_state.agent
                msg_content = user_input if user_input else "Uploaded an image."

                # Handle Image Analysis
                if uploaded_chat_file:
                    st.toast("Analyzing skin tone via AI Vision...")
                    img_b64 = encode_image(uploaded_chat_file)
                    skin_analysis = agent.analyze_skin_tone(img_b64)
                    if skin_analysis:
                        st.session_state.skin_profile = skin_analysis
                        msg_content += f" [Analyzed: {skin_analysis}]"
                        st.toast("Skin profile updated!")

                st.session_state.history.append(("user", msg_content))

                # Build Context
                skin_txt = f" Recommended colors based on skin tone: {st.session_state.skin_profile}" if st.session_state.skin_profile else ""
                # Inject Trends into Context
                season = st.session_state.weather_context.get("season", "Spring")
                active_trends = TrendService.get_trends(st.session_state.location, season)
                trend_txt = f" Trends: {', '.join(active_trends)}."

                context_query = f"{user_input}. User is in {st.session_state.location}. Weather: {weather}. Occasion: {occasion}.{skin_txt}{trend_txt}"

                # Retrieve & Generate
                retrieved, _ = agent.retrieve(context_query, k=15)
                parsed = agent.generate_lookbook(context_query, retrieved, st.session_state.history,
                                                 raw_input=msg_content,
                                                 skin_analysis_result=st.session_state.skin_profile)

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
                    'image_url'] else "[https://via.placeholder.com/300x300?text=Vestra](https://via.placeholder.com/300x300?text=Vestra)"
                st.image(img_url, use_container_width=True)
                st.markdown(f"<div style='font-weight:600; margin-bottom:5px;'>{product['title']}</div>",
                            unsafe_allow_html=True)

                # --- NEW: DISPLAY EXTERNAL RATING ---
                # Check if rating exists in item (from agent) or fetch on fly (if not in item)
                # We check the loopbook item first because agent already fetched it
                rating = product.get(
                    'ext_rating')  # Agent might not have saved it to product dict in CSV, so we use session state or fetch

                # Fetch fresh if needed (mostly for display purposes if not in agent response)
                if 'ext_rating' not in product:
                    rev_data = GoogleReviewService.fetch_rating(product['title'])
                    rating = rev_data['rating']
                    source = rev_data['source']
                else:
                    source = product.get('ext_source', 'Web')

                st.markdown(f'<div class="rating-badge">⭐ {rating}/5 ({source})</div>', unsafe_allow_html=True)

                # --- NEW: FABRIC ANALYSIS ---
                mat_analysis = MaterialAnalyzer.analyze(product.get('description', ''), weather)
                for endo in mat_analysis['endorsements']:
                    st.caption(f"{endo}")
                for warn in mat_analysis['warnings']:
                    st.caption(f"{warn}")

                st.caption(f"✨ {item.get('reason', 'AI Match')}")

                # PRICE DISPLAY WITH LOCK ICON
                st.markdown(f"**${product['price']}** <span class='lock-badge'>Intent-Locked</span>",
                            unsafe_allow_html=True)

                if st.button("➕ Add & Lock Price", key=f"add_{pid}"):
                    # INTENT LOCK: Record the locked price
                    product['locked_price'] = product['price']
                    product['locked_date'] = datetime.now()
                    st.session_state.cart.append(product)
                    st.session_state.reward_points += 5
                    st.toast(f"Price locked at ${product['price']}!")
                st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Kai is analyzing current trends for you. Open the Chat to begin.")

# ---------------------------------------------------------
# Overlays
# ---------------------------------------------------------
if st.session_state.get("run_prediction"):
    st.toast("Running AI Prediction Model...")
    # 1. Post Purchase Recommendations
    if st.session_state.orders:
        recs = st.session_state.agent.post_purchase_recommendations(st.session_state.orders[-1]["items"], top_n=3)
        st.markdown("### 🔮 Complete The Look")
        p_cols = st.columns(3)
        for i, r in enumerate(recs):
            with p_cols[i]:
                st.info(f"Recommended: {r['title']}")
                if st.button("Add Bundle", key=f"pred_add_{i}"):
                    # Apply Lock on Bundle
                    r['locked_price'] = r['price']
                    r['locked_date'] = datetime.now()
                    st.session_state.cart.append(r)
                    rerun()

    # 2. Replenishment Prediction (Consumables)
    replenish_items = ReplenishmentService.predict_next_buy(st.session_state.orders)
    if replenish_items:
        st.markdown("### 🔄 It's Time to Restock")
        for item in replenish_items:
            st.warning(f"You last bought {item['title']} 30 days ago. Add to cart?")
            if st.button(f"Restock {item['title']}", key=f"restock_{item['id']}"):
                item['locked_price'] = item['price']
                st.session_state.cart.append(item)
                rerun()
    elif not st.session_state.orders:
        st.warning("No purchase history found for predictions.")
    else:
        st.info("No immediate replenishment needs detected.")

    st.session_state.run_prediction = False

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
                        # Autonomous: Reserve logic could go here
                    else:
                        st.error(msg)
                    rerun()
    if not has_orders: st.write("No eligible items for return.")

if st.session_state.get("show_checkout"):
    st.sidebar.markdown("## 🧾 Secure Checkout")
    subtotal = sum([item['price'] for item in st.session_state.cart])
    shipping_method = st.sidebar.radio("Delivery Method", ["Standard", "Express", "Hyper-Drone"], index=0)
    shipping_cost = PolicyManager.get_shipping_cost(shipping_method)

    # Auto-apply free shipping if threshold met
    threshold = PolicyManager.get_free_shipping_threshold("Standard")  # Assuming standard has free tier
    if subtotal > threshold and shipping_method == "Standard":
        shipping_cost = 0
        st.sidebar.success("Free Shipping Applied!")

    final_total = subtotal + shipping_cost

    st.sidebar.markdown(f"**Total:** :green[${final_total:.2f}]")
    st.sidebar.info("🔒 Intent-Locked Pricing Active. If price drops in 30 days, we auto-refund.")

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