# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Roomy Personal Assistant** — an AI-powered sidebar chat widget for the Floor & Decor website (flooranddecor.com). Modeled after Lowe's "Mylow" assistant. Customers ask flooring questions and receive answers enriched with F&D product links, video tutorials, care guides, and workshop invitations.

This repo currently contains the architecture guide (`Roomy_Assistant_Architecture_Guide.md`). Source code should be built following that guide.

## Tech Stack

| Layer | Technology |
|---|---|
| F&D Storefront | Salesforce Commerce Cloud (SFCC) — SFRA |
| Frontend UI | CopilotKit v2 (`@copilotkit/react-core/v2`) + Next.js 14 |
| Agent Framework | LangGraph (Python) |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) |
| Backend Runtime | Python FastAPI + `ag-ui-langgraph` + `copilotkit` middleware |
| Node.js Bridge | CopilotKit Runtime — `LangGraphHttpAgent` in Next.js API route |
| Hosting | Vercel (frontend) / Railway or Render (backend) |
| Website Integration | `<script>` tag in SFRA global footer ISML template |

## Architecture (3 Layers)

1. **Embed Script** — vanilla JS (~30 lines) on the F&D site injects a floating "Ask Roomy" button + iframe pointing to the hosted Next.js app.
2. **CopilotKit Sidebar** — React/Next.js app using `<CopilotSidebar>` for chat UI, streaming, and state management.
3. **LangGraph Agent** — 4-node graph: **classify intent → generate answer → enrich with F&D resources → suggest follow-up questions**. Calls Claude for the answer, attaches relevant F&D resources via Generative UI widgets.

## Target Project Structure

```
roomy-assistant/
├── apps/frontend/              # Next.js 14 (CopilotKit UI)
│   ├── app/
│   │   ├── layout.tsx          # CopilotKit provider
│   │   ├── page.tsx            # CopilotSidebar + widget registration
│   │   └── api/copilotkit/route.ts  # CopilotRuntime → LangGraphHttpAgent
│   ├── components/
│   │   └── RoomyWidgets.tsx    # Generative UI widgets (useComponent)
│   ├── lib/fd-knowledge-base.ts
│   └── public/roomy-widget.js  # Embed script for F&D site
└── packages/agent/             # LangGraph agent (Python)
    ├── agent.py                # Graph: classify → answer → enrich → suggest
    ├── nodes/                  # Individual graph node modules
    ├── knowledge_base.py       # F&D resource definitions
    └── server.py               # FastAPI + CopilotKitMiddleware
```

## Development Commands

```bash
# Python backend
cd packages/agent
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# Next.js frontend (separate terminal)
cd apps/frontend
npm install
npm run dev
# Open http://localhost:3000
```

## Environment Variables

- **Frontend** (`.env.local`): `AGENT_URL=http://localhost:8000/copilotkit`
- **Backend** (`.env`): `ANTHROPIC_API_KEY=sk-ant-xxxxxxxxxxxx`

## Key Integration Details

- The agent name `"roomy_assistant"` must match across three places: `<CopilotKit agent=...>` in `layout.tsx`, the key in `CopilotRuntime agents{}` in the API route, and the `name=` in `LangGraphAGUIAgent` in `server.py`.
- Agent state must inherit from `CopilotKitState` (not plain `TypedDict`) to enable Generative UI — frontend widget tools are discovered via `state["copilotkit"]["actions"]`.
- CopilotKit v2 imports use `/v2` path (e.g., `@copilotkit/react-core/v2`). Styles: `@copilotkit/react-ui/v2/styles.css`.
- Frontend widgets are registered via `useComponent` hook with Zod schemas — the agent calls them as tools and CopilotKit renders them inline in chat.

## Generative UI Widgets

Four widget tools the agent can invoke to render rich cards in chat:

| Widget | Tool Name | Purpose |
|---|---|---|
| Tile Category Card | `showTileCategory` | Product category with "Shop Now" CTA |
| Video Card | `showVideoCard` | Installation video with thumbnail + play button |
| Workshop Card | `showWorkshopCard` | Free in-store workshop with schedule + "Register Free" |
| Resource Card | `showResourceCard` | Guide, PDF, or blog link card |

## SFCC Integration Notes

- Embed goes in `app_storefront_base/cartridge/templates/default/components/footer/footer.isml`
- SFCC CSP must allow the hosting domain in both `frame-src` and `script-src` (configured in Business Manager)
- FastAPI CORS must include `https://www.flooranddecor.com`
