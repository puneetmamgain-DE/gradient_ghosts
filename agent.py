import os
import json
import re
import openai
import numpy as np
from utils import load_faiss_index, fetch_product_by_id, get_embeddings, topk_products_from_index, GoogleReviewService

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
        self.name = "Kai"

    def _detect_sentiment(self, text):
        negatives = ["angry", "bad", "hate", "wrong", "broken", "terrible", "return", "stupid"]
        if any(w in text.lower() for w in negatives):
            return "negative"
        return "neutral"

    def analyze_skin_tone(self, image_base64):
        """
        Uses OpenAI Vision to detect skin tone and return a color profile.
        """
        if not OPENAI_API_KEY or not image_base64:
            return None

        try:
            response = openai.ChatCompletion.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "Analyze the skin tone in this image. 1. Identify the skin tone (e.g., Fair, Olive, Deep) and Undertone (Cool, Warm). 2. Suggest 3 specific color palettes that suit this person best for clothing. Output a short, concise summary string."},
                            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}}
                        ]
                    }
                ],
                max_tokens=150
            )
            analysis = response.choices[0].message.content
            return analysis
        except Exception as e:
            print(f"Vision API Error: {e}")
            return None

    def retrieve(self, text, k=8):
        if not self.index:
            return [], []

        emb = get_embeddings([text], model=self.emb_method)[0]
        emb = np.ascontiguousarray(emb, dtype=np.float32)

        ids, sims = topk_products_from_index(self.index, emb, k=k)

        products = []
        for pid in ids:
            p = fetch_product_by_id(str(pid + 1))
            if p: products.append(p)

        return products, sims

    def generate_lookbook(self, user_request, retrieved_products, chat_history=[], raw_input="", skin_analysis_result=None):
        """
        Generates lookbook. Now includes External Review Scanning and Skin Tone Analysis.
        """
        sentiment = self._detect_sentiment(user_request)

        # Budget Logic
        budget_limit = None
        numbers = re.findall(r'\d+', raw_input)
        if numbers:
            potential_budgets = [int(n) for n in numbers if int(n) > 20]
            if potential_budgets:
                budget_limit = max(potential_budgets)
                retrieved_products = [p for p in retrieved_products if p['price'] <= budget_limit]

        # ---------------------------------------------------------
        # NEW LOGIC: Augment products with External Google Reviews
        # ---------------------------------------------------------
        # We only check the top 5 filtered products to save API calls/latency
        for p in retrieved_products[:5]:
            review_data = GoogleReviewService.fetch_rating(p['title'])
            p['ext_rating'] = review_data['rating']
            p['ext_source'] = review_data['source']

        # Serialize product context with RATINGS
        ctx_items = []
        for p in retrieved_products:
            rating_info = f" | Ext Rating: {p.get('ext_rating', 'N/A')}/5 ({p.get('ext_source','N/A')})"
            ctx_items.append(f"- ID:{p['id']} | {p['title']} | ${p['price']} | {p['category']}{rating_info}")

        history_context = ""
        if chat_history:
            for role, text in chat_history[-6:]:
                history_context += f"{role.capitalize()}: {text}\n"

        # Construct System Prompt with Skin Tone Awareness
        skin_instruction = ""
        if skin_analysis_result:
            skin_instruction = (
                f"\n**SKIN TONE ANALYSIS PROVIDED:** {skin_analysis_result}\n"
                "   - Prioritize items from the inventory that match the suggested color palettes.\n"
                "   - Explicitly mention in the 'reason' field if a color suits their skin tone (e.g., 'This Earthy Green matches your Warm Olive tone').\n"
            )

        system_prompt = (
            f"You are {self.name}, an intelligent shopping assistant for 'Vestra'.\n"
            "**YOUR MODE: SLOT FILLING & BEST-FIT ANALYSIS**\n"
            "1. Gather slots: Item Type, Style, Budget, Occasion.\n"
            "2. Once slots are filled, recommend products.\n"
            "3. **CRITICAL:** Use the 'Ext Rating' provided in the inventory to highlight the best-fit items.\n"
            "   - If an item has a high external rating (4.5+), mention it as 'highly rated online' or 'customer favorite'.\n"
            f"{skin_instruction}"
            "4. **USP: Intent-Locked Pricing™**\n"
            "   - Remind the user that adding items to the cart LOCKS the price today."
            "   - If the price drops in the next 30 days, they get an auto-refund."
            "5. Return valid JSON."
        )

        user_prompt = (
            f"Chat History:\n{history_context}\n"
            f"Current User Input: {user_request}\n"
            f"Inventory (with External Ratings):\n" + "\n".join(ctx_items) + "\n\n"
            "Task: Determine if you have enough info. If yes, return lookbook with top rated items prioritized."
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
                    max_tokens=600
                )
                content = resp["choices"][0]["message"]["content"]
                if content.startswith("```json"):
                    content = content.replace("```json", "").replace("```", "")
                return json.loads(content)
            except Exception as e:
                print(f"LLM Error: {e}")

        # Fallback Logic (Autonomous)
        fallback_msg = f"I've found some great items for you! Plus, your price is locked the moment you decide."
        items = []
        full_context = (history_context + " " + raw_input).lower()

        has_item = any(w in full_context for w in ["dress", "shoe", "shirt", "pant", "jacket"])
        has_budget = any(c in full_context for c in ["$", "dollar", "budget", "under", "price"])
        has_style_occ = any(w in full_context for w in ["formal", "casual", "wedding", "party", "office"])

        if sentiment == "negative":
            fallback_msg = f"I'm sorry. I can process a return immediately."
            items = []
        elif not has_item:
            fallback_msg = "What kind of item are you looking for?"
        elif not has_budget and not has_style_occ:
            fallback_msg = "What style and budget do you have in mind?"
        elif not has_style_occ:
            fallback_msg = "What occasion is this for?"
        elif not has_budget:
            fallback_msg = "Do you have a price range?"
        else:
            fallback_msg = "Here are my top recommendations based on internal matches and external web reviews. Prices are locked!"
            # Sort by external rating if available in fallback mode
            sorted_prods = sorted(retrieved_products, key=lambda x: x.get('ext_rating', 0), reverse=True)
            for p in sorted_prods[:4]:
                items.append({
                    "product_id": p["id"],
                    "reason": f"Rated {p.get('ext_rating', 'N/A')}/5 online."
                })

        return {
            "chat_response": fallback_msg,
            "lookbook": items
        }

    def post_purchase_recommendations(self, purchased_items, top_n=3):
        if not purchased_items: return []
        cats = " ".join([i['category'] for i in purchased_items])
        query = f"Accessories matching {cats}"
        recs, _ = self.retrieve(query, k=top_n + 2)
        purchased_ids = [str(i['id']) for i in purchased_items]
        final = [r for r in recs if str(r['id']) not in purchased_ids][:top_n]
        return final