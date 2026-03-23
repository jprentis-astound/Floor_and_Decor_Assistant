# Tile Data Observations

## Catalog Overview

- **Total products scraped**: 1,192 tiles
- **Source**: Floor & Decor public APIs (Bazaarvoice + SFCC pricing + XML Sitemap)
- **Scrape date**: 2026-03
- **Data file**: `data-scraping/tile_products.json` (1.9 MB, 23,841 lines)

---

## Material Breakdown

| Material | Count | % of Catalog |
|----------|-------|-------------|
| Porcelain | 866 | 73% |
| Ceramic | 192 | 16% |
| Glass | 129 | 11% |
| Floor Tile (generic) | 4 | <1% |
| Wall Tile (generic) | 1 | <1% |

Porcelain dominates the catalog by a wide margin. Glass tiles, while fewest in number, tend to have the most visually distinctive product images.

---

## Price Distribution

- **Minimum**: $0.29/sqft (Tender Gray II Wall Tile)
- **Maximum**: $94.99/sqft (luxury/specialty tile)
- **Estimated average**: ~$5.64/sqft
- **Most common range**: $0.50–$3.00/sqft (budget to mid-range)
- **Premium threshold**: $8+/sqft (marble-look, specialty shapes)

Both per-sqft and per-box pricing are available for most products.

---

## Brand Distribution (Top 15)

| Brand | Products |
|-------|----------|
| Vetta Elements | 152 |
| Adessi | 120 |
| San Giorgio | 90 |
| Castille | 86 |
| Maximo | 84 |
| Pianetto | 66 |
| Montage | 60 |
| Villa | 53 |
| Montalcino | 48 |
| Viviano | 45 |
| Moda Del Mar | 44 |
| Floor and Decor | 43 |
| Ashford | 42 |
| Festival | 38 |
| Canvas | 25 |

**41 unique brands total.** Several brands have "with NatureMatch" variants, suggesting a sustainability program.

---

## Finish Extraction Quality

Finishes are extracted via regex from product names, not a dedicated field.

| Finish | Count | Notes |
|--------|-------|-------|
| Matte | 575 | 48% of catalog — most common |
| Polished | 237 | 20% — high-gloss |
| Satin | 14 | Subtle sheen |
| Textured | 4 | Tactile surface |
| Glossy | 3 | High-shine variant |
| Honed | 2 | Smooth but not polished |
| *No finish extracted* | ~357 | ~30% of products lack finish keywords in name |

**Coverage: ~70%** — decent but not complete. Products without finish in their name show an empty field.

---

## Color Extraction Quality

Colors are pattern-matched from product names against 38 predefined color terms.

**Most common extracted colors:**

| Color | Count |
|-------|-------|
| White | 100 |
| Gray | 70 |
| Sand | 32 |
| Bianco | 29 |
| Ivory | 25 |
| Almond | 24 |
| Beige | 23 |
| Blue | 18 |
| Gold | 11 |
| Tan | 10 |

**Coverage: ~50%** — many product names use creative/brand-specific color names (e.g., "Calacatta", "Statuario") that don't match the 38 predefined patterns. The search compensates by also matching color terms against the full product name via `LIKE`.

---

## Size Extraction Quality

Sizes extracted via regex: `(\d{1,3})\s*[xX×]\s*(\d{1,3})`

**Most common sizes:**

| Size (in.) | Count |
|------------|-------|
| 24 x 48 | 175 |
| 12 x 12 | 144 |
| 12 x 24 | 139 |
| 24 x 24 | 77 |
| 15 x 30 | 33 |
| 32 x 32 | 27 |
| 6 x 6 | 23 |
| 48 x 48 | 20 |

**136 unique sizes found** but only ~11% of products have an extractable size. Large format tiles (24x48, 12x24) are the most prevalent, reflecting current design trends.

---

## FTS5 Keyword Effectiveness

Tested common search terms against the full-text index:

| Keyword | Matches | Verdict |
|---------|---------|---------|
| mosaic | 214 | Excellent |
| contemporary | 303 | Excellent |
| modern | 161 | Excellent |
| hexagon | 78 | Good |
| marble | 34 | Good |
| limestone | 66 | Good |
| slate | 35 | Good |
| travertine | 26 | Good |
| penny | 24 | Good |
| brick | 9 | Fair |
| herringbone | 6 | Fair |
| chevron | 5 | Fair |
| concrete | 2 | Sparse |
| subway | 0 | **Not in data** |
| granite | 0 | **Not in data** |
| farmhouse | 1 | Sparse |

**Key gap**: "subway tile" is a very common customer search term but yields 0 results. Product names use different terminology for the same shape.

---

## Review & Rating Data

- `avg_rating` and `review_count` fields are present but **mostly empty/zero**
- The Bazaarvoice API returned limited review data for this product set
- Search results fall back to price-based sorting when review counts are tied

---

## Data Quality Summary

| Field | Coverage | Notes |
|-------|----------|-------|
| name | 100% | Always present |
| brand | 100% | Always present |
| price_sqft | ~98% | 2% null — filtered out in search |
| image_url | ~95% | Most have Amplience CDN URLs |
| product_url | 100% | Always present |
| material | ~99% | Extracted from product_type URL |
| finish | ~70% | Regex from product name |
| color | ~50% | Regex from product name |
| size | ~11% | Regex from name/description |
| description | ~90% | From Bazaarvoice API |
| avg_rating | <5% | Mostly empty |

---

## Recommendations for Improvement

1. **Color extraction** — Expand beyond 38 terms. Add Italian color words common in tile naming (Calacatta, Statuario, Bianco Carrara) and map them to base colors.
2. **Size extraction** — Parse sizes from the SFCC product attributes rather than regex on names.
3. **Subway tile gap** — Add keyword synonyms/aliases (e.g., map "subway" → products with 3x6, 4x12, 2x8 dimensions).
4. **Review data** — Consider a separate Bazaarvoice bulk fetch for review stats, or use a different endpoint.
5. **Additional categories** — Current data is tiles only. Wood, vinyl, laminate, stone, and decoratives would expand the catalog significantly (noted in `todo.md`).
