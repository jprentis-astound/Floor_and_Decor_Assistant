"""
Step 2: Fetch product details from Bazaarvoice API and SFCC pricing endpoint.
Reads tile_product_ids.json, fetches data in batches, outputs tile_products.json.
"""

import requests
import json
import time
import re
import sys

INPUT_FILE = "tile_product_ids.json"
OUTPUT_FILE = "tile_products.json"

# Bazaarvoice API (public, no auth)
BV_BASE = "https://api.bazaarvoice.com/data/batch.json"
BV_PASSKEY = "caxdHHRkVz2B19Gp5BaswP6SynHfGhm28CG5XDvVs1Pig"
BV_API_VERSION = "5.5"
BV_DISPLAY_CODE = "10499-en_us"

# SFCC Pricing endpoint (public, no auth)
PRICING_BASE = "https://www.flooranddecor.com/on/demandware.store/Sites-floor-decor-Site/default/DynamicYield-GetProductStorePrices"

# Amplience CDN for images
AMPLIENCE_CDN = "https://i8.amplience.net/i/flooranddecor"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}

# Batch sizes
BV_BATCH_SIZE = 20  # Bazaarvoice supports multiple products per request
PRICING_BATCH_SIZE = 10


def load_product_ids() -> list[dict]:
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def fetch_bazaarvoice_batch(product_ids: list[str]) -> dict:
    """Fetch product data from Bazaarvoice for a batch of product IDs."""
    params = {
        "passkey": BV_PASSKEY,
        "apiversion": BV_API_VERSION,
        "displaycode": BV_DISPLAY_CODE,
        "resource.q0": "products",
        "filter.q0": f"id:eq:{','.join(product_ids)}",
        "stats.q0": "questions,reviews",
        "limit.q0": str(len(product_ids)),
    }

    try:
        resp = requests.get(BV_BASE, params=params, headers=HEADERS, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return data
    except Exception as e:
        print(f"  BV API error: {e}")
        return {}


def parse_bv_product(bv_result: dict) -> dict:
    """Extract useful fields from a Bazaarvoice product result."""
    review_stats = bv_result.get("ReviewStatistics", {})
    qa_stats = bv_result.get("QAStatistics", {})

    image_url = bv_result.get("ImageUrl", "")

    return {
        "name": bv_result.get("Name", ""),
        "description": bv_result.get("Description", ""),
        "brand": bv_result.get("Brand", {}).get("Name", "") if isinstance(bv_result.get("Brand"), dict) else "",
        "category_id": bv_result.get("CategoryId", ""),
        "image_url": image_url,
        "ean": bv_result.get("EAN", ""),
        "upc": bv_result.get("UPC", ""),
        "avg_rating": review_stats.get("AverageOverallRating", 0),
        "review_count": review_stats.get("TotalReviewCount", 0),
        "qa_count": qa_stats.get("TotalQuestionCount", 0),
    }


def fetch_pricing_batch(product_ids: list[str]) -> dict:
    """Fetch pricing from the SFCC DynamicYield endpoint."""
    pids = ",".join(product_ids)
    try:
        resp = requests.get(
            PRICING_BASE,
            params={"pids": pids},
            headers=HEADERS,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        print(f"  Pricing API error: {e}")
        return {}


def build_image_url(product_id: str, product_name: str) -> str:
    """Build the Amplience CDN image URL from product ID and name slug."""
    slug = re.sub(r"[^a-z0-9]+", "_", product_name.lower()).strip("_")
    return f"{AMPLIENCE_CDN}/{product_id}_{slug}_room"


def extract_product_type(url: str) -> str:
    """Extract product type from URL path, e.g. 'porcelain-tile'."""
    match = re.search(r"flooranddecor\.com/([^/]+)/", url)
    return match.group(1) if match else "tile"


def main():
    products_meta = load_product_ids()
    print(f"Loaded {len(products_meta)} tile product IDs")

    # Limit for initial run - process all products but in manageable chunks
    max_products = int(sys.argv[1]) if len(sys.argv) > 1 else len(products_meta)
    products_meta = products_meta[:max_products]
    print(f"Processing {len(products_meta)} products...")

    # Build lookup from ID -> URL
    id_to_url = {p["product_id"]: p["url"] for p in products_meta}
    all_ids = [p["product_id"] for p in products_meta]

    results = []
    total_batches = (len(all_ids) + BV_BATCH_SIZE - 1) // BV_BATCH_SIZE

    for i in range(0, len(all_ids), BV_BATCH_SIZE):
        batch_ids = all_ids[i : i + BV_BATCH_SIZE]
        batch_num = i // BV_BATCH_SIZE + 1
        print(f"\rBatch {batch_num}/{total_batches} - Fetching BV data for {len(batch_ids)} products...", end="", flush=True)

        bv_data = fetch_bazaarvoice_batch(batch_ids)

        # Parse BV results
        bv_results = {}
        if bv_data.get("BatchedResults", {}).get("q0", {}).get("Results"):
            for item in bv_data["BatchedResults"]["q0"]["Results"]:
                pid = item.get("Id", "")
                if pid:
                    bv_results[pid] = parse_bv_product(item)

        # Fetch pricing for this batch
        price_data = fetch_pricing_batch(batch_ids)

        # Combine everything
        for pid in batch_ids:
            product = {
                "product_id": pid,
                "url": id_to_url.get(pid, ""),
                "product_type": extract_product_type(id_to_url.get(pid, "")),
            }

            # Add BV data
            if pid in bv_results:
                product.update(bv_results[pid])
            else:
                product["name"] = ""
                product["description"] = ""
                product["brand"] = ""

            # Add pricing
            if isinstance(price_data, dict) and pid in price_data:
                p = price_data[pid]
                product["price_per_sqft"] = p.get("dy_product_price")
                product["price_per_box"] = p.get("product_price")
                product["refinement_price"] = p.get("product_refinement_price")
            elif isinstance(price_data, list):
                # Sometimes returns a list
                for p in price_data:
                    if isinstance(p, dict) and p.get("id") == pid:
                        product["price_per_sqft"] = p.get("dy_product_price")
                        product["price_per_box"] = p.get("product_price")
                        break

            # Add image URLs
            if product.get("image_url"):
                product["image_url_bv"] = product["image_url"]
            if product.get("name"):
                product["image_url_amplience"] = build_image_url(pid, product["name"])

            results.append(product)

        # Rate limiting - be respectful
        time.sleep(0.5)

    print(f"\n\nTotal products fetched: {len(results)}")

    # Filter out products with no name (BV didn't return data)
    products_with_data = [p for p in results if p.get("name")]
    products_no_data = [p for p in results if not p.get("name")]
    print(f"Products with BV data: {len(products_with_data)}")
    print(f"Products without BV data: {len(products_no_data)}")

    # Save all results
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved all {len(results)} products to {OUTPUT_FILE}")

    # Print sample
    print("\n--- Sample products with data ---")
    for p in products_with_data[:5]:
        print(f"\n  Name: {p['name']}")
        print(f"  Brand: {p['brand']}")
        print(f"  Type: {p['product_type']}")
        print(f"  Rating: {p['avg_rating']} ({p['review_count']} reviews)")
        print(f"  Image: {p.get('image_url', 'N/A')}")
        print(f"  Price/sqft: {p.get('price_per_sqft', 'N/A')}")
        print(f"  URL: {p['url']}")


if __name__ == "__main__":
    main()
