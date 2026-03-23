"""
Load scraped tile product data into SQLite with FTS5 for natural language search.
Run once: python db_loader.py
"""

import json
import re
import sqlite3
import os

SCRAPED_DATA = os.path.join(os.path.dirname(__file__), "..", "..", "..", "data-scraping", "tile_products.json")
DB_PATH = os.path.join(os.path.dirname(__file__), "tiles.db")

# ── Attribute extraction helpers ─────────────────────────────────────────────

FINISH_PATTERNS = [
    "polished", "matte", "honed", "glossy", "satin", "textured",
    "lappato", "structured", "tumbled", "brushed", "sandblasted",
    "rectified", "unpolished",
]

COLOR_PATTERNS = [
    "white", "black", "gray", "grey", "beige", "cream", "ivory",
    "brown", "tan", "taupe", "blue", "green", "red", "gold",
    "silver", "charcoal", "espresso", "walnut", "almond", "sand",
    "pearl", "bone", "slate", "navy", "terracotta", "rust",
    "honey", "smoke", "snow", "midnight", "onyx", "marble",
    "bianco", "grigio", "nero", "crema", "noce", "noche",
]


def extract_finish(name: str) -> str:
    name_lower = name.lower()
    for f in FINISH_PATTERNS:
        if f in name_lower:
            return f.capitalize()
    return ""


def extract_color(name: str) -> str:
    name_lower = name.lower()
    for c in COLOR_PATTERNS:
        if c in name_lower:
            return c.capitalize()
    return ""


def extract_size(name: str, description: str) -> str:
    """Extract tile dimensions like '12 x 24' from name or description."""
    text = f"{name} {description}"
    # Match patterns: 12x24, 12 x 24, 12"x24", etc.
    match = re.search(r"(\d{1,3})\s*[xX×]\s*(\d{1,3})", text)
    if match:
        return f"{match.group(1)} x {match.group(2)}"
    return ""


def extract_material(product_type: str) -> str:
    """Normalize material from product_type URL slug."""
    mapping = {
        "porcelain-tile": "Porcelain",
        "ceramic-tile": "Ceramic",
        "glass-tile": "Glass",
        "floor-tile": "Floor Tile",
        "wall-tile": "Wall Tile",
        "stone-tile": "Stone",
        "marble-tile": "Marble",
        "mosaic-tile": "Mosaic",
    }
    return mapping.get(product_type, product_type.replace("-", " ").title())


def parse_price(price_str) -> float | None:
    """Parse '$4.49' or '4.49' to float."""
    if not price_str:
        return None
    if isinstance(price_str, (int, float)):
        return float(price_str)
    cleaned = str(price_str).replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def load_data():
    print(f"Loading data from {SCRAPED_DATA}...")
    with open(SCRAPED_DATA, "r", encoding="utf-8") as f:
        products = json.load(f)
    print(f"Loaded {len(products)} products")
    return products


def create_db(products: list[dict]):
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Main products table
    cur.execute("""
        CREATE TABLE tiles (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            brand TEXT,
            material TEXT,
            finish TEXT,
            color TEXT,
            size TEXT,
            price_sqft REAL,
            price_box REAL,
            image_url TEXT,
            product_url TEXT,
            product_type TEXT,
            avg_rating REAL,
            review_count INTEGER DEFAULT 0,
            category_id TEXT
        )
    """)

    # FTS5 virtual table for full-text search
    cur.execute("""
        CREATE VIRTUAL TABLE tiles_fts USING fts5(
            id UNINDEXED,
            name,
            description,
            brand,
            material,
            finish,
            color,
            size,
            content='tiles',
            content_rowid='rowid'
        )
    """)

    # Insert data
    inserted = 0
    for p in products:
        if not p.get("name"):
            continue

        name = p["name"]
        desc = p.get("description", "")
        material = extract_material(p.get("product_type", ""))
        finish = extract_finish(name)
        color = extract_color(name)
        size = extract_size(name, desc)
        price_sqft = parse_price(p.get("price_per_sqft"))
        price_box = parse_price(p.get("price_per_box"))

        cur.execute("""
            INSERT OR IGNORE INTO tiles
            (id, name, description, brand, material, finish, color, size,
             price_sqft, price_box, image_url, product_url, product_type,
             avg_rating, review_count, category_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["product_id"], name, desc, p.get("brand", ""),
            material, finish, color, size,
            price_sqft, price_box,
            p.get("image_url", ""), p.get("url", ""),
            p.get("product_type", ""), p.get("avg_rating"),
            p.get("review_count", 0), p.get("category_id", ""),
        ))

        # Insert into FTS
        cur.execute("""
            INSERT INTO tiles_fts (id, name, description, brand, material, finish, color, size)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            p["product_id"], name, desc, p.get("brand", ""),
            material, finish, color, size,
        ))

        inserted += 1

    conn.commit()

    # Create indexes for filtered queries
    cur.execute("CREATE INDEX idx_material ON tiles(material)")
    cur.execute("CREATE INDEX idx_brand ON tiles(brand)")
    cur.execute("CREATE INDEX idx_price ON tiles(price_sqft)")
    cur.execute("CREATE INDEX idx_finish ON tiles(finish)")
    cur.execute("CREATE INDEX idx_color ON tiles(color)")
    conn.commit()

    print(f"Inserted {inserted} tiles into {DB_PATH}")

    # Print stats
    cur.execute("SELECT COUNT(*) FROM tiles")
    print(f"Total rows: {cur.fetchone()[0]}")
    cur.execute("SELECT material, COUNT(*) FROM tiles GROUP BY material ORDER BY COUNT(*) DESC")
    print("\nBy material:")
    for row in cur.fetchall():
        print(f"  {row[0]:20s} {row[1]:>5}")
    cur.execute("SELECT COUNT(*) FROM tiles WHERE finish != ''")
    print(f"\nWith finish data: {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM tiles WHERE size != ''")
    print(f"With size data:   {cur.fetchone()[0]}")
    cur.execute("SELECT COUNT(*) FROM tiles WHERE color != ''")
    print(f"With color data:  {cur.fetchone()[0]}")

    conn.close()


if __name__ == "__main__":
    products = load_data()
    create_db(products)
    print(f"\nDatabase ready at {DB_PATH}")
