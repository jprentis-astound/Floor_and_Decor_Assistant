# Roomy — Floor & Decor AI Assistant

An AI-powered help center assistant for [Floor & Decor](https://www.flooranddecor.com). Customers ask flooring questions and receive streaming answers enriched with product cards, video tutorials, care guides, and workshop invitations.

## Architecture

```
roomy-assistant/
├── apps/frontend/              # Next.js 14 — Help Center UI
│   ├── app/
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Entry point
│   │   └── api/chat/route.ts   # SSE proxy to Python backend
│   ├── components/
│   │   ├── RoomyApp.tsx        # Main page + inline chat component
│   │   └── RoomyWidgets.tsx    # Product cards, video player widgets
│   └── public/
│       └── fd-logo.svg         # Official Floor & Decor logo
└── packages/agent/             # LangGraph agent (Python)
    ├── agent.py                # ReAct graph: chat → tools → chat
    ├── search.py               # SQLite FTS5 product search
    ├── server.py               # FastAPI SSE streaming endpoint
    └── tiles.db                # 1,192 real F&D tile products
data-scraping/                  # Product scraping utilities
```

### How It Works

1. **Frontend** — Next.js help center page with categories, trending questions, and a fixed bottom chat bar. When the user types, the chat drawer slides up with streaming responses.
2. **API Proxy** — Next.js API route (`/api/chat`) proxies SSE from the Python backend, avoiding CORS issues.
3. **Backend** — FastAPI streams LangGraph agent events as SSE (tokens, tool calls, tool results). The agent uses Claude Sonnet for reasoning and has three tools:
   - `search_tile_products` — SQLite FTS5 search across 1,192 real F&D tiles
   - `get_tile_filters` — Returns available materials, brands, finishes, price ranges
   - `show_video` — Returns relevant F&D how-to videos with inline playback

## Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 14, React, Tailwind CSS, react-markdown |
| Agent | LangGraph, LangChain, Python FastAPI |
| LLM | Anthropic Claude (`claude-sonnet-4-20250514`) |
| Database | SQLite with FTS5 full-text search |
| Streaming | Server-Sent Events (SSE) |
| Hosting | Vercel (frontend) / Railway or Render (backend) |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+
- Anthropic API key

### Backend (LangGraph Agent)

```bash
cd roomy-assistant/packages/agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Add your ANTHROPIC_API_KEY
uvicorn server:app --reload --port 8080
```

### Frontend (Next.js)

```bash
cd roomy-assistant/apps/frontend
npm install
# Create .env.local with: AGENT_URL=http://localhost:8080
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the help center.

## Environment Variables

| Variable | Location | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | `packages/agent/.env` | Anthropic API key |
| `ANTHROPIC_MODEL` | `packages/agent/.env` | Model ID (default: `claude-sonnet-4-20250514`) |
| `AGENT_URL` | `apps/frontend/.env.local` | Python backend URL (default: `http://localhost:8080`) |

## Features

- **Streaming chat** — Real-time token-by-token response streaming via SSE
- **Product search** — Search 1,192 real F&D tiles by material, color, price, finish, brand
- **Inline product cards** — Rich cards with images, prices, and "View Product" links
- **Video tutorials** — Inline playable F&D workshop videos with expand/collapse
- **Help center topics** — Installation, care, shipping, returns, design services, workshops
- **Follow-up suggestions** — Agent suggests relevant next questions
- **Agentic UI** — Live status indicators (Thinking, Searching, Writing)

## Data Scraping

The `data-scraping/` directory contains scripts for scraping Floor & Decor product data:

```bash
cd data-scraping
python scrape_sitemap.py      # Collect product URLs
python scrape_products.py     # Scrape product details → tiles.db
python analyze_data.py        # Analyze scraped data
```

## License

Private — internal use only.
