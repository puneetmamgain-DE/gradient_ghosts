# sample_data/generate_products.py
import csv
import os
import time
import requests
from random import choice, uniform, randint
from urllib.parse import quote_plus
import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

OUT = "sample_data"
os.makedirs(OUT, exist_ok=True)
F = os.path.join(OUT, "products.csv")

categories = {
    "Women's Dresses": ["maxi dress", "cocktail dress", "wrap dress", "midi dress"],
    "Men's Suits": ["two-piece suit", "blazer", "tuxedo", "morning coat"],
    "Outerwear": ["wool coat", "pea coat", "trench coat", "puffer jacket"],
    "Accessories": ["clutch", "leather belt", "silk scarf", "statement necklace"],
    "Shoes": ["heels", "oxfords", "loafers", "boots"]
}

colors = ["navy", "black", "ivory", "emerald", "burgundy", "charcoal", "tan", "blush", "pink"]
materials = ["wool", "silk", "cotton", "linen", "polyester blend", "suede", "leather"]

# Pexels API settings
PEXELS_API_KEY = os.environ.get("PEXELS_API_KEY")
if not PEXELS_API_KEY:
    logging.error("Environment variable PEXELS_API_KEY not set. Please export your Pexels API key and rerun.")
    logging.error("Example (Linux/macOS): export PEXELS_API_KEY='your_key_here'")
    sys.exit(1)

PEXELS_API_BASE = "https://api.pexels.com/v1"
SEARCH_ENDPOINT = f"{PEXELS_API_BASE}/search"
CURATED_ENDPOINT = f"{PEXELS_API_BASE}/curated"
HEADERS = {"Authorization": PEXELS_API_KEY}

# helper: choose best src url from a photo object
def choose_best_src(photo):
    # Pexels provides multiple sizes in photo['src']
    src = photo.get("src", {})
    # prefer higher quality sizes, fallback down
    for key in ("original", "large2x", "large", "medium", "small"):
        if key in src and src[key]:
            return src[key]
    return src.get("original") or photo.get("url") or None

def pexels_search_image_url(query, per_page=3, sleep_between=0.2):
    """
    Search Pexels for 'query' and return the best image URL.
    If no results, falls back to curated photos endpoint (first photo).
    Returns None on error.
    """
    q = str(query).strip()
    params = {"query": q, "per_page": per_page, "page": 1}
    try:
        resp = requests.get(SEARCH_ENDPOINT, headers=HEADERS, params=params, timeout=10)
    except requests.RequestException as e:
        logging.warning("Request error for query '%s': %s", q, e)
        return None

    if resp.status_code == 200:
        data = resp.json()
        photos = data.get("photos", [])
        if photos:
            # pick a random photo from the top results for variety, but you can choose index 0 for determinism
            photo = choice(photos)
            url = choose_best_src(photo)
            if url:
                time.sleep(sleep_between)
                return url
            else:
                logging.debug("No src found in selected photo for query '%s'", q)
        else:
            logging.debug("No search results for '%s' (status 200). Trying curated fallback.", q)
    else:
        # handle common errors (401 unauthorized, 429 rate limit, etc.)
        logging.warning("Pexels API returned %s for query '%s': %s", resp.status_code, q, resp.text)
        # If unauthorized (401), it's likely the API key is wrong/expired
        if resp.status_code == 401:
            logging.error("Unauthorized: check your PEXELS_API_KEY. Pexels expects the key directly in the Authorization header.")
        return None

    # fallback: try curated photos endpoint and pick first
    try:
        resp2 = requests.get(CURATED_ENDPOINT, headers=HEADERS, params={"per_page": 1, "page": 1}, timeout=10)
    except requests.RequestException as e:
        logging.warning("Curated request error: %s", e)
        return None

    if resp2.status_code == 200:
        data2 = resp2.json()
        photos2 = data2.get("photos", [])
        if photos2:
            photo = photos2[0]
            url = choose_best_src(photo)
            time.sleep(sleep_between)
            return url
    else:
        logging.warning("Pexels curated endpoint returned %s: %s", resp2.status_code, resp2.text)

    return None

rows = []
id_counter = 1
total_per_category = 50  # configurable

for cat, templates in categories.items():
    for i in range(total_per_category):
        template = choice(templates)
        color = choice(colors)
        mat = choice(materials)
        title = f"{color.title()} {template.title()} ({mat})"
        desc = (f"A {color} {template} made from {mat}. Versatile, elegant, "
                "and suitable for semi-formal events. Lightweight, breathable, and tailored fit.")
        price = round(uniform(39.99, 499.99), 2)

        # Build a focused query for Pexels
        img_q = f"{cat} {template} {color}"
        # get image URL from Pexels API
        img_url = pexels_search_image_url(img_q)
        if not img_url:
            # If Pexels search failed, create a conservative placeholder (still Pexels domain if possible),
            # but prefer None to indicate no image.
            logging.warning("Could not fetch Pexels image for '%s' — leaving image_url blank for id %d.", img_q, id_counter)
            img_url = ""

        attrs = {"color": color, "material": mat, "occasion": "semi-formal" if "dress" in template or "suit" in template else "casual"}
        rows.append({
            "id": str(id_counter),
            "title": title,
            "category": cat,
            "description": desc,
            "price": price,
            "image_url": img_url,
            "attributes": str(attrs)
        })
        id_counter += 1

# write CSV
with open(F, "w", newline="", encoding="utf-8") as fh:
    writer = csv.DictWriter(fh, fieldnames=["id","title","category","description","price","image_url","attributes"])
    writer.writeheader()
    for r in rows:
        writer.writerow(r)

print(f"Wrote {len(rows)} products to {F}")
