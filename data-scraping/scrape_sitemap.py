"""
Step 1: Fetch the Floor & Decor product sitemap and extract product URLs/IDs.
Filters for tile-related products.
"""

import requests
import json
import re
from lxml import etree

SITEMAP_URL = "https://www.flooranddecor.com/sitemap-PDP.xml"
OUTPUT_FILE = "tile_product_ids.json"

# Tile-related URL patterns to filter for
TILE_PATTERNS = [
    r"/tile/",
    r"/porcelain-tile",
    r"/ceramic-tile",
    r"/mosaic-tile",
    r"/glass-tile",
    r"/marble-tile",
    r"/stone-tile",
    r"/subway-tile",
    r"/floor-tile",
    r"/wall-tile",
    r"/outdoor-tile",
    r"/decorative-tile",
]


def extract_product_id(url: str) -> str | None:
    """Extract the numeric product ID from a URL like:
    .../porcelain-tile-101174019.html -> 101174019
    """
    match = re.search(r"-(\d{6,})\.html", url)
    return match.group(1) if match else None


def fetch_sitemap():
    print(f"Fetching sitemap from {SITEMAP_URL}...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    resp = requests.get(SITEMAP_URL, headers=headers, timeout=60)
    resp.raise_for_status()
    print(f"Sitemap fetched: {len(resp.content)} bytes")
    return resp.content


def parse_sitemap(xml_content: bytes) -> list[dict]:
    """Parse sitemap XML and extract all product URLs."""
    root = etree.fromstring(xml_content)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}

    products = []
    for url_elem in root.findall(".//sm:url", ns):
        loc = url_elem.find("sm:loc", ns)
        if loc is not None and loc.text:
            product_id = extract_product_id(loc.text)
            if product_id:
                products.append({
                    "url": loc.text,
                    "product_id": product_id,
                })
    return products


def filter_tile_products(products: list[dict]) -> list[dict]:
    """Filter for tile-related products based on URL patterns."""
    tile_products = []
    pattern = re.compile("|".join(TILE_PATTERNS), re.IGNORECASE)
    for p in products:
        if pattern.search(p["url"]):
            tile_products.append(p)
    return tile_products


def main():
    xml_content = fetch_sitemap()
    all_products = parse_sitemap(xml_content)
    print(f"Total products in sitemap: {len(all_products)}")

    tile_products = filter_tile_products(all_products)
    print(f"Tile products found: {len(tile_products)}")

    # Save to JSON
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(tile_products, f, indent=2)
    print(f"Saved {len(tile_products)} tile product IDs to {OUTPUT_FILE}")

    # Print a sample
    print("\nSample tile products:")
    for p in tile_products[:10]:
        print(f"  ID: {p['product_id']}  URL: {p['url']}")


if __name__ == "__main__":
    main()
