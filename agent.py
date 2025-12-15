import os
import json
import re
import openai
import numpy as np
from utils import load_faiss_index, fetch_product_by_id, get_embeddings, topk_products_from_index

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY


class ShoppingAgent:
    def __init__(self, index_path_openai="product_index_openai.faiss",
                 index_path_local="product_index_local.faiss",
                 emb_method="openai"):
        self.emb_method = emb_method
        self.index_openai = load_faiss_index(index_path_openai)
        self.index_local = load_faiss_index(index_path_local)

        self.index = self.index_openai if emb_method == "openai" else self.index_local
        # Module 4: Agent Identity "Kai"
        self.name = "Kai"

        # -------------------------------------------------

    # Module 2: Sentiment-Based Triage
    # -------------------------------------------------
    def _detect_sentiment(self, text):
        negatives = ["angry", "bad", "hate", "wrong", "broken", "terrible", "return", "stupid"]
        if any(w in text.lower() for w in negatives):
            return "negative"
        return "neutral"

    # -------------------------------------------------
    # Retrieval Logic
    # -------------------------------------------------
    def retrieve(self, text, k=8):
        if not self.index:
            return [], []  # Safety if index not built

        emb = get_embeddings([text], model=self.emb_method)[0]
        emb = np.ascontiguousarray(emb, dtype=np.float32)

        ids, sims = topk_products_from_index(self.index, emb, k=k)

        products = []
        for pid in ids:
            # Assuming IDs in FAISS are 0-indexed, CSV is 1-indexed usually
            p = fetch_product_by_id(str(pid + 1))
            if p: products.append(p)

        return products, sims

    # -------------------------------------------------
    # Module 2, 4, 5: Lookbook & Chat Generation
    # Multi-Turn Dialogue Capability Added
    # -------------------------------------------------
    def generate_lookbook(self, user_request, retrieved_products, chat_history=[], raw_input=""):
        """
        Generates structured JSON response including a chat message from 'Kai'.
        Uses raw_input to detect vagueness correctly.
        """
        sentiment = self._detect_sentiment(user_request)

        # --- NEW: Budget Extraction Logic ---
        # Look for numbers in the input (e.g., "200", "$150", "under 300")
        budget_limit = None
        numbers = re.findall(r'\d+', raw_input)
        if numbers:
            # Take the largest number found that is reasonable for a price (>20)
            potential_budgets = [int(n) for n in numbers if int(n) > 20]
            if potential_budgets:
                budget_limit = max(potential_budgets)
                # Apply Filter: Keep only items <= budget_limit
                retrieved_products = [p for p in retrieved_products if p['price'] <= budget_limit]

        # Serialize product context
        ctx_items = []
        for p in retrieved_products:
            ctx_items.append(f"- ID:{p['id']} | {p['title']} | ${p['price']} | {p['category']} | {p['attributes']}")

        # Prepare Chat History for context
        history_context = ""
        if chat_history:
            for role, text in chat_history[-6:]:  # More history for context
                history_context += f"{role.capitalize()}: {text}\n"

        # Module 4: System Prompt with Persona "Kai"
        # UPDATED: Explicit "Slot Filling" Instructions to match user example
        system_prompt = (
            f"You are {self.name}, a futuristic, empathetic, and intelligent shopping assistant for 'Vestra'.\n"
            "**YOUR MODE: SLOT FILLING**\n"
            "You must NOT recommend products until you have gathered specific details from the user.\n"
            "**Required Details (Slots):**\n"
            "1. Item Type (e.g., Dress, Shoes)\n"
            "2. Style (e.g., A-line, Maxi, Sneaker)\n"
            "3. Budget (e.g., Under $150)\n"
            "4. Occasion/Fabric/Color (e.g., Wedding, Silk, Blue)\n\n"
            "**Conversation Flow Rules:**\n"
            "- IF the user just says 'I need a dress', ASK: 'Great! What style are you thinking of? What's your budget?'\n"
            "- IF the user gives Style/Budget, ASK: 'Okay. Do you prefer specific colors/fabrics? What occasion is this for?'\n"
            "- IF you have enough details (3+ slots filled), ONLY THEN return the 'lookbook' with items.\n"
            "- OTHERWISE, return an EMPTY 'lookbook' [] and ask the next follow-up question.\n"
            "- Handle negative sentiment with empathy and offer returns.\n"
            "- Output ONLY valid JSON."
        )

        user_prompt = (
                f"Chat History:\n{history_context}\n"
                f"Current User Input: {user_request}\n"
                f"Sentiment Detected: {sentiment}\n"
                f"Available Inventory (Filtered): \n" + "\n".join(ctx_items) + "\n\n"
                                                                               "Task: Determine if you have enough info (Style, Budget, Occasion). If missing, ask. If complete, recommend."
                                                                               "Return JSON format: { 'chat_response': 'string', 'lookbook': [ {'product_id': id, 'reason': 'short reason'} ] }"
        )

        if OPENAI_API_KEY:
            try:
                resp = openai.ChatCompletion.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.3,
                    max_tokens=500
                )
                content = resp["choices"][0]["message"]["content"]
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "")
                return json.loads(content)
            except Exception as e:
                print(f"LLM Error: {e}")
                # Fallback below

        # Fallback Logic (Autonomous / No LLM)
        fallback_msg = f"I've found some great items for you, {self.name} here!"
        items = []

        # Check combined history for slots (Heuristic)
        full_context = (history_context + " " + raw_input).lower()

        has_item = any(w in full_context for w in ["dress", "shoe", "shirt", "pant", "jacket"])
        has_budget = any(c in full_context for c in ["$", "dollar", "budget", "under", "price"])
        has_style_occ = any(
            w in full_context for w in ["formal", "casual", "wedding", "party", "office", "summer", "winter"])

        if sentiment == "negative":
            fallback_msg = f"I'm sorry to hear that. As {self.name}, I can process an instant return for you right now."
            items = []
        elif not has_item:
            fallback_msg = "I can certainly help! What kind of item are you looking for today?"
            items = []
        elif not has_budget and not has_style_occ:
            fallback_msg = f"Great choice! To narrow it down, what style are you thinking of? And do you have a budget range?"
            items = []  # Trigger follow-up
        elif not has_style_occ:
            fallback_msg = "Noted. What occasion is this for? Or do you have a specific color in mind?"
            items = []  # Trigger follow-up
        elif not has_budget:
            fallback_msg = "Almost there! Do you have a price range or budget I should stick to?"
            items = []  # Trigger follow-up
        else:
            # All slots filled (or close enough)
            fallback_msg = "Perfect! Based on those details, here are my top recommendations."
            for p in retrieved_products[:4]:
                items.append({
                    "product_id": p["id"],
                    "reason": "Matches your criteria."
                })

        return {
            "chat_response": fallback_msg,
            "lookbook": items
        }

    # -------------------------------------------------
    # Module 2: Post-Purchase / Bundle Recommendations
    # -------------------------------------------------
    def post_purchase_recommendations(self, purchased_items, top_n=3):
        if not purchased_items: return []
        cats = " ".join([i['category'] for i in purchased_items])
        query = f"Accessories matching {cats}"
        recs, _ = self.retrieve(query, k=top_n + 2)
        purchased_ids = [str(i['id']) for i in purchased_items]
        final = [r for r in recs if str(r['id']) not in purchased_ids][:top_n]
        return final