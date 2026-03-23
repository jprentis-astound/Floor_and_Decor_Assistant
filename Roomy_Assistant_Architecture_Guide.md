# Floor & Decor — Roomy Personal Assistant
## Agent Sidebar — Architecture & Implementation Guide
### Built with CopilotKit + LangGraph + Anthropic Claude
*March 2026 — Confidential*

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Floor & Decor Website Tech Stack — Confirmed](#2-floor--decor-website-tech-stack--confirmed)
3. [Architecture Overview](#3-architecture-overview)
4. [Project Structure](#4-project-structure)
5. [Frontend Code (CopilotKit + Next.js)](#5-frontend-code-copilotkit--nextjs)
6. [Backend Code (LangGraph Agent + Anthropic Claude)](#6-backend-code-langgraph-agent--anthropic-claude)
7. [Generative UI — In-Chat Widgets](#7-generative-ui--in-chat-widgets)
8. [Floor & Decor Resource Pages — Scraped Summary](#8-floor--decor-resource-pages--scraped-summary)
9. [Demo Questions & Intended Responses](#9-demo-questions--intended-responses)
10. [Environment Variables & Deployment](#10-environment-variables--deployment)
11. [Recommended Next Steps](#11-recommended-next-steps)
12. [Product Data Sourcing for Roomy](#12-product-data-sourcing-for-roomy)

---

## 1. Project Overview

The **Roomy Personal Assistant** is an AI-powered sidebar widget embedded on the Floor & Decor website. It enables customers to ask flooring-related questions and receive intelligent, contextual answers enriched with Floor & Decor-specific product links, video tutorials, care guides, and workshop invitations — modelled after the Lowe's AI assistant experience.

**Competitor Reference:** [Lowe's AI at Lowes](https://www.lowes.com/l/about/ai-at-lowes) — demonstrates step-by-step instructions, product recommendations, video links, care guides, and follow-up question suggestions.

### Technology Stack

| Layer | Technology |
|---|---|
| F&D Storefront | Salesforce Commerce Cloud (SFCC) — Storefront Reference Architecture (SFRA) |
| Frontend UI | CopilotKit v2 — `CopilotSidebar` from `@copilotkit/react-core/v2` |
| Agent Framework | LangGraph — stateful, multi-step AI agent graph |
| LLM | Anthropic Claude (`claude-sonnet-4-6`) |
| Backend Runtime | Python — FastAPI + `ag-ui-langgraph` + `copilotkit` middleware |
| Node.js Bridge | CopilotKit Runtime — `LangGraphHttpAgent` in a Next.js API route |
| Hosting | AWS Amplify (Next.js frontend) / AWS ECS Fargate (Python backend) |
| LLM Provider | AWS Bedrock — `anthropic.claude-3-haiku-20240307-v1:0` |
| Website Integration | `<script>` tag injected into SFRA's global footer ISML template |

---

## 2. Floor & Decor Website Tech Stack — Confirmed

**`flooranddecor.com` is built on Salesforce Commerce Cloud (SFCC), running its latest Storefront Reference Architecture (SFRA).** This is now confirmed, and it directly shapes how Roomy is integrated.

### What SFCC SFRA Means for This Integration

SFRA is a Node.js/Express MVC framework running on Salesforce's managed cloud. It uses **ISML templates** (Salesforce's server-side templating language) to render storefront pages. All global page elements — header, footer, scripts — live in a small set of shared cartridge template files.

This is actually ideal for our purposes because:

- **No storefront re-architecture needed.** Roomy runs entirely outside SFCC. It's a decoupled app hosted on AWS Amplify.
- **One-line embed.** A single `<script>` tag added to the SFRA global footer template is all that touches the storefront.
- **No Salesforce cartridge required.** Since Roomy is not a commerce feature (no cart, no checkout), it doesn't need to be certified or deployed as an SFCC cartridge.

### Exactly Where to Add the Embed in SFRA

The embed script goes into the SFRA footer ISML template. The path inside the cartridge is:

```
app_storefront_base/
└── cartridge/
    └── templates/
        └── default/
            └── components/
                └── footer/
                    └── footer.isml   ← add the <script> tag here
```

Add this one line just before the closing `</body>` tag:

```html
<!-- Roomy Personal Assistant — Floor & Decor AI Sidebar -->
<script src="https://your-app.amplifyapp.com/roomy-widget.js" defer></script>
```

If the storefront uses a custom cartridge that overrides `footer.isml`, the tag goes in the override file instead. Your SFCC developer will know which cartridge is active.

### SFCC-Specific Requirements

**Content Security Policy (CSP)**
SFCC enforces strict CSP headers by default. Your IT or platform team must add the Roomy hosting domain to two CSP directives in Business Manager under **Merchant Tools → SEQ → Content Security Policy**:

| Directive | Value to add |
|---|---|
| `frame-src` | `https://your-app.amplifyapp.com` |
| `script-src` | `https://your-app.amplifyapp.com` |

Without these additions, the browser will silently block both the embed script and the iframe.

**CORS on the FastAPI backend**
The Roomy agent backend must allow requests from the F&D domain. Add this to `server.py`:

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://www.flooranddecor.com"],
    allow_methods=["POST"],
    allow_headers=["*"],
)
```

**Page Designer (optional scope control)**
If the team wants Roomy to appear only on specific pages (e.g. just Tile category pages, not checkout), SFCC's Page Designer can place the widget as a component on selected page types rather than injecting it sitewide via the footer.

---

## 3. Architecture Overview

The sidebar follows a three-layer architecture:

```
┌──────────────────────────────────────────────────┐
│           FLOOR & DECOR WEBSITE                  │
│   Salesforce Commerce Cloud — SFRA               │
│                                                  │
│   <script src="roomy-widget.js"></script>        │
│           ↓ injects iframe                       │
│   ┌──────────────────────────────────────┐       │
│   │   CopilotKit Sidebar (React)         │       │
│   │   • Chat input & messages            │       │
│   │   • Streaming responses              │       │
│   │   • Suggested follow-up questions    │       │
│   │   • Product / link cards             │       │
│   └──────────────────────────────────────┘       │
└──────────────────────────────────────────────────┘
                       ↓ REST / WebSocket
┌──────────────────────────────────────────────────┐
│         BACKEND (Python / FastAPI)               │
│                                                  │
│  CopilotKit Runtime ────── LangGraph Agent       │
│                                 │                │
│               ┌─────────────────┴──────────┐     │
│               │    Agent Graph Nodes        │     │
│               │    1. Classify intent       │     │
│               │    2. Generate answer       │     │
│               │    3. Add F&D links         │     │
│               │    4. Suggest questions     │     │
│               └────────────────────────────┘     │
│                            ↓                     │
│             Anthropic Claude API                 │
└──────────────────────────────────────────────────┘
```

### How Each Layer Works

**Layer 1 — The Embed Script** is a tiny vanilla JavaScript file (~30 lines) placed on the F&D website. It injects a floating "Ask Roomy" button and an iframe pointing to the hosted Next.js app.

**Layer 2 — The CopilotKit Sidebar** is a React/Next.js app hosted separately. CopilotKit provides a pre-built `<CopilotSidebar>` component that handles the chat UI, streaming, and state management out of the box.

**Layer 3 — The LangGraph Agent** is the brain. It receives each user message, runs it through a 4-node graph (classify → answer → enrich → suggest), calls Anthropic Claude for the answer, attaches relevant F&D resources, and returns a structured response.

---

## 4. Project Structure

```
roomy-assistant/
├── apps/
│   └── frontend/                    # Next.js 14 app (CopilotKit UI)
│       ├── app/
│       │   ├── layout.tsx           # CopilotKit provider wraps everything
│       │   └── page.tsx             # Main page (or sidebar-only entry)
│       ├── components/
│       │   ├── RoomyAssistant.tsx   # Sidebar component
│       │   ├── ProductCard.tsx      # F&D product / link card
│       │   └── SuggestedQuestions.tsx
│       ├── lib/
│       │   └── fd-knowledge-base.ts # F&D URLs & resource metadata
│       └── public/
│           └── roomy-widget.js      # Tiny embed script for F&D website
└── packages/
    └── agent/                       # LangGraph agent (Python)
        ├── agent.py                 # Main graph definition
        ├── nodes/
        │   ├── classify.py          # Detect flooring topic
        │   ├── answer.py            # Generate Claude response
        │   ├── enrich.py            # Attach F&D resources & links
        │   └── suggest.py           # Generate follow-up questions
        ├── knowledge_base.py        # F&D resource definitions
        └── server.py                # FastAPI server (CopilotKit runtime)
```

---

## 5. Frontend Code (CopilotKit + Next.js)

### 5.1 Install Dependencies

```bash
# Frontend (Next.js app)
npm install @copilotkit/react-core @copilotkit/react-ui @copilotkit/runtime

# Backend runtime LangGraph adapter
npm install @copilotkit/runtime
```

> **Note:** CopilotKit v2 is the latest version. Imports changed from v1 — always use the `/v2` path for components and styles (shown below).

### 5.2 CopilotKit Provider — `app/layout.tsx`

Wrap the entire app in the `CopilotKit` provider. The `agent` prop must match the agent name registered in the Copilot Runtime. Import the v2 styles here so they apply globally.

```tsx
// app/layout.tsx
import { CopilotKit } from "@copilotkit/react-core";
import "@copilotkit/react-ui/v2/styles.css"; // ← v2 styles, import once at root

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <CopilotKit
          runtimeUrl="/api/copilotkit"  // Points to the Next.js API route
          agent="roomy_assistant"        // Must match the agent name in CopilotRuntime
        >
          {children}
        </CopilotKit>
      </body>
    </html>
  );
}
```

### 5.3 Choosing a Chat UI Component

CopilotKit v2 ships **three** prebuilt components — pick the one that fits best:

| Component | Layout | Best for |
|---|---|---|
| `CopilotSidebar` | Fixed panel on the side, wraps your page content | Persistent assistant alongside the page |
| `CopilotPopup` | Floating bubble, overlays content | Lightweight chat button anywhere |
| `CopilotChat` | Inline, placed anywhere in your layout | Embedded chat panel in a specific area |

**For Roomy, `CopilotSidebar` is the right choice** — it mirrors the Lowe's sidebar pattern exactly.

### 5.4 Roomy Sidebar Component — `app/page.tsx`

In CopilotKit v2, `CopilotSidebar` **wraps your main page content** as children. The sidebar slides in alongside the content rather than overlaying it. Import from `@copilotkit/react-core/v2`.

```tsx
// app/page.tsx
"use client";
import { CopilotSidebar } from "@copilotkit/react-core/v2";

export default function Page() {
  return (
    // CopilotSidebar wraps your main content — it manages the layout
    <CopilotSidebar
      defaultOpen={false}
      width={420}
      labels={{
        modalHeaderTitle: "Roomy — Floor & Decor Assistant",
        welcomeMessageText: "Hi! I'm Roomy 🏠 Ask me anything about flooring — installation, cleaning, product selection, and more!",
        chatInputPlaceholder: "Ask Roomy a flooring question...",
      }}
    >
      {/* Your existing page content goes here */}
      <main>
        <h1>Welcome to Floor & Decor</h1>
        {/* rest of page */}
      </main>
    </CopilotSidebar>
  );
}
```

**Customising the look with slots** — every part of the sidebar UI can be overridden via slot props. No need to rebuild the component from scratch:

```tsx
<CopilotSidebar
  defaultOpen={false}
  // Style the header with a Tailwind class string
  header="bg-[#1B5E20] text-white"
  // Style the input area
  input={{
    textArea: "border-[#1B5E20] focus:ring-[#1B5E20]",
    sendButton: "bg-[#1B5E20] hover:bg-[#2E7D32]",
  }}
  // Style assistant message bubbles
  messageView={{
    assistantMessage: {
      className: "bg-[#E8F5E9] rounded-xl",
    },
    userMessage: "bg-[#1565C0] text-white rounded-xl",
  }}
  labels={{
    modalHeaderTitle: "Roomy — Floor & Decor Assistant",
    welcomeMessageText: "Hi! I'm Roomy 🏠 Ask me anything about flooring!",
  }}
>
  <YourMainContent />
</CopilotSidebar>
```

**Alternative — `CopilotPopup`** (floating button, no layout shift):

```tsx
// Use this if you don't want the sidebar to push the page content
import { CopilotPopup } from "@copilotkit/react-core/v2";

export default function Page() {
  return (
    <>
      <YourMainContent />
      <CopilotPopup
        labels={{
          modalHeaderTitle: "Roomy — Floor & Decor Assistant",
          welcomeMessageText: "Hi! I'm Roomy 🏠",
        }}
      />
    </>
  );
}
```

### 5.5 Embedding on the Floor & Decor Website (SFCC SFRA)

Add one line to the SFRA global footer ISML template — see Section 2 for the exact file path and SFCC-specific requirements (CSP, CORS).

```html
<!-- app_storefront_base/cartridge/templates/default/components/footer/footer.isml -->
<!-- Add just before </body> -->
<script src="https://your-app.amplifyapp.com/roomy-widget.js" defer></script>
```

The widget script (`public/roomy-widget.js`) injects a floating button and an iframe:

```js
// public/roomy-widget.js  (vanilla JS, ~30 lines)
(function () {
  // Create floating button
  const btn = document.createElement('button');
  btn.innerText = '🏠 Ask Roomy';
  btn.style.cssText = `
    position: fixed; bottom: 24px; right: 24px;
    background: #1B5E20; color: white; border: none;
    padding: 14px 20px; border-radius: 28px;
    font-size: 15px; cursor: pointer; z-index: 9999;
    box-shadow: 0 4px 16px rgba(0,0,0,0.25);
  `;
  document.body.appendChild(btn);

  // Create iframe sidebar
  const iframe = document.createElement('iframe');
  iframe.src = 'https://your-app.amplifyapp.com/sidebar';
  iframe.style.cssText = `
    display: none; position: fixed; bottom: 80px; right: 24px;
    width: 400px; height: 600px; border: none;
    border-radius: 16px; z-index: 9998;
    box-shadow: 0 8px 32px rgba(0,0,0,0.3);
  `;
  document.body.appendChild(iframe);

  // Toggle sidebar open/closed
  btn.addEventListener('click', () => {
    iframe.style.display = iframe.style.display === 'none' ? 'block' : 'none';
  });
})();
```

### 5.6 Next.js API Route — `app/api/copilotkit/route.ts`

The Copilot Runtime is the backend layer that connects the frontend to the LangGraph agent. It handles authentication, routing, and middleware. Use `LangGraphHttpAgent` to point at the Python FastAPI server, and `ExperimentalEmptyAdapter` since the LLM lives inside the Python agent (not on this Node.js side).

```ts
// app/api/copilotkit/route.ts
import {
  CopilotRuntime,
  ExperimentalEmptyAdapter,
  copilotRuntimeNextJSAppRouterEndpoint,
} from "@copilotkit/runtime";
import { LangGraphHttpAgent } from "@copilotkit/runtime/langgraph";
import { NextRequest } from "next/server";

const serviceAdapter = new ExperimentalEmptyAdapter();

const runtime = new CopilotRuntime({
  agents: {
    // "roomy_assistant" must match the agent= prop on <CopilotKit> and
    // the name registered in the Python FastAPI server
    roomy_assistant: new LangGraphHttpAgent({
      url: process.env.AGENT_URL ?? "http://localhost:8000",
    }),
  },
});

export const POST = async (req: NextRequest) => {
  const { handleRequest } = copilotRuntimeNextJSAppRouterEndpoint({
    runtime,
    serviceAdapter,
    endpoint: "/api/copilotkit",
  });
  return handleRequest(req);
};
```

> **Tip:** If you only have one agent and want to skip specifying `agent=` everywhere, name it `"default"` in the runtime — CopilotKit's prebuilt components will pick it up automatically.

---

## 6. Backend Code (LangGraph Agent + Anthropic Claude)

### 6.1 Install Dependencies

```bash
# Core agent + API server
pip install langgraph langchain-anthropic fastapi uvicorn

# CopilotKit middleware + AG-UI LangGraph endpoint adapter
pip install copilotkit ag-ui-langgraph
```

### 6.2 Knowledge Base — `knowledge_base.py`

This defines the Floor & Decor resource library the agent uses when enriching responses.

```python
# packages/agent/knowledge_base.py

FD_RESOURCES = {
  "tile_installation": {
    "topic_keywords": ["install tile", "lay tile", "tile floor", "tiling tips"],
    "resources": [
      {
        "type": "category",
        "title": "Shop Our Tile Collection",
        "url": "https://www.flooranddecor.com/tile",
        "description": "Browse hundreds of tile styles"
      },
      {
        "type": "category",
        "title": "Installation Materials",
        "url": "https://www.flooranddecor.com/installation-materials",
        "description": "Thinset, grout, spacers and tools"
      },
      {
        "type": "video",
        "title": "Watch: How to Install Tile (Workshop Video)",
        "url": "https://www.flooranddecor.com/videos/v/floor-decor-workshop-how-to-install-tile-stone/227571108",
        "description": "Step-by-step floor & stone installation video"
      },
      {
        "type": "workshop",
        "title": "Free In-Store Workshops",
        "url": "https://www.flooranddecor.com/vhtc.html",
        "description": "Free hands-on tile installation workshops — first Saturday of every month"
      },
    ]
  },
  "tile_cleaning": {
    "topic_keywords": ["clean tile", "cleaning tile", "tile floor care", "grout cleaning"],
    "resources": [
      {
        "type": "category",
        "title": "Tile Sealers & Cleaners",
        "url": "https://www.flooranddecor.com/tile-sealers-and-cleaners-installation-materials",
        "description": "Professional-grade tile and grout cleaners"
      },
      {
        "type": "guide",
        "title": "Tile Care Guide",
        "url": "https://www.flooranddecor.com/tile-care-guide",
        "description": "Complete guide to maintaining tile floors"
      },
      {
        "type": "pdf",
        "title": "Download: Tile Care & Maintenance Guide (PDF)",
        "url": "https://flooranddecor.a.bigcontent.io/v1/static/TileCareandMaintenanceGuide",
        "description": "Printable PDF care guide"
      },
      {
        "type": "blog",
        "title": "Cleaning Guide for Every Type of Floor",
        "url": "https://www.flooranddecor.com/blogs/cleaning-guide-for-every-type-of-floor.html",
        "description": "Blog article covering all floor types"
      },
    ]
  },
}
```

### 6.3 LangGraph Agent — `agent.py`

The agent is a 4-node graph: **classify intent → generate answer → enrich with F&D resources → suggest follow-up questions.**

```python
# packages/agent/agent.py
from langgraph.graph import StateGraph, END
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from typing import TypedDict, List, Optional
from knowledge_base import FD_RESOURCES
import json

# ── State definition ───────────────────────────────────────────────────────────
class RoomyState(TypedDict):
    user_message: str
    detected_topic: Optional[str]
    answer: Optional[str]
    resources: Optional[List[dict]]
    suggested_questions: Optional[List[str]]

# ── Claude LLM ─────────────────────────────────────────────────────────────────
llm = ChatAnthropic(
    model="claude-sonnet-4-6",
    anthropic_api_key="YOUR_ANTHROPIC_API_KEY",  # use env var in production
    temperature=0.3,
)

# ── Node 1: Classify topic ──────────────────────────────────────────────────────
def classify_node(state: RoomyState) -> RoomyState:
    """Detect which F&D topic the question matches."""
    msg = state["user_message"].lower()
    for topic, data in FD_RESOURCES.items():
        if any(kw in msg for kw in data["topic_keywords"]):
            return {**state, "detected_topic": topic}
    return {**state, "detected_topic": "general"}

# ── Node 2: Generate answer ─────────────────────────────────────────────────────
def answer_node(state: RoomyState) -> RoomyState:
    """Ask Claude for a step-by-step answer."""
    system = """You are Roomy, a friendly and knowledgeable flooring assistant
for Floor & Decor. Give clear, step-by-step answers. Be concise but thorough.
Always use a warm, encouraging tone. Do not make up product links."""

    response = llm.invoke([
        SystemMessage(content=system),
        HumanMessage(content=state["user_message"]),
    ])
    return {**state, "answer": response.content}

# ── Node 3: Enrich with F&D resources ──────────────────────────────────────────
def enrich_node(state: RoomyState) -> RoomyState:
    """Attach relevant Floor & Decor links and resources."""
    topic = state.get("detected_topic", "general")
    resources = FD_RESOURCES.get(topic, {}).get("resources", [])
    return {**state, "resources": resources}

# ── Node 4: Suggest follow-up questions ────────────────────────────────────────
def suggest_node(state: RoomyState) -> RoomyState:
    """Generate 3 relevant follow-up questions."""
    prompt = f"""Based on this question: '{state['user_message']}'
Suggest 3 short follow-up questions a Floor & Decor customer might ask next.
Return ONLY a JSON array of 3 strings. Example: ["Q1?", "Q2?", "Q3?"]"""

    result = llm.invoke([HumanMessage(content=prompt)])
    try:
        qs = json.loads(result.content)
    except Exception:
        qs = ["What tools do I need?", "How long will this project take?", "Can I get help in-store?"]
    return {**state, "suggested_questions": qs}

# ── Build the graph ─────────────────────────────────────────────────────────────
workflow = StateGraph(RoomyState)
workflow.add_node("classify", classify_node)
workflow.add_node("answer", answer_node)
workflow.add_node("enrich", enrich_node)
workflow.add_node("suggest", suggest_node)

workflow.set_entry_point("classify")
workflow.add_edge("classify", "answer")
workflow.add_edge("answer", "enrich")
workflow.add_edge("enrich", "suggest")
workflow.add_edge("suggest", END)

roomy_graph = workflow.compile()
```

### 6.4 FastAPI Server — `server.py`

Use `ag_ui_langgraph` to expose the LangGraph graph as an AG-UI-compatible HTTP endpoint. The `CopilotKitMiddleware` bridges the agent to CopilotKit's frontend features (generative UI, frontend actions, shared state). Add CORS middleware so the Next.js frontend can call this server cross-origin.

```python
# packages/agent/server.py
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ag_ui_langgraph import add_langgraph_fastapi_endpoint
from copilotkit import CopilotKitMiddleware, LangGraphAGUIAgent
from agent import roomy_graph

app = FastAPI()

# Allow requests from the Next.js frontend (local dev + production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://www.flooranddecor.com",       # production F&D site
        "https://your-app.amplifyapp.com",  # hosted Next.js app
    ],
    allow_methods=["POST"],
    allow_headers=["*"],
)

# Register the Roomy agent — name must match:
#   • agent= prop on <CopilotKit> in layout.tsx
#   • the key in CopilotRuntime agents{} in the Next.js API route
add_langgraph_fastapi_endpoint(
    app=app,
    agent=LangGraphAGUIAgent(
        name="roomy_assistant",
        description="Roomy — Floor & Decor flooring assistant",
        graph=roomy_graph,
        middleware=[CopilotKitMiddleware()],   # enables frontend tools & context
    ),
    path="/",
)

if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)

# Run with: python server.py
# Or:       uvicorn server:app --reload --port 8000
```

---

## 7. Generative UI — In-Chat Widgets

This is the core feature that makes Roomy match and exceed the Lowe's Mylow experience. Instead of plain text links, Roomy renders rich **visual cards directly inside the chat** — product tiles, video thumbnails, and workshop banners — using CopilotKit's Generative UI system.

### 7.1 How It Works

CopilotKit v2 provides the `useComponent` hook. You register a React component with a name and a Zod schema. When the LangGraph agent decides to show that component, it calls the tool by name — and CopilotKit automatically renders your component in the chat with the tool's arguments as props.

```
User asks: "How do I install tile?"
        ↓
Agent (Claude) generates step-by-step answer
        ↓
Agent calls showTileCategory({ title, description, url, imageUrl })
Agent calls showInstallMaterials({ title, description, url })
Agent calls showVideoCard({ title, thumbnailUrl, videoUrl, duration })
Agent calls showWorkshopCard({ title, schedule, url })
        ↓
CopilotKit renders each React widget inline in the chat
        ↓
User sees: text answer + product cards + video card + workshop card
```

### 7.2 Register Widgets on the Frontend — `components/RoomyWidgets.tsx`

```tsx
// components/RoomyWidgets.tsx
"use client";
import { useComponent } from "@copilotkit/react-core/v2";
import { z } from "zod";

// ── 1. Tile / Product Category Card ──────────────────────────────────────────
const tileCategorySchema = z.object({
  title:       z.string().describe("Card heading, e.g. 'Shop Our Tile Collection'"),
  description: z.string().describe("One-line description"),
  url:         z.string().describe("Full URL to the F&D category page"),
  imageUrl:    z.string().optional().describe("Hero image URL (optional)"),
  ctaLabel:    z.string().optional().describe("Button label, default 'Shop Now'"),
});

function TileCategoryCard({ title, description, url, imageUrl, ctaLabel }: z.infer<typeof tileCategorySchema>) {
  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden shadow-sm my-2 max-w-sm">
      {imageUrl && <img src={imageUrl} alt={title} className="w-full h-32 object-cover" />}
      <div className="p-3">
        <p className="font-semibold text-sm text-gray-900">{title}</p>
        <p className="text-xs text-gray-500 mt-1">{description}</p>
        <a
          href={url} target="_blank" rel="noreferrer"
          className="mt-3 inline-block bg-[#CC0000] text-white text-xs font-semibold px-4 py-2 rounded-full hover:bg-[#aa0000]"
        >
          {ctaLabel ?? "Shop Now"}
        </a>
      </div>
    </div>
  );
}

// ── 2. Installation Video Card ────────────────────────────────────────────────
const videoCardSchema = z.object({
  title:        z.string().describe("Video title"),
  description:  z.string().optional().describe("Short description"),
  videoUrl:     z.string().describe("Full URL to the F&D video page"),
  thumbnailUrl: z.string().optional().describe("Thumbnail image URL"),
});

function VideoCard({ title, description, videoUrl, thumbnailUrl }: z.infer<typeof videoCardSchema>) {
  return (
    <a href={videoUrl} target="_blank" rel="noreferrer"
       className="flex gap-3 rounded-xl border border-gray-200 p-3 shadow-sm my-2 max-w-sm hover:bg-gray-50">
      <div className="relative w-24 h-16 flex-shrink-0 rounded-lg overflow-hidden bg-gray-900 flex items-center justify-center">
        {thumbnailUrl
          ? <img src={thumbnailUrl} alt={title} className="w-full h-full object-cover" />
          : <span className="text-white text-2xl">▶</span>
        }
        <span className="absolute inset-0 flex items-center justify-center">
          <span className="bg-black/50 text-white rounded-full w-8 h-8 flex items-center justify-center text-sm">▶</span>
        </span>
      </div>
      <div>
        <p className="font-semibold text-sm text-gray-900">{title}</p>
        {description && <p className="text-xs text-gray-500 mt-1">{description}</p>}
        <p className="text-xs text-[#CC0000] mt-1 font-medium">Watch Video →</p>
      </div>
    </a>
  );
}

// ── 3. In-Store Workshop Card ─────────────────────────────────────────────────
const workshopCardSchema = z.object({
  title:    z.string().describe("Workshop title"),
  schedule: z.string().describe("When it runs, e.g. 'First Saturday of every month'"),
  url:      z.string().describe("Link to the workshop / VHTC page"),
});

function WorkshopCard({ title, schedule, url }: z.infer<typeof workshopCardSchema>) {
  return (
    <div className="rounded-xl border border-[#1B5E20] bg-[#E8F5E9] p-3 my-2 max-w-sm shadow-sm">
      <p className="text-xs font-bold uppercase text-[#1B5E20] tracking-wide">Free In-Store Workshop</p>
      <p className="font-semibold text-sm text-gray-900 mt-1">{title}</p>
      <p className="text-xs text-gray-600 mt-1">🗓 {schedule}</p>
      <a href={url} target="_blank" rel="noreferrer"
         className="mt-3 inline-block bg-[#1B5E20] text-white text-xs font-semibold px-4 py-2 rounded-full hover:bg-[#2E7D32]">
        Register Free
      </a>
    </div>
  );
}

// ── 4. Resource / Guide Link Card ────────────────────────────────────────────
const resourceCardSchema = z.object({
  type:        z.enum(["guide", "pdf", "blog", "category"]).describe("Resource type"),
  title:       z.string().describe("Card title"),
  description: z.string().describe("One-line description"),
  url:         z.string().describe("Full URL"),
});

function ResourceCard({ type, title, description, url }: z.infer<typeof resourceCardSchema>) {
  const icons: Record<string, string> = { guide: "📚", pdf: "📄", blog: "✍️", category: "🛍️" };
  return (
    <a href={url} target="_blank" rel="noreferrer"
       className="flex items-start gap-3 rounded-xl border border-gray-200 p-3 shadow-sm my-2 max-w-sm hover:bg-gray-50">
      <span className="text-2xl">{icons[type]}</span>
      <div>
        <p className="font-semibold text-sm text-gray-900">{title}</p>
        <p className="text-xs text-gray-500 mt-1">{description}</p>
        <p className="text-xs text-[#1565C0] mt-1 font-medium">View →</p>
      </div>
    </a>
  );
}

// ── Hook — call this inside your page component ───────────────────────────────
export function useRoomyWidgets() {
  useComponent({ name: "showTileCategory",    description: "Show a Floor & Decor tile or product category card in the chat.", parameters: tileCategorySchema,  render: TileCategoryCard });
  useComponent({ name: "showVideoCard",       description: "Show an installation video card in the chat.",                   parameters: videoCardSchema,      render: VideoCard });
  useComponent({ name: "showWorkshopCard",    description: "Show a free in-store workshop card in the chat.",               parameters: workshopCardSchema,   render: WorkshopCard });
  useComponent({ name: "showResourceCard",    description: "Show a guide, PDF, or blog link card in the chat.",             parameters: resourceCardSchema,   render: ResourceCard });
}
```

### 7.3 Use the Widgets in Your Page — `app/page.tsx`

Call `useRoomyWidgets()` inside the component that is a child of `<CopilotKit>`. This registers all four widget tools so the agent can find and invoke them.

```tsx
// app/page.tsx
"use client";
import { CopilotSidebar } from "@copilotkit/react-core/v2";
import { useRoomyWidgets } from "@/components/RoomyWidgets";

function PageContent() {
  // Register all widgets — agent can now call them as tools
  useRoomyWidgets();

  return (
    <main>
      <h1>Your main page content here</h1>
    </main>
  );
}

export default function Page() {
  return (
    <CopilotSidebar
      defaultOpen={false}
      width={420}
      labels={{
        modalHeaderTitle: "Roomy — Floor & Decor Assistant",
        welcomeMessageText: "Hi! I'm Roomy 🏠 Ask me anything about flooring!",
        chatInputPlaceholder: "Ask Roomy a flooring question...",
      }}
    >
      <PageContent />
    </CopilotSidebar>
  );
}
```

### 7.4 Enable Widgets in the Python Agent — `agent.py`

The Python agent must inherit from `CopilotKitState` so it can discover the widgets registered on the frontend. The system prompt instructs Claude to call them at the right time.

```python
# In agent.py — updated state and answer node
from copilotkit import CopilotKitState

class RoomyState(CopilotKitState):  # ← inherit from CopilotKitState
    user_message: str
    detected_topic: Optional[str]
    answer: Optional[str]
    suggested_questions: Optional[List[str]]

async def answer_node(state: RoomyState, config: RunnableConfig) -> RoomyState:
    """Generate answer and call widgets via frontend tools."""
    # Pull in the registered frontend widget tools
    frontend_tools = state.get("copilotkit", {}).get("actions", [])

    system = """You are Roomy, a friendly flooring assistant for Floor & Decor.

When answering questions about tile installation, ALWAYS call these tools after your answer:
- showTileCategory   → for tile category and product pages
- showInstallMaterials via showTileCategory → for installation materials
- showVideoCard      → for how-to videos
- showWorkshopCard   → for in-store workshops
- showResourceCard   → for guides, PDFs, and blog articles

Call each tool with real Floor & Decor URLs. Never make up URLs."""

    model = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.3)
    model_with_tools = model.bind_tools(frontend_tools)

    response = await model_with_tools.ainvoke([
        SystemMessage(content=system),
        HumanMessage(content=state["user_message"]),
    ], config)

    return {**state, "answer": response.content}
```

### 7.5 Widget Rendering Summary

| Widget | Tool Name | Triggers On | What It Shows |
|---|---|---|---|
| Tile Category Card | `showTileCategory` | Tile install / shop questions | Image + title + "Shop Now" button → `/tile` |
| Installation Materials Card | `showTileCategory` | Any install question | Brands grid + "Shop Now" → `/installation-materials` |
| Video Card | `showVideoCard` | How-to / install questions | Thumbnail + play button → workshop video page |
| Workshop Card | `showWorkshopCard` | Install questions | Green card + "Register Free" → `/vhtc.html` |
| Resource Card | `showResourceCard` | Cleaning / care questions | Icon + link → care guide, PDF, blog |

---

## 8. Floor & Decor Resource Pages — Scraped Summary

The following is what was found by directly browsing each resource URL. This informs exactly what the agent should say and link to.

### Tile Category (`/tile`)
- Full category page with left-rail filters: Color, Approximate Size, Materials, Product Type, and "Shop in-stock items" toggle
- Collections displayed as image grids with "SHOP NOW" buttons
- Top nav confirms F&D's six main categories: TILE · STONE · WOOD · LAMINATE · VINYL · DECORATIVES

### Installation Materials (`/installation-materials`)
- Category page showing subcategory tiles: **Mortars & Thinsets, Grout, Underlayment, Metal Trims, Shower Systems, Wood Adhesives, Moldings, Stair Parts, Outdoor Installation, Large Format Tile & Stone Installation, Floor Warming Systems, Leveling Systems**
- Brand wall prominently features: Schluter Systems, DeWalt, Raimondi, Bostik, Miracle Sealants, Laticrete, Sika, USG, Skil, Goldblatt, Mapei, FILA, Cortag, Rubi

### Installation Video (`/videos/v/floor-decor-workshop-how-to-install-tile-stone/227571108`)
- Page title: **"Floor & Decor Workshop: How to Install Tile & Stone"**
- Embedded video player (Brightcove / HTML5)
- Breadcrumb: Home / Video / Floor & Decor Workshop: How to Install Tile & Stone
- Secondary video nav tabs: Trends, Tile, Stone, Wood, Laminate, Vinyl, Decoratives, How-To

### Virtual How-To Clinics (`/vhtc.html`)
- Page title: **"Virtual How-To Clinics | Floor & Decor"**
- Located under: Home > Design Services > Virtual How-To Clinics
- Branded as **"FLOOR & DECOR HOW-TO CLINICS"** with hands-on workshop photography
- Covers multiple flooring types; tile installation workshop is the **first Saturday of every month**

### Tile Sealers & Cleaners (`/tile-sealers-and-cleaners-installation-materials`)
- Page title: **"Tile & Stone Sealers and Cleaners"**
- Breadcrumb: Installation Materials > Shop Tile & Stone Installation > Sealers & Cleaners
- Featured product image: Miracle Sealants 511 Impregnator Sealer
- Filters: Product Type, Brand

### Tile Care Guide (`/tile-care-guide`)
- Page title: **"Tile Care & Maintenance Guide — For Porcelain, Ceramic, and Glass Tile"**
- On-page sections: **General Care** · **Grout Maintenance**
- Key content: inorganic stains (soda, grout haze, soap scum, rust) → acidic cleaner; organic stains (grease, oil, wine, epoxy, adhesive) → alkaline cleaner
- Inline CTA: **"SHOP TILE CLEANERS"** button

### Cleaning Blog (`/blogs/cleaning-guide-for-every-type-of-floor.html`)
- Blog title: **"HOW TO CLEAN EVERY FLOORING TYPE"**
- Author: Floor & Decor
- Covers all flooring types — not just tile. Wide applicability for future Roomy questions about hardwood, LVP, laminate, stone.
- Sidebar: Popular Blogs — Trends, Tips

### Competitor Reference — Lowe's Mylow
- Named **"Mylow"** — positioned as "your home improvement helping hand"
- Three core value props: **Inspiration**, **Project Help**, **Product Recommendations**
- Floating chat button (bottom-right corner of site)
- Provides how-to guidance, idea inspiration, and shopping search directly in chat
- Key insight: **product recommendations appear as clickable cards with images and links**

---

## 9. Demo Questions & Intended Responses

### Demo Question 1 — "How do I install tile?"

**Trigger phrases:** how to install tile, how to lay tile, how to install a tile floor, tips for installing tile

**Full response flow:**
1. Claude generates a step-by-step tile installation guide (text)
2. Agent calls `showTileCategory` → **Tile Category Card** renders in chat
3. Agent calls `showTileCategory` again → **Installation Materials Card** renders in chat
4. Agent calls `showVideoCard` → **Video Card** with play button renders in chat
5. Agent calls `showWorkshopCard` → **Green Workshop Card** renders in chat
6. Agent generates 3 follow-up question suggestions

**Widgets rendered in sidebar chat:**

| Widget | Tool Called | What the User Sees |
|---|---|---|
| 🛍️ Tile Category Card | `showTileCategory` | Image card + "Shop Now" → [flooranddecor.com/tile](https://www.flooranddecor.com/tile) |
| 🔧 Installation Materials Card | `showTileCategory` | Brand logos + "Shop Now" → [flooranddecor.com/installation-materials](https://www.flooranddecor.com/installation-materials) |
| 🎥 Video Card | `showVideoCard` | Thumbnail + play button → [Floor & Decor Workshop: How to Install Tile & Stone](https://www.flooranddecor.com/videos/v/floor-decor-workshop-how-to-install-tile-stone/227571108) |
| 🏠 Workshop Card | `showWorkshopCard` | Green card "First Saturday of every month" → [Free In-Store Workshops](https://www.flooranddecor.com/vhtc.html) |

**Suggested follow-up questions (auto-generated):**
- What type of tile is best for a bathroom floor?
- How much thinset and grout do I need for a 100 sq ft room?
- Can I install tile over existing vinyl flooring?

---

### Demo Question 2 — "How do I clean tile floors?"

**Trigger phrases:** how to clean tile floors, cleaning tile floors, cleaning tile, grout cleaning

**Full response flow:**
1. Claude generates a step-by-step tile cleaning guide covering daily, weekly, and deep-clean routines — including the inorganic (acidic cleaner) vs. organic stain (alkaline cleaner) distinction from the scraped Tile Care Guide
2. Agent calls `showTileCategory` → **Tile Sealers & Cleaners Card** renders in chat
3. Agent calls `showResourceCard` (guide) → **Tile Care Guide Card** renders in chat
4. Agent calls `showResourceCard` (pdf) → **PDF Download Card** renders in chat
5. Agent calls `showResourceCard` (blog) → **Blog Article Card** renders in chat
6. Agent generates 3 follow-up question suggestions

**Widgets rendered in sidebar chat:**

| Widget | Tool Called | What the User Sees |
|---|---|---|
| 🧼 Tile Cleaners Card | `showTileCategory` | Product image + "Shop Now" → [Tile Sealers & Cleaners](https://www.flooranddecor.com/tile-sealers-and-cleaners-installation-materials) |
| 📚 Care Guide Card | `showResourceCard` | Guide icon + link → [Tile Care & Maintenance Guide](https://www.flooranddecor.com/tile-care-guide) |
| 📄 PDF Card | `showResourceCard` | PDF icon + download → [Tile Care Guide PDF](https://flooranddecor.a.bigcontent.io/v1/static/TileCareandMaintenanceGuide) |
| ✍️ Blog Card | `showResourceCard` | Blog icon + link → [How to Clean Every Flooring Type](https://www.flooranddecor.com/blogs/cleaning-guide-for-every-type-of-floor.html) |

**Suggested follow-up questions (auto-generated):**
- How do I clean grout lines without scrubbing?
- What's the best sealer for natural stone tiles?
- How often should I reseal my tile floor?

---

## 10. Environment Variables & Deployment

### 10.1 Environment Variables

```bash
# .env.local  (Next.js frontend)
AGENT_URL=http://localhost:8000/copilotkit

# .env  (Python backend — AWS Bedrock)
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-1
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
```

> **AWS IAM Note:** In production (ECS Fargate), attach an IAM role to the task with `bedrock:InvokeModel` permission instead of using long-lived access keys. The AWS SDK will automatically pick up the task role credentials.

### 10.2 Running Locally

```bash
# 1. Start the Python agent backend
cd packages/agent
pip install -r requirements.txt
uvicorn server:app --reload --port 8000

# 2. In a new terminal, start the Next.js frontend
cd apps/frontend
npm install
npm run dev

# 3. Open http://localhost:3000
# 4. Click the "Ask Roomy" button to open the sidebar
```

### 10.3 Production Deployment — AWS

| Service | AWS Platform | Notes |
|---|---|---|
| Frontend (Next.js) | [AWS Amplify](https://aws.amazon.com/amplify/) | Connect GitHub repo; set `AGENT_URL` env var in Amplify Console → Environment variables |
| Backend (Python FastAPI) | [AWS ECS Fargate](https://aws.amazon.com/fargate/) | Containerise with Docker; attach IAM task role with `bedrock:InvokeModel` permission |
| LLM | [AWS Bedrock](https://aws.amazon.com/bedrock/) | Model: `anthropic.claude-3-haiku-20240307-v1:0` — must be enabled in Bedrock Model Access console |
| Container Registry | [Amazon ECR](https://aws.amazon.com/ecr/) | Push Docker image here; ECS pulls from ECR |
| Embed script | Add `<script>` tag to `footer.isml` in the SFRA cartridge | See Section 2 for exact file path |
| CORS | Add `https://www.flooranddecor.com` to FastAPI CORS allow-list | Required for cross-origin iframe |
| CSP | Add Amplify domain to `frame-src` and `script-src` in SFCC Business Manager | See Section 2 — without this, the browser blocks the widget silently |

#### AWS Bedrock — Python Integration

Replace the direct Anthropic SDK call in `agent.py` with the Bedrock runtime client:

```python
import boto3
import json

bedrock = boto3.client(
    service_name="bedrock-runtime",
    region_name="us-east-1"  # or os.environ["AWS_REGION"]
)

def call_llm(prompt: str) -> str:
    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    })
    response = bedrock.invoke_model(
        modelId="anthropic.claude-3-haiku-20240307-v1:0",
        body=body,
        contentType="application/json",
        accept="application/json"
    )
    result = json.loads(response["body"].read())
    return result["content"][0]["text"]
```

#### ECS Fargate — Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY packages/agent/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY packages/agent/ .
EXPOSE 8000
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### IAM Policy for Bedrock Access

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "bedrock:InvokeModel",
      "Resource": "arn:aws:bedrock:us-east-1::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
    }
  ]
}
```

---

## 11. Recommended Next Steps

1. Enable the Anthropic Claude model in [AWS Bedrock Model Access](https://us-east-1.console.aws.amazon.com/bedrock/home#/modelaccess) (`anthropic.claude-3-haiku-20240307-v1:0`)
2. Set up the Next.js frontend project with CopilotKit v2 (Section 5)
3. Build the four widget components using `useComponent` (Section 7)
4. Set up the Python LangGraph agent with `CopilotKitState` and the Bedrock runtime client (Sections 6 & 10)
5. Update the agent system prompt to instruct Claude to call widget tools alongside answers
6. Test locally with the two demo questions — verify widgets render in the chat (Section 9)
7. Create an ECR repository, build and push the Docker image, then deploy the backend to ECS Fargate (Section 10)
8. Deploy the Next.js frontend to AWS Amplify — connect GitHub repo, set `AGENT_URL` to the ECS service URL (Section 10)
9. Work with the SFCC developer team to add the `<script>` tag to `footer.isml` in the active storefront cartridge (Section 2)
10. Have the platform/IT team update CSP directives in SFCC Business Manager (`frame-src` and `script-src`) — see Section 2
11. Add the Amplify domain to the FastAPI CORS allow-list before go-live
12. Use public product APIs (Bazaarvoice + SFCC Pricing + Sitemap) from day one; request Algolia key and SFCC OCAPI client_id from F&D platform team for richer product search (Section 12)
13. Expand the knowledge base and widgets with more topics — hardwood, LVP, carpet, stone, grout, and more

---

> **Ready for code files?** Say "Generate the full source code files" and all the individual runnable files (`agent.py`, `RoomyAssistant.tsx`, `server.py`, `knowledge_base.py`, etc.) will be created in your folder.

---

## 12. Product Data Sourcing for Roomy

During an API reconnaissance of `flooranddecor.com/tile`, four no-auth public data sources were confirmed alongside two internal credentials that unlock full catalog access. **No frontend scraping is needed for the Roomy MVP** — all required product data is available through structured APIs.

### 12.1 Data Sources at a Glance

| Source | Auth Required | Data Available |
|---|---|---|
| **Bazaarvoice API** | ✅ None (public passkey) | Product name, description, brand, category, image URL, SKU, review stats, Q&A counts |
| **SFCC Pricing Endpoint** | ✅ None (public endpoint) | Real-time price per sq ft, price per box, refinement price — by product ID |
| **XML Product Sitemap** | ✅ None (public) | 20,855 product URLs with embedded product IDs — updated daily |
| **Amplience Image CDN** | ✅ None (public CDN) | Product images via predictable URL: `i8.amplience.net/i/flooranddecor/{productId}_{slug}_display` |
| **Algolia Search** | ⚠️ Search-only API key needed | Full-text product search, faceted filters, relevance ranking — index: `production__products__default` |
| **SFCC OCAPI** | ⚠️ `client_id` required | Full product catalog, inventory, pricing, categories — the gold standard |

### 12.2 Confirmed Public APIs

These endpoints are fully public — no credentials, API keys, or authentication headers required. Call them directly from the Roomy LangGraph agent.

**Bazaarvoice Product API — No Auth Required**

```
GET https://api.bazaarvoice.com/data/batch.json
  ?passkey=caxdHHRkVz2B19Gp5BaswP6SynHfGhm28CG5XDvVs1Pig
  &apiversion=5.5
  &displaycode=10499-en_us
  &resource.q0=products
  &filter.q0=id:eq:{PRODUCT_ID}
  &stats.q0=questions,reviews

Returns: name, description, brand, category, image URL, SKU, review count, rating, Q&A count
```

**SFCC Real-Time Pricing — No Auth Required**

```
GET https://www.flooranddecor.com/on/demandware.store/
    Sites-floor-decor-Site/default/DynamicYield-GetProductStorePrices
    ?pids={ID1},{ID2},...

Returns: dy_product_price (per sq ft), product_price (per box), product_refinement_price
```

**XML Product Sitemap — No Auth Required**

```
GET https://www.flooranddecor.com/sitemap-PDP.xml

Contains 20,855 product URLs, updated daily.
Product IDs are embedded in the URL filename: e.g., porcelain-tile-101174019.html
Parse once daily to build/refresh your local product ID list.
```

### 12.3 Internal Credentials Needed

These two sources require credentials obtainable from the F&D platform/IT team. Neither requires personal user data or admin-level access — both are standard read-only API keys.

| Credential Needed | What It Unlocks |
|---|---|
| **Algolia Search-Only Key + App ID** | Query index `production__products__default` directly — full-text search, faceting, category browsing, relevance ranking. App ID is bundled in the F&D JS source; request the search-only key from the F&D platform team. |
| **SFCC OCAPI `client_id`** | Access `GET /dw/shop/v21_3/products/{id}` — full product detail including long descriptions, inventory, category hierarchy, and all attribute variants. Register in SFCC Business Manager under **Administration → Site Development → Open Commerce API Settings**. |

### 12.4 Recommended Data Strategy

Use a phased approach — start with the four public sources (sufficient for the Roomy MVP), then unlock search and full catalog access as internal credentials are provisioned.

| Phase | Data Sources | Capability |
|---|---|---|
| **Phase 1 — Now** | Bazaarvoice + SFCC Pricing + Sitemap + Amplience CDN | Product name, brand, image, category, price, review stats — zero credentials needed. Sufficient for Roomy MVP. |
| **Phase 2 — Quick Win** | + Algolia Search (search-only key from F&D platform team) | Adds natural-language product search — Roomy can search for "matte porcelain tile under $3/sq ft" in real time. |
| **Phase 3 — Full Data** | + SFCC OCAPI (`client_id` from F&D IT/Business Manager) | Complete product catalog access — full descriptions, all attributes, inventory, category tree. Enables a fully dynamic product knowledge base. |
