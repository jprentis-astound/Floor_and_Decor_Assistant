# Roomy — Floor & Decor AI Assistant

An AI-powered sidebar chat widget for the [Floor & Decor](https://www.flooranddecor.com) website. Customers ask flooring questions and receive answers enriched with product links, video tutorials, care guides, and workshop invitations.

## Architecture

The project has three layers:

1. **Embed Script** — vanilla JS injected on the F&D storefront that loads the chat widget in an iframe.
2. **CopilotKit Sidebar** (`apps/frontend/`) — Next.js 14 + CopilotKit React UI for streaming chat and Generative UI widgets.
3. **LangGraph Agent** (`packages/agent/`) — Python graph: *classify intent → generate answer → enrich with F&D resources → suggest follow-ups*. Uses Anthropic Claude as the LLM.

```
roomy-assistant/
├── apps/frontend/          # Next.js 14 (CopilotKit UI)
└── packages/agent/         # LangGraph agent (Python / FastAPI)
data-scraping/              # Product scraping utilities
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| Storefront | Salesforce Commerce Cloud (SFCC / SFRA) |
| Frontend | Next.js 14, CopilotKit, Tailwind CSS |
| Agent | LangGraph, LangChain, Python FastAPI |
| LLM | Anthropic Claude (claude-sonnet-4-6) |
| Hosting | Vercel (frontend) / Railway or Render (backend) |

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.11+

### Backend (LangGraph Agent)

```bash
cd roomy-assistant/packages/agent
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # Add your ANTHROPIC_API_KEY
uvicorn server:app --reload --port 8000
```

### Frontend (Next.js)

```bash
cd roomy-assistant/apps/frontend
npm install
# Create .env.local with: AGENT_URL=http://localhost:8000/copilotkit
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) to see the chat widget.

## Environment Variables

| Variable | Location | Description |
|----------|----------|-------------|
| `ANTHROPIC_API_KEY` | `packages/agent/.env` | Anthropic API key |
| `AGENT_URL` | `apps/frontend/.env.local` | URL of the Python agent server |

## Data Scraping

The `data-scraping/` directory contains scripts for scraping Floor & Decor product data:

```bash
cd data-scraping
python scrape_sitemap.py      # Collect product URLs
python scrape_products.py     # Scrape product details
python analyze_data.py        # Analyze scraped data
```

## License

Private — internal use only.
