# agent.py
import os
import json
import openai
from utils import load_faiss_index, fetch_product_by_id, get_embeddings, topk_products_from_index
import numpy as np

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

        # Load indices if files exist
        self.index_openai = load_faiss_index(index_path_openai) if index_path_openai and os.path.exists(index_path_openai) else None
        self.index_local = load_faiss_index(index_path_local) if index_path_local and os.path.exists(index_path_local) else None

        self.index_map = {
            "openai": self.index_openai,
            "local": self.index_local
        }

        if self.index_map[emb_method] is None:
            raise ValueError(f"No FAISS index found for emb_method='{emb_method}'")

        self.index = self.index_map[emb_method]
        print(f"[ShoppingAgent] Using {emb_method} embeddings with index dim={self.index.d}")

    def retrieve(self, text, k=8):
        emb = get_embeddings([text], model=self.emb_method)[0]
        emb = np.ascontiguousarray(emb, dtype=np.float32)

        if emb.shape[0] != self.index.d:
            raise ValueError(
                f"Embedding dimension {emb.shape[0]} does not match FAISS index dimension {self.index.d}. "
                f"Check emb_method or rebuild index."
            )

        ids, sims = topk_products_from_index(self.index, emb, k=k)
        product_ids = [str(i + 1) for i in ids]
        products = [fetch_product_by_id(pid) for pid in product_ids]
        return products, sims
    def generate_lookbook(self, user_request, retrieved_products, chat_history):
        """
        Build a prompt using retrieved products and call LLM to create:
        - a curated lookbook (list of 4-8 items with explanation for each)
        - styling notes
        - suggested complementary items (post-purchase)
        - short checkout action suggestion
        Return structured JSON.
        """
        # Build the context text from retrieved products
        ctx_items = []
        for p in retrieved_products:
            if p is None:
                continue
            ctx_items.append(f"- {p['title']}. Price: ${p['price']}. Category: {p['category']}. Attributes: {p['attributes']}")

        system = (
            "You are an expert personal shopper assistant. Given the user's request and a small catalog of products, "
            "return a JSON object with keys: lookbook, styling_notes, complementary_items, checkout_instructions. "
            "Each lookbook item must reference a product id and include a short reason and matching occasion."
        )

        user_prompt = (
            f"User request: {user_request}\n\n"
            f"Catalog snippets:\n" + "\n".join(ctx_items) + "\n\n"
            f"Conversation history (most recent 5 messages):\n" + "\n".join(chat_history[-10:]) + "\n\n"
            "Return only JSON parsable output."
        )

        # Call LLM
        if OPENAI_API_KEY:
            resp = openai.ChatCompletion.create(
                model="gpt-4o-mini",  # choose a chat model available; replace if not available
                messages=[
                    {"role":"system","content":system},
                    {"role":"user","content":user_prompt}
                ],
                max_tokens=450,
                temperature=0.25
            )
            content = resp["choices"][0]["message"]["content"]
        else:
            # Minimal fallback: build a basic JSON from first 4 items
            items = []
            for p in retrieved_products[:4]:
                if p:
                    items.append({
                        "product_id": p["id"],
                        "title": p["title"],
                        "reason": "Well matched to the user's requested style and occasion.",
                        "price": p["price"]
                    })
            out = {
                "lookbook": items,
                "styling_notes": "Mix textures and pick neutral shoes. Consider a lightweight coat for chilly evenings.",
                "complementary_items": [{"title": "Travel steamer", "reason": "Keep garments crease-free"}],
                "checkout_instructions": "Add items to cart and proceed to checkout."
            }
            content = json.dumps(out)

        # ensure valid JSON
        try:
            parsed = json.loads(content)
        except Exception:
            # attempt to salvage by finding first `{` and last `}`
            start = content.find("{")
            end = content.rfind("}")
            parsed = {}
            if start != -1 and end != -1:
                try:
                    parsed = json.loads(content[start:end+1])
                except:
                    parsed = {
                        "lookbook": [],
                        "styling_notes": content[:500],
                        "complementary_items": [],
                        "checkout_instructions": ""
                    }
        return parsed

    # Simple post-purchase recommender: recommend complementary items based on purchased categories
    def post_purchase_recommendations(self, purchased_items, top_n=3):
        cats = {}
        for it in purchased_items:
            cats[it.get("category","other")] = cats.get(it.get("category","other"),0)+1
        # choose top category
        top_cat = sorted(cats.items(), key=lambda x:-x[1])[0][0] if cats else None
        if not top_cat:
            return []
        # ask retrieve for "complementary to {top_cat}"
        q = f"complementary items for {top_cat}"
        recs, _ = self.retrieve(q, k=8)
        return [r for r in recs if r][:top_n]
