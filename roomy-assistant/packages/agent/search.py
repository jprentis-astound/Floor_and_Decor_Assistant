"""
SQLite search functions for the tile product database.
Supports full-text search (FTS5) + structured filters.
"""

import json
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "tiles.db")


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _parse_multi_value(value: str) -> list[str]:
    """Parse a filter value that might be a JSON array, comma-separated, or single value.
    e.g. '["white", "gray"]' → ['white', 'gray']
         'white, gray'        → ['white', 'gray']
         'white'              → ['white']
    """
    if not value or not value.strip():
        return []
    v = value.strip()
    # Try JSON array first
    if v.startswith("["):
        try:
            parsed = json.loads(v)
            if isinstance(parsed, list):
                return [str(item).strip() for item in parsed if str(item).strip()]
        except (json.JSONDecodeError, ValueError):
            pass
    # Try comma-separated
    if "," in v:
        return [item.strip() for item in v.split(",") if item.strip()]
    # Single value
    return [v]


def search_tiles(
    query: str = "",
    material: str = "",
    min_price: float | None = None,
    max_price: float | None = None,
    brand: str = "",
    finish: str = "",
    color: str = "",
    size: str = "",
    limit: int = 8,
) -> list[dict]:
    """
    Search tiles with natural language query + structured filters.
    Returns a list of tile dicts with all product fields.
    """
    conn = get_connection()
    cur = conn.cursor()

    conditions = []
    params = []

    # Full-text search via FTS5
    if query.strip():
        # Clean query for FTS5 — remove special chars, wrap each word for prefix matching
        words = [w.strip() for w in query.split() if w.strip()]
        # Filter out FTS5 operators and very short words
        fts_words = [w for w in words if len(w) >= 2 and w.lower() not in (
            "and", "or", "not", "the", "for", "with", "under", "over",
            "less", "more", "than", "per", "sqft", "sq", "ft",
        )]
        if fts_words:
            fts_query = " OR ".join(f'"{w}"' for w in fts_words)
            print(f"[FTS5] words={fts_words} → MATCH query: {fts_query}")
            conditions.append("t.id IN (SELECT id FROM tiles_fts WHERE tiles_fts MATCH ?)")
            params.append(fts_query)

    # Structured filters — each supports multiple values (OR within, AND across)
    materials = _parse_multi_value(material)
    if materials:
        or_clauses = " OR ".join(["LOWER(t.material) LIKE ?"] * len(materials))
        conditions.append(f"({or_clauses})")
        params.extend(f"%{m.lower()}%" for m in materials)

    brands = _parse_multi_value(brand)
    if brands:
        or_clauses = " OR ".join(["LOWER(t.brand) LIKE ?"] * len(brands))
        conditions.append(f"({or_clauses})")
        params.extend(f"%{b.lower()}%" for b in brands)

    finishes = _parse_multi_value(finish)
    if finishes:
        or_clauses = " OR ".join(["LOWER(t.finish) LIKE ?"] * len(finishes))
        conditions.append(f"({or_clauses})")
        params.extend(f"%{f.lower()}%" for f in finishes)

    colors = _parse_multi_value(color)
    if colors:
        or_clauses = " OR ".join(
            ["(LOWER(t.color) LIKE ? OR LOWER(t.name) LIKE ?)"] * len(colors)
        )
        conditions.append(f"({or_clauses})")
        for c in colors:
            params.extend([f"%{c.lower()}%", f"%{c.lower()}%"])

    sizes = _parse_multi_value(size)
    if sizes:
        or_clauses = " OR ".join(["t.size LIKE ?"] * len(sizes))
        conditions.append(f"({or_clauses})")
        params.extend(f"%{s}%" for s in sizes)

    if min_price is not None:
        conditions.append("t.price_sqft >= ?")
        params.append(min_price)

    if max_price is not None:
        conditions.append("t.price_sqft <= ?")
        params.append(max_price)

    # Always require a valid price
    conditions.append("t.price_sqft IS NOT NULL")

    where = " AND ".join(f"({c})" for c in conditions) if conditions else "1=1"

    sql = f"""
        SELECT t.id, t.name, t.brand, t.material, t.finish, t.color, t.size,
               t.price_sqft, t.price_box, t.image_url, t.product_url,
               t.product_type, t.avg_rating, t.review_count, t.description
        FROM tiles t
        WHERE {where}
        ORDER BY t.review_count DESC, t.price_sqft ASC
        LIMIT ?
    """
    params.append(limit)

    print(f"\n[SQL QUERY]")
    print(f"  {sql.strip()}")
    print(f"[SQL PARAMS] {params}")

    cur.execute(sql, params)
    rows = cur.fetchall()
    print(f"[SQL RESULT] {len(rows)} rows returned")
    conn.close()

    results = []
    for row in rows:
        results.append({
            "id": row["id"],
            "name": row["name"],
            "brand": row["brand"],
            "material": row["material"],
            "finish": row["finish"],
            "color": row["color"],
            "size": row["size"],
            "price_sqft": row["price_sqft"],
            "price_box": row["price_box"],
            "image_url": row["image_url"],
            "product_url": row["product_url"],
            "product_type": row["product_type"],
            "avg_rating": row["avg_rating"],
            "review_count": row["review_count"],
            "description": row["description"][:200] if row["description"] else "",
        })
    return results


def get_available_filters() -> dict:
    """Return distinct filter values for the UI."""
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT DISTINCT material FROM tiles WHERE material != '' ORDER BY material")
    materials = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT brand FROM tiles WHERE brand != '' ORDER BY brand")
    brands = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT DISTINCT finish FROM tiles WHERE finish != '' ORDER BY finish")
    finishes = [r[0] for r in cur.fetchall()]

    cur.execute("SELECT MIN(price_sqft), MAX(price_sqft) FROM tiles WHERE price_sqft IS NOT NULL")
    price_range = cur.fetchone()

    conn.close()
    return {
        "materials": materials,
        "brands": brands,
        "finishes": finishes,
        "price_min": price_range[0],
        "price_max": price_range[1],
    }


if __name__ == "__main__":
    # Quick test
    print("=== Search: 'white porcelain matte' ===")
    for t in search_tiles(query="white porcelain matte", limit=5):
        print(f"  {t['name'][:50]:50s} | ${t['price_sqft']:.2f}/sqft | {t['size']} | {t['material']} | {t['finish']}")

    print("\n=== Filter: porcelain under $3/sqft ===")
    for t in search_tiles(material="porcelain", max_price=3.0, limit=5):
        print(f"  {t['name'][:50]:50s} | ${t['price_sqft']:.2f}/sqft | {t['brand']}")

    print("\n=== Filter: glass tile ===")
    for t in search_tiles(material="glass", limit=5):
        print(f"  {t['name'][:50]:50s} | ${t['price_sqft']:.2f}/sqft | {t['size']}")

    print("\n=== Available filters ===")
    filters = get_available_filters()
    print(f"  Materials: {filters['materials']}")
    print(f"  Finishes:  {filters['finishes']}")
    print(f"  Price range: ${filters['price_min']:.2f} - ${filters['price_max']:.2f}")
