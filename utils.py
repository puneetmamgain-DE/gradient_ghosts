import os
import json
import numpy as np
import pandas as pd
import faiss
import openai
from datetime import datetime, timedelta  # Added for Return Policy


# -------------------------------------------------
# Module 8: Shipping & Return Policy Logic
# -------------------------------------------------
class PolicyManager:
    """
    Handles Shipping logic and Return Eligibility.
    """
    SHIPPING_OPTIONS = {
        "Standard": {"cost": 0, "days": "5-7 Business Days"},
        "Express": {"cost": 15.00, "days": "2-3 Business Days"},
        "Overnight": {"cost": 25.00, "days": "1 Business Day"}
    }

    @staticmethod
    def get_shipping_cost(method):
        return PolicyManager.SHIPPING_OPTIONS.get(method, {}).get("cost", 0)

    @staticmethod
    def check_return_eligibility(purchase_date):
        """
        Checks if the order is within the 15-day return window.
        Input: purchase_date (datetime.date object)
        Returns: (bool, message)
        """
        if not purchase_date:
            return False, "Date not found."

        today = datetime.now().date()
        delta = today - purchase_date

        if delta.days <= 15:
            return True, f"Eligible ({delta.days} days since purchase)"
        else:
            return False, f"Ineligible ({delta.days} days since purchase. Policy: 15 days)"


# -------------------------------------------------
# Module 6: Sizes as per Location Enabled
# -------------------------------------------------
class SizeConverter:
    """
    Handles autonomous size conversion based on user region.
    """
    SIZE_MAP = {
        "US": {"XS": "0-2", "S": "4-6", "M": "8-10", "L": "12-14", "XL": "16+"},
        "EU": {"XS": "32-34", "S": "36-38", "M": "40-42", "L": "44-46", "XL": "48+"},
        "UK": {"XS": "4-6", "S": "8-10", "M": "12-14", "L": "16-18", "XL": "20+"},
        "JP": {"XS": "5-7", "S": "9", "M": "11", "L": "13", "XL": "15"},
    }

    @staticmethod
    def convert(size_key, region="US"):
        """Converts a generic size (e.g., 'M') to local standard."""
        region_map = SizeConverter.SIZE_MAP.get(region, SizeConverter.SIZE_MAP["US"])
        local_size = region_map.get(size_key, size_key)
        return f"{region} {local_size} ({size_key})"


# -------------------------------------------------
# Module 7: Customer Rewards Logic
# -------------------------------------------------
class RewardSystem:
    """
    AI-managed loyalty system logic.
    """

    @staticmethod
    def calculate_points(action_type, amount=0):
        """
        Calculates points.
        For purchases, points = total dollar amount (1 point per $1).
        """
        if action_type == "purchase":
            return int(amount)  # Dynamic: 1 point per dollar spent

        rewards = {
            "review": 50,  # The "Review Bounty"
            "share": 25,  # The "Influencer" Dividend
            "ar_try_on": 10,  # Gamification engagement
            "eco_choice": 15  # Green Streaks
        }
        return rewards.get(action_type, 0)


# -------------------------------------------------
# Load products from CSV (single source of truth)
# -------------------------------------------------
def load_products(csv_path="sample_data/products.csv"):
    if not os.path.exists(csv_path):
        # Create dummy data if file doesn't exist for immediate testing
        data = {
            "id": [1, 2, 3, 4, 5],
            "title": ["Eco-Hemp Jacket", "Urban Glide Sneakers", "Midnight Gala Dress", "Smart Wool Blazer",
                      "Boho Summer Tunic"],
            "category": ["Men's Fashion", "Footwear", "Women's Fashion", "Men's Fashion", "Women's Fashion"],
            "description": ["Sustainable hemp fiber jacket.", "High-tech running shoes.", "Elegant evening wear.",
                            "Professional office attire.", "Lightweight summer vibe."],
            "price": [120.00, 85.00, 250.00, 180.00, 45.00],
            "image_url": ["", "", "", "", ""],
            "attributes": ["Sustainable", "Sporty", "Formal", "Business", "Casual"]
        }
        return pd.DataFrame(data)
    return pd.read_csv(csv_path)


# -------------------------------------------------
# Fetch product by ID
# -------------------------------------------------
def fetch_product_by_id(product_id, csv_path="sample_data/products.csv"):
    df = load_products(csv_path)
    # Ensure ID comparison handles string/int differences
    try:
        row = df[df["id"].astype(str) == str(product_id)]
    except KeyError:
        return None

    if row.empty:
        return None

    row = row.iloc[0]
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "category": row["category"],
        "description": row["description"],
        "price": float(row["price"]),
        "image_url": row.get("image_url", ""),
        "attributes": row.get("attributes", "")
    }


# -------------------------------------------------
# Embeddings
# -------------------------------------------------
def get_embeddings(texts, model="openai"):
    api_key = os.getenv("OPENAI_API_KEY")

    if model == "openai" and api_key:
        openai.api_key = api_key
        try:
            resp = openai.Embedding.create(
                model="text-embedding-3-small",
                input=texts
            )
            embs = [r["embedding"] for r in resp["data"]]
        except Exception as e:
            print(f"OpenAI Error: {e}, falling back to random.")
            embs = [np.random.rand(1536) for _ in texts]

    elif model == "local":
        try:
            from sentence_transformers import SentenceTransformer
            # Using a lightweight model for local demo
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            embs = embedder.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True
            )
        except ImportError:
            # Fallback if sentence_transformers not installed
            embs = [np.random.rand(384) for _ in texts]

    else:
        # Fallback for no API/Library
        embs = [np.random.rand(1536) for _ in texts]

    embs = np.array(embs, dtype=np.float32)
    return np.ascontiguousarray(embs)


# -------------------------------------------------
# FAISS helpers
# -------------------------------------------------
def load_faiss_index(index_path):
    try:
        return faiss.read_index(index_path)
    except:
        return None


def build_faiss_index(texts, model="openai", save_path="product_index.faiss"):
    embs = get_embeddings(texts, model=model)
    faiss.normalize_L2(embs)

    d = embs.shape[1]
    index = faiss.IndexFlatIP(d)  # cosine similarity
    index.add(embs)

    faiss.write_index(index, save_path)
    print(f"FAISS index saved to {save_path}")
    return index


def topk_products_from_index(index, query_emb, k=6):
    q = np.array(query_emb, dtype=np.float32)
    if q.ndim == 1:
        q = q[np.newaxis, :]

    faiss.normalize_L2(q)
    D, I = index.search(q, k)

    return I[0].tolist(), D[0].tolist()