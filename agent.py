# agent.py
import os
import json
import openai
from utils import load_faiss_index, fetch_product_by_id, get_embeddings, topk_products_from_index
import numpy as np
import hashlib

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if OPENAI_API_KEY:
    openai.api_key = OPENAI_API_KEY


class ShoppingAgent:
    def __init__(self, index_path_openai="product_index_openai.faiss",
                       index_path_local="product_index_local.faiss",
                       meta_db="products_meta.db",
                       emb_method="openai"):
        self.emb_method = emb_method
        self.meta_db = meta_db

        self.index_openai = load_faiss_index(index_path_openai) if index_path_openai and os.path.exists(index_path_openai) else None
        self.index_local = load_faiss_index(index_path_local) if index_path_local and os.path.exists(index_path_local) else None

        self.index_map = {
            "openai": self.index_openai,
            "local": self.index_local
        }

        if self.index_map[emb_method] is None:
            raise ValueError(f"No FAISS index found for emb_method='{emb_method}'")

        self.index = self.index_map[emb_method]
        self.used_lookbooks = set()
        print(f"[ShoppingAgent] Using {emb_method} embeddings with index dim={self.index.d}")

    # -------------------------------------------------
    # Gender intent detection (USER INTENT ONLY)
    # -------------------------------------------------
    def _detect_gender_intent(self, text: str):
        t = text.lower()

        men_aliases = [
            "men", "man", "male", "mens", "men's", "boys", "boy", "gents", "gentlemen"
        ]
        women_aliases = [
            "women", "woman", "female", "womens", "women's", "girls", "girl", "ladies"
        ]

        men_hit = any(a in t for a in men_aliases)
        women_hit = any(a in t for a in women_aliases)

        if men_hit and not women_hit:
            return "men"
        if women_hit and not men_hit:
            return "women"
        return None  # gender not requested

    # -------------------------------------------------
    # HARD gender gate (ABSOLUTE, NO LEAKAGE)
    # -------------------------------------------------
    def _gender_matches(self, product, gender):
        cat = product.get("category", "").lower()
        attrs = json.dumps(product.get("attributes", "")).lower()
        text = f"{cat} {attrs}"

        men_terms = ["men", "man", "male", "mens", "men's", "gents", "boy"]
        women_terms = ["women", "woman", "female", "womens", "women's", "ladies", "girl"]

        # USER ASKED FOR MEN → WOMEN MUST NEVER PASS
        if gender == "men":
            if any(w in text for w in women_terms):
                return False
            return any(m in text for m in men_terms)

        # USER ASKED FOR WOMEN → MEN MUST NEVER PASS
        if gender == "women":
            if any(m in text for m in men_terms):
                return False
            return any(w in text for w in women_terms)

        # NO GENDER INTENT → ALLOW ALL
        return True

    # -------------------------------------------------
    # Retrieval with strict gender enforcement
    # -------------------------------------------------
    def retrieve(self, text, k=8):
        gender_intent = self._detect_gender_intent(text)

        emb = get_embeddings([text], model=self.emb_method)[0]
        emb = np.ascontiguousarray(emb, dtype=np.float32)

        if emb.shape[0] != self.index.d:
            raise ValueError(
                f"Embedding dimension {emb.shape[0]} does not match FAISS index dimension {self.index.d}."
            )

        ids, sims = topk_products_from_index(self.index, emb, k=k * 4)

        products = []
        scores = []

        for pid, score in zip(ids, sims):
            p = fetch_product_by_id(str(pid + 1))
            if not p:
                continue

            if not self._gender_matches(p, gender_intent):
                continue

            products.append(p)
            scores.append(score)

            if len(products) >= k:
                break

        return products, scores

    # -------------------------------------------------
    # Lookbook generation (gender-safe + unique)
    # -------------------------------------------------
    def generate_lookbook(self, user_request, retrieved_products, chat_history):
        gender_intent = self._detect_gender_intent(user_request)

        ctx_items = []
        for p in retrieved_products:
            if not p:
                continue
            if not self._gender_matches(p, gender_intent):
                continue
            ctx_items.append(
                f"- ID:{p['id']} | {p['title']} | ${p['price']} | {p['category']} | {p['attributes']}"
            )

        system = (
            "You are an expert personal shopper assistant. "
            "You MUST ONLY use the provided catalog items. "
            "DO NOT infer gender. DO NOT introduce new products. "
            "Return JSON with keys: lookbook, styling_notes, complementary_items, checkout_instructions."
        )

        user_prompt = (
            f"User request: {user_request}\n\n"
            f"Catalog:\n" + "\n".join(ctx_items) + "\n\n"
            "Return ONLY valid JSON."
        )

        if OPENAI_API_KEY:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=450
            )
            content = resp["choices"][0]["message"]["content"]
        else:
            items = []
            for p in retrieved_products[:4]:
                if p and self._gender_matches(p, gender_intent):
                    items.append({
                        "product_id": p["id"],
                        "title": p["title"],
                        "reason": "Matches requested style and gender intent.",
                        "occasion": "Recommended use",
                        "price": p["price"]
                    })
            content = json.dumps({
                "lookbook": items,
                "styling_notes": "Keep colors consistent and proportions balanced.",
                "complementary_items": [],
                "checkout_instructions": "Proceed to checkout."
            })

        parsed = json.loads(content)

        lb_ids = sorted(str(i.get("product_id")) for i in parsed.get("lookbook", []))
        lb_hash = hashlib.md5("|".join(lb_ids).encode()).hexdigest()

        if lb_hash in self.used_lookbooks:
            parsed["lookbook"] = parsed["lookbook"][::-1]

        self.used_lookbooks.add(lb_hash)
        return parsed

    # -------------------------------------------------
    # Post-purchase recommendations (gender locked)
    # -------------------------------------------------
    def post_purchase_recommendations(self, purchased_items, top_n=3):
        if not purchased_items:
            return []

        gender = self._detect_gender_intent(
            " ".join(i.get("category", "") for i in purchased_items)
        )

        top_cat = purchased_items[0].get("category", "")
        q = f"complementary items for {top_cat}"

        recs, _ = self.retrieve(q, k=8)
        return [r for r in recs if self._gender_matches(r, gender)][:top_n]
