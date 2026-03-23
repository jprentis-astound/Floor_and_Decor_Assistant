"""
Step 3: Analyze the scraped tile product data and print a summary report.
"""

import json
from collections import Counter

INPUT_FILE = "tile_products.json"

with open(INPUT_FILE, "r", encoding="utf-8") as f:
    products = json.load(f)

print(f"=" * 70)
print(f"FLOOR & DECOR TILE DATA - SCRAPING REPORT")
print(f"=" * 70)

print(f"\nTotal products scraped: {len(products)}")

# Products with data
has_name = sum(1 for p in products if p.get("name"))
has_desc = sum(1 for p in products if p.get("description"))
has_brand = sum(1 for p in products if p.get("brand"))
has_image = sum(1 for p in products if p.get("image_url"))
has_price = sum(1 for p in products if p.get("price_per_sqft"))
has_reviews = sum(1 for p in products if p.get("review_count", 0) > 0)

print(f"\n--- Data Completeness ---")
print(f"  Name:         {has_name:>5} / {len(products)} ({has_name/len(products)*100:.1f}%)")
print(f"  Description:  {has_desc:>5} / {len(products)} ({has_desc/len(products)*100:.1f}%)")
print(f"  Brand:        {has_brand:>5} / {len(products)} ({has_brand/len(products)*100:.1f}%)")
print(f"  Image URL:    {has_image:>5} / {len(products)} ({has_image/len(products)*100:.1f}%)")
print(f"  Price/sqft:   {has_price:>5} / {len(products)} ({has_price/len(products)*100:.1f}%)")
print(f"  Has Reviews:  {has_reviews:>5} / {len(products)} ({has_reviews/len(products)*100:.1f}%)")

# Product types breakdown
types = Counter(p.get("product_type", "unknown") for p in products)
print(f"\n--- Product Types ---")
for t, count in types.most_common():
    print(f"  {t:30s} {count:>5}")

# Brand breakdown
brands = Counter(p.get("brand", "Unknown") for p in products if p.get("brand"))
print(f"\n--- Top 20 Brands ---")
for b, count in brands.most_common(20):
    print(f"  {b:30s} {count:>5}")

# Price ranges
prices = [float(p["price_per_sqft"].replace("$", "")) for p in products
          if p.get("price_per_sqft") and p["price_per_sqft"] != "N/A"]
if prices:
    print(f"\n--- Price per Sq Ft ---")
    print(f"  Min:    ${min(prices):.2f}")
    print(f"  Max:    ${max(prices):.2f}")
    print(f"  Avg:    ${sum(prices)/len(prices):.2f}")
    print(f"  Median: ${sorted(prices)[len(prices)//2]:.2f}")

    # Price distribution
    brackets = [(0, 2), (2, 4), (4, 6), (6, 10), (10, 20), (20, 50), (50, 1000)]
    print(f"\n  Price Distribution:")
    for lo, hi in brackets:
        count = sum(1 for p in prices if lo <= p < hi)
        bar = "#" * (count // 5)
        print(f"    ${lo:>3} - ${hi:<4}  {count:>5}  {bar}")

# Review stats
rated = [p for p in products if p.get("avg_rating") and p["avg_rating"] > 0]
if rated:
    print(f"\n--- Reviews ---")
    print(f"  Products with ratings: {len(rated)}")
    avg_rating = sum(p["avg_rating"] for p in rated) / len(rated)
    print(f"  Average rating: {avg_rating:.2f}")
    total_reviews = sum(p.get("review_count", 0) for p in products)
    print(f"  Total reviews across all products: {total_reviews}")

# File size
import os
file_size = os.path.getsize(INPUT_FILE)
print(f"\n--- Output ---")
print(f"  File: {INPUT_FILE}")
print(f"  Size: {file_size / 1024:.1f} KB ({file_size / 1024 / 1024:.2f} MB)")
print(f"\n{'=' * 70}")
