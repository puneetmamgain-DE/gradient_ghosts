import streamlit as st
from streamlit import rerun
from agent import ShoppingAgent
# Added PolicyManager and datetime import
from utils import load_products, fetch_product_by_id, SizeConverter, RewardSystem, PolicyManager
import os
from datetime import datetime

st.set_page_config(layout="wide", page_title="Vestra — Intelligent Shopping")

# ---------------------------------------------------------
# Module 1: Branding (Vestra) & Futuristic CSS
# ---------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Inter:wght@300;400;600&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    color: #e2e8f0;
}

body {
    background: linear-gradient(135deg, #020617, #0f172a, #1e1b4b);
    background-attachment: fixed;
}

section.main > div {
    background: rgba(15, 23, 42, 0.6);
    backdrop-filter: blur(12px);
    border-radius: 16px;
    padding: 2rem;
    border: 1px solid rgba(255,255,255,0.05);
}

/* --- SIDEBAR STYLING --- */
[data-testid="stSidebar"] {
    background: #020617;
    border-right: 1px solid rgba(255,255,255,0.1);
}

/* 1. Force Headers, Text, Paragraphs, and List Items to White */
[data-testid="stSidebar"] h1, 
[data-testid="stSidebar"] h2, 
[data-testid="stSidebar"] h3, 
[data-testid="stSidebar"] span, 
[data-testid="stSidebar"] label, 
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] li,
[data-testid="stSidebar"] div[data-testid="stMarkdownContainer"] p {
    color: #f8fafc !important;
}

/* 2. Fix Sidebar Button Visibility */
[data-testid="stSidebar"] button {
    background-color: #3b82f6 !important; /* Bright Blue */
    color: white !important;
    border: 1px solid rgba(255,255,255,0.2) !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] button:hover {
    background-color: #2563eb !important;
    border-color: white !important;
}

/* 3. Fix Input/Select Fields Background */
[data-testid="stSidebar"] input, 
[data-testid="stSidebar"] textarea, 
[data-testid="stSidebar"] [data-baseweb="select"] > div {
    background-color: rgba(255, 255, 255, 0.1) !important;
    color: white !important;
    border-color: rgba(255,255,255,0.2) !important;
}

/* Fix text inside Selectbox dropdowns */
[data-testid="stSidebar"] [data-baseweb="select"] span {
    color: white !important;
}

/* Fix Dropdown Menu Popover */
[data-baseweb="menu"] {
    background-color: #0f172a !important;
}
[data-baseweb="menu"] li {
    color: white !important;
}

/* 3D Branding Title */
.vestra-title {
    font-family: 'Orbitron', sans-serif;
    font-size: 56px;
    font-weight: 900;
    text-align: center;
    background: linear-gradient(to right, #818cf8, #c084fc, #f472b6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0px 0px 20px rgba(129, 140, 248, 0.5);
    margin-bottom: 0.5rem;
}

.tagline {
    text-align: center;
    font-size: 18px;
    color: #94a3b8;
    margin-bottom: 3rem;
    letter-spacing: 2px;
}

/* Card Styling */
.product-card {
    background: linear-gradient(180deg, rgba(255,255,255,0.03), rgba(255,255,255,0.01));
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 12px;
    padding: 15px;
    transition: transform 0.2s;
}
.product-card:hover {
    transform: translateY(-5px);
    border-color: #818cf8;
}
</style>

<div class="vestra-title">VESTRA</div>
<div class="tagline">YOUR STYLE, INTELLIGENTLY CURATED.</div>
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

st.session_state.setdefault("history", [])
st.session_state.setdefault("cart", [])
st.session_state.setdefault("orders", [])
st.session_state.setdefault("last_lookbook", {})
# Module 7: Points Initialization
st.session_state.setdefault("reward_points", 200)  # Start with welcome bonus
st.session_state.setdefault("location", "US")

# ---------------------------------------------------------
# Sidebar: Context, Location & Rewards
# ---------------------------------------------------------
with st.sidebar:
    st.subheader("🌐 Global Settings")
    # Module 6: Location Detection (Mocked via UI)
    selected_loc = st.selectbox("Region (Auto-Detected)", ["US", "EU", "UK", "JP"], index=0)
    st.session_state.location = selected_loc

    st.subheader("💎 Vestra Rewards")
    st.metric("Loyalty Points", st.session_state.reward_points, delta=10)
    st.progress(min(st.session_state.reward_points / 1000, 1.0))
    st.caption("Level: Trendsetter (Next tier at 1000)")

    st.markdown("---")
    st.subheader("🎯 Context")


    def preference_changed():
        st.session_state.refresh_lookbook = True


    occasion = st.selectbox("Occasion", ["Wedding", "Office", "Casual", "Gym", "Date Night"], index=2,
                            on_change=preference_changed)
    weather = st.selectbox("Weather", ["Sunny", "Rainy", "Cold", "Snow"], index=0, on_change=preference_changed)
    base_size = st.selectbox("Your Size", ["XS", "S", "M", "L", "XL"], index=2, on_change=preference_changed)

    # Module 6: Real-time Size Conversion Display
    local_size_display = SizeConverter.convert(base_size, st.session_state.location)
    st.info(f"Shopping in: {local_size_display}")

    budget_min, budget_max = st.slider("Budget", 20, 1000, (50, 500), on_change=preference_changed)

    # Cart Display
    st.markdown("---")
    st.subheader(f"🛒 Cart ({len(st.session_state.cart)})")

    if st.session_state.cart:
        for i, item in enumerate(st.session_state.cart):
            # Using Markdown for Cart Item visibility
            st.markdown(f"**{i + 1}. {item['title'][:20]}...** — ${item['price']}")
            if st.button(f"Remove Item {i + 1}", key=f"rm_{i}"):
                st.session_state.cart.pop(i)
                rerun()

        st.markdown("---")
        if st.button("Proceed to Checkout"):
            st.session_state.show_checkout = True
    else:
        st.write("Your cart is empty.")

# ---------------------------------------------------------
# Module 3: AR Room Vibe Auditor / Fit Predictor
# ---------------------------------------------------------
with st.expander("🔮 AR Vibe Auditor & Virtual Try-On"):
    col_ar1, col_ar2 = st.columns([1, 2])
    with col_ar1:
        ar_mode = st.radio("Select Mode", ["Room Vibe Detect", "Virtual Fit"])
        uploaded_file = st.file_uploader("Upload AR Image", type=["jpg", "png"], key="ar_upload")
    with col_ar2:
        if uploaded_file:
            # Replaced deprecated use_column_width logic
            st.image(uploaded_file, use_container_width=True)
            if st.button("Analyze with AI"):
                # Simulation of Computer Vision analysis
                st.success("Analysis Complete!")
                if ar_mode == "Room Vibe Detect":
                    st.write("**Detected Style:** Mid-Century Modern")
                    st.write("**Suggestion:** Recommending earth-tone furniture.")
                else:
                    st.write("**Fit Prediction:** 92% Match")
                    st.write(f"The {base_size} drapes perfectly on your frame.")

                # Module 7: Gamification Reward
                points = RewardSystem.calculate_points("ar_try_on")
                st.session_state.reward_points += points
                st.toast(f"Earned {points} points for using AR!")

# ---------------------------------------------------------
# Main Chat & Lookbook Logic
# ---------------------------------------------------------
col1, col2 = st.columns([2, 3])

# Refresh logic
if st.session_state.get("refresh_lookbook", False) and st.session_state.history:
    last_query = st.session_state.history[-1][1] if st.session_state.history[-1][0] == 'user' else "Recommendations"
    # Inject context into query invisibly
    full_context = f"{last_query}. Context: {occasion}, {weather} weather, {st.session_state.location} region."

    agent = st.session_state.agent
    retrieved, _ = agent.retrieve(full_context, k=8)

    # Filter by budget
    filtered = [p for p in retrieved if p and budget_min <= p.get("price", 0) <= budget_max]

    parsed = agent.generate_lookbook(full_context, filtered, st.session_state.history, raw_input=last_query)
    st.session_state.last_lookbook = parsed
    st.session_state.refresh_lookbook = False
    rerun()

with col1:
    st.markdown("### 💬 Kai (AI Assistant)")

    # Chat History
    for role, text in st.session_state.history:
        align = "right" if role == "user" else "left"
        color = "#3b82f6" if role == "user" else "#334155"

        # Explicitly added 'color: white' to the inline style
        st.markdown(
            f"<div style='text-align:{align}; background:{color}; color: white; padding:10px; border-radius:10px; margin:5px; display:inline-block;'>{text}</div>",
            unsafe_allow_html=True)

        st.markdown(f"<div style='clear:both'></div>", unsafe_allow_html=True)

    # --- File Uploader for Kai ---
    uploaded_chat_file = st.file_uploader("Upload a file (Image/PDF) for context:",
                                          type=["png", "jpg", "jpeg", "pdf", "txt"], key="chat_upload")

    user_input = st.text_input("Ask Kai...", key="chat_input")

    # Check if either text input or file input is present
    if st.button("Send") and (user_input or uploaded_chat_file):

        # Construct message content
        msg_content = user_input if user_input else "Uploaded a file."
        if uploaded_chat_file:
            msg_content += f" [Attached File: {uploaded_chat_file.name}]"

        st.session_state.history.append(("user", msg_content))

        # --- MULTI-TURN LOGIC for Retrieval ---
        # Append previous assistant context to the query so searching for "Red"
        # acts like "Red Shoes" if Kai just asked about shoes.
        context_prefix = ""
        # Look back for context, but keep it relevant
        if len(st.session_state.history) >= 2:
            # Grab last 2-3 exchanges to form a dense context query
            recent_turns = st.session_state.history[-3:]
            for r, t in recent_turns:
                context_prefix += f"{t} "

        # Build Contextual Query
        context_query = f"{context_prefix} {user_input}. User is in {st.session_state.location}. Weather is {weather}. Occasion is {occasion}."

        if uploaded_chat_file:
            context_query += f" The user also uploaded a file named {uploaded_chat_file.name} for visual/text context."

        agent = st.session_state.agent

        # Retrieve
        # We retrieve broadly (k=15) so the agent can filter/select later
        retrieved, _ = agent.retrieve(context_query, k=15)

        # Pass raw input so agent can extract budget (e.g. "200") and handle slots
        parsed = agent.generate_lookbook(context_query, retrieved, st.session_state.history, raw_input=msg_content)

        st.session_state.last_lookbook = parsed

        # Agent response from JSON or default
        agent_msg = parsed.get("chat_response", "I've curated some items for you.")
        st.session_state.history.append(("assistant", agent_msg))
        rerun()

with col2:
    st.markdown("### 👗 Curated for You")
    lookbook = st.session_state.get("last_lookbook", {})

    # Check if lookbook has items. If empty, the agent is likely asking a follow-up.
    if lookbook and "lookbook" in lookbook and len(lookbook["lookbook"]) > 0:
        # Dynamic Grid
        grid_cols = st.columns(2)
        for idx, item in enumerate(lookbook["lookbook"]):
            pid = item.get("product_id") or item.get("id")
            product = fetch_product_by_id(pid)

            if product:
                with grid_cols[idx % 2]:
                    st.markdown('<div class="product-card">', unsafe_allow_html=True)
                    # Use placeholder if no image
                    img_url = product['image_url'] if product[
                        'image_url'] else "https://via.placeholder.com/200x250?text=Vestra+Item"

                    # Updated image display to avoid deprecation warning
                    st.image(img_url, use_container_width=True)

                    st.markdown(f"**{product['title']}**")
                    st.caption(f"{item.get('reason', 'Best match')}")

                    # Module 6: Price & Size Display
                    converted_size = SizeConverter.convert(base_size, st.session_state.location)
                    st.markdown(f"**${product['price']}** | Size: {converted_size}")

                    if st.button("Add to Cart", key=f"add_{pid}"):
                        st.session_state.cart.append(product)
                        # Module 7: Rewards (Small bonus for add)
                        st.session_state.reward_points += 5
                        st.success("Added!")
                    st.markdown('</div>', unsafe_allow_html=True)
    else:
        # Fallback if AI decides to ask a question instead of showing products
        st.info("Kai is refining options. Check the chat for a follow-up question!")

# ---------------------------------------------------------
# Checkout (Consolidated) with Shipping Options
# ---------------------------------------------------------
if st.session_state.get("show_checkout"):
    st.sidebar.markdown("## 🧾 Checkout")

    # Calculate item subtotal
    subtotal = sum([item['price'] for item in st.session_state.cart])

    # Shipping Method Selection
    shipping_method = st.sidebar.radio("Delivery Method", ["Standard", "Express", "Overnight"])
    shipping_cost = PolicyManager.get_shipping_cost(shipping_method)

    # Total calculation
    final_total = subtotal + shipping_cost

    st.sidebar.markdown(f"""
    **Subtotal:** ${subtotal:.2f}  
    **Shipping ({shipping_method}):** ${shipping_cost:.2f}  
    **TOTAL:** :green[${final_total:.2f}]
    """)

    name = st.sidebar.text_input("Name")
    email = st.sidebar.text_input("Email")
    addr = st.sidebar.text_area("Shipping Address")

    if st.sidebar.button("Place Order"):
        order_id = len(st.session_state.orders) + 1

        # Module 7: Purchase Rewards
        pts = RewardSystem.calculate_points("purchase", amount=final_total)
        st.session_state.reward_points += pts

        # Store order with current date for Return Eligibility Check
        st.session_state.orders.append({
            "order_id": order_id,
            "items": st.session_state.cart.copy(),
            "total": final_total,
            "name": name,
            "email": email,
            "address": addr,
            "date": datetime.now().date()  # Timestamp added
        })
        st.session_state.cart = []
        st.session_state.show_checkout = False
        st.sidebar.success(f"Order #{order_id} placed! You earned {pts} points.")
        rerun()

# ---------------------------------------------------------
# Returns Section (Consolidated with Policy Check)
# ---------------------------------------------------------
st.sidebar.markdown("---")
st.sidebar.subheader("🔄 Returns")

if "return_messages" not in st.session_state:
    st.session_state.return_messages = []

# Quick Access to Returns
if st.sidebar.button("My Orders / Return Items"):
    st.session_state.show_return_items = True

if st.session_state.get("show_return_items"):
    has_orders = False
    for order_idx, order in enumerate(st.session_state.orders):
        if order["items"]:
            has_orders = True
            st.sidebar.markdown(f"**Order #{order['order_id']} (Total: ${order['total']:.2f})**")
            # Show date
            st.sidebar.caption(f"Ordered on: {order.get('date', 'Unknown')}")

            for item_idx, item in enumerate(order["items"]):
                if st.sidebar.button(
                        f"Return {item['title']} — ${item['price']}",
                        key=f"return_{order_idx}_{item_idx}"
                ):
                    # CHECK 15-DAY POLICY
                    purchase_date = order.get("date")
                    eligible, msg = PolicyManager.check_return_eligibility(purchase_date)

                    if eligible:
                        refund_amount = item["price"]
                        order["items"].pop(item_idx)
                        order["total"] -= refund_amount

                        # Remove order if empty
                        if len(order["items"]) == 0:
                            st.session_state.orders.pop(order_idx)

                        st.session_state.return_messages.append(
                            f"Return initiated for {item['title']} (${refund_amount:.2f})"
                        )
                        st.toast(f"Return Approved: {msg}")
                    else:
                        st.error(f"Return Denied: {msg}")

                    rerun()
    if not has_orders:
        st.sidebar.write("No active orders available for return.")
        st.session_state.show_return_items = False

if st.session_state.return_messages:
    st.sidebar.markdown("**Return Status:**")
    for msg in st.session_state.return_messages:
        st.sidebar.info(msg)

# ---------------------------------------------------------
# Post-purchase Recommendations (Module 5)
# ---------------------------------------------------------
st.sidebar.markdown("---")
if st.sidebar.button("Recommend based on History"):
    if st.session_state.orders:
        last = st.session_state.orders[-1]
        recs = st.session_state.agent.post_purchase_recommendations(
            last["items"], top_n=3
        )
        # Using markdown for better visibility control
        st.sidebar.markdown("**We think you'll love:**")
        for r in recs:
            st.sidebar.markdown(f"- {r['title']} (**${r['price']}**)")
    else:
        st.sidebar.markdown("**Make a purchase first!**")