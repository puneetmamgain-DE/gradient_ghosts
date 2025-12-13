# utils.py
import os
import json
import numpy as np
import pandas as pd
import faiss
import openai


# -------------------------------------------------
# Load products from CSV (single source of truth)
# -------------------------------------------------
def load_products(csv_path="sample_data/products.csv"):
    return pd.read_csv(csv_path)


# -------------------------------------------------
# Fetch product by ID (CSV-based, no DB)
# -------------------------------------------------
def fetch_product_by_id(product_id, csv_path="sample_data/products.csv"):
    df = load_products(csv_path)
    row = df[df["id"] == int(product_id)]

    if row.empty:
        return None

    row = row.iloc[0]
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "category": row["category"],
        "description": row["description"],
        "price": float(row["price"]),
        "image_url": row["image_url"],
        "attributes": row["attributes"]
    }


# -------------------------------------------------
# Embeddings
# -------------------------------------------------
def get_embeddings(texts, model="openai"):
    """
    Returns embeddings for list of texts.
    - OpenAI: 1536-d
    - Local (sentence-transformers): 384-d
    """
    api_key = os.getenv("OPENAI_API_KEY")

    if model == "openai" and api_key:
        openai.api_key = api_key
        resp = openai.Embedding.create(
            model="text-embedding-3-small",
            input=texts
        )
        embs = [r["embedding"] for r in resp["data"]]

    elif model == "local":
        try:
            from sentence_transformers import SentenceTransformer
            embedder = SentenceTransformer("all-MiniLM-L6-v2")
            embs = embedder.encode(
                texts,
                show_progress_bar=False,
                convert_to_numpy=True
            )
        except ImportError:
            embs = [np.random.rand(384) for _ in texts]

    else:
        embs = [np.random.rand(1536) for _ in texts]

    embs = np.array(embs, dtype=np.float32)
    return np.ascontiguousarray(embs)


# -------------------------------------------------
# FAISS helpers
# -------------------------------------------------
def load_faiss_index(index_path):
    return faiss.read_index(index_path)


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
