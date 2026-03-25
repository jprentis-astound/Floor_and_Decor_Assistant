"""
LangGraph agent for Roomy — Floor & Decor tile assistant.
Uses a ReAct tool-calling loop with Claude via Anthropic API + SQLite search.
"""

import json
import os
from typing import Optional

from dotenv import load_dotenv
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode

from search import search_tiles, get_available_filters

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MODEL_ID = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514")


# ── LLM Factory ──────────────────────────────────────────────────────────────

def get_llm():
    return ChatAnthropic(
        model=MODEL_ID,
        max_tokens=4096,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


# ── Agent State ──────────────────────────────────────────────────────────────

class RoomyState(MessagesState):
    """Agent state — just messages with the LangGraph add_messages reducer."""
    pass


# ── Message Sanitization ─────────────────────────────────────────────────────

def sanitize_messages_for_claude(messages: list) -> list:
    """
    Anthropic requires every AIMessage with tool_calls to be immediately
    followed by its matching ToolMessage(s). AG-UI injects context messages that
    can break this contract. This rebuilds the list safely.
    """
    sanitized = []
    i = 0
    while i < len(messages):
        msg = messages[i]

        if isinstance(msg, HumanMessage):
            sanitized.append(msg)
            i += 1

        elif isinstance(msg, AIMessage):
            if hasattr(msg, "tool_calls") and msg.tool_calls:
                tool_call_ids = {tc["id"] for tc in msg.tool_calls}
                tool_msgs = []
                j = i + 1
                while j < len(messages) and isinstance(messages[j], ToolMessage):
                    if messages[j].tool_call_id in tool_call_ids:
                        tool_msgs.append(messages[j])
                    j += 1

                if len(tool_msgs) == len(tool_call_ids):
                    sanitized.append(msg)
                    sanitized.extend(tool_msgs)
                    i = j
                else:
                    i += 1
            else:
                sanitized.append(msg)
                i += 1

        elif isinstance(msg, ToolMessage):
            i += 1

        else:
            i += 1

    return sanitized


# ── Backend Tools ────────────────────────────────────────────────────────────

@tool
def search_tile_products(
    query: str = "",
    material: str = "",
    min_price: float = 0,
    max_price: float = 0,
    brand: str = "",
    finish: str = "",
    color: str = "",
    limit: int = 6,
) -> str:
    """Search Floor & Decor tile products by natural language query and/or filters.

    Args:
        query: Free text search terms (e.g. "subway tile", "hexagon mosaic")
        material: Filter by material type: Porcelain, Ceramic, or Glass
        min_price: Minimum price per square foot (0 means no minimum)
        max_price: Maximum price per square foot (0 means no maximum)
        brand: Filter by brand name (e.g. "Maximo", "San Giorgio")
        finish: Filter by finish type: Matte, Polished, Honed, Glossy, Textured
        color: Filter by color (e.g. "white", "gray", "beige")
        limit: Number of results to return (default 6, max 10)
    """
    print(f"\n{'='*60}")
    print(f"[TOOL CALL] search_tile_products")
    print(f"  query={query!r}, material={material!r}, color={color!r}")
    print(f"  finish={finish!r}, brand={brand!r}")
    print(f"  min_price={min_price}, max_price={max_price}, limit={limit}")
    print(f"{'='*60}")

    results = search_tiles(
        query=query,
        material=material,
        min_price=min_price if min_price > 0 else None,
        max_price=max_price if max_price > 0 else None,
        brand=brand,
        finish=finish,
        color=color,
        limit=min(limit, 10),
    )

    print(f"  → {len(results)} results returned")

    if not results:
        return json.dumps({"results": [], "message": "No tiles found matching your criteria. Try broadening your search."})

    simplified = []
    for r in results:
        simplified.append({
            "name": r["name"],
            "brand": r["brand"],
            "material": r["material"],
            "finish": r["finish"],
            "color": r["color"],
            "size": r["size"],
            "price_sqft": f"${r['price_sqft']:.2f}" if r["price_sqft"] else "N/A",
            "price_box": f"${r['price_box']:.2f}" if r["price_box"] else "N/A",
            "image_url": r["image_url"],
            "product_url": r["product_url"],
        })

    return json.dumps({"results": simplified, "count": len(simplified)})


@tool
def get_tile_filters() -> str:
    """Get available filter options for tile search (materials, brands, finishes, price range).
    Call this when the user wants to know what options are available."""
    filters = get_available_filters()
    return json.dumps(filters)


@tool
def show_video(
    topic: str = "",
) -> str:
    """Show a relevant Floor & Decor video to the customer. Use this when the customer asks about installation, how-to, or DIY topics.

    Args:
        topic: The topic to find a video for (e.g. "tile installation", "backsplash", "grouting", "floor prep")
    """
    # Video library — F&D TVPage videos with direct MP4 sources
    # Pattern: //v.tvpage.com/1759402/{video_id}/{hash}/{quality}_media.mp4
    videos = [
        {"title": "How to Install Tile & Stone", "topic": "tile installation install", "video_url": "https://v.tvpage.com/1759402/227571108/a49b9/480p_media.mp4", "poster": "https://i8.amplience.net/i/flooranddecor/design-services-re-studios?w=560&fmt=auto&qlt=80&sm=aspect&aspect=16:9&$poi$", "duration": "Workshop", "page_url": "https://www.flooranddecor.com/videos/v/floor-decor-workshop-how-to-install-tile-stone/227571108"},
        {"title": "How to Install a Backsplash", "topic": "backsplash kitchen wall", "video_url": "https://v.tvpage.com/1759402/227571108/a49b9/480p_media.mp4", "poster": "https://i8.amplience.net/i/flooranddecor/design-services-re-any-style?w=560&fmt=auto&qlt=80&sm=aspect&aspect=16:9&$poi$", "duration": "Workshop", "page_url": "https://www.flooranddecor.com/videos/v/floor-decor-workshop-how-to-install-a-backsplash/227571109"},
        {"title": "How to Prepare Your Subfloor", "topic": "floor prep subfloor surface preparation", "video_url": "https://v.tvpage.com/1759402/227571108/a49b9/480p_media.mp4", "poster": "https://i8.amplience.net/i/flooranddecor/design-services-re-design-centers?w=560&fmt=auto&qlt=80&sm=aspect&aspect=16:9&$poi$", "duration": "Workshop", "page_url": "https://www.flooranddecor.com/videos/v/how-to-prepare-your-subfloor/227571111"},
        {"title": "How to Grout Tile", "topic": "grouting grout", "video_url": "https://v.tvpage.com/1759402/227571108/a49b9/480p_media.mp4", "poster": "https://i8.amplience.net/i/flooranddecor/design-services-re-galleries?w=560&fmt=auto&qlt=80&sm=aspect&aspect=16:9&$poi$", "duration": "Workshop", "page_url": "https://www.flooranddecor.com/videos/v/how-to-grout-tile/227571110"},
        {"title": "Floor Tile Installation Guide", "topic": "floor tile flooring", "video_url": "https://v.tvpage.com/1759402/227571108/a49b9/480p_media.mp4", "poster": "https://i8.amplience.net/i/flooranddecor/design-services-re-blogs?w=560&fmt=auto&qlt=80&sm=aspect&aspect=16:9&$poi$", "duration": "Workshop", "page_url": "https://www.flooranddecor.com/videos/v/floor-decor-workshop-how-to-install-tile-stone/227571108"},
    ]

    topic_lower = topic.lower()
    # Find best match
    matched = []
    for v in videos:
        if any(word in v["topic"] for word in topic_lower.split()):
            matched.append(v)

    if not matched:
        matched = [videos[0]]  # Default to tile installation

    return json.dumps({"videos": matched[:3]})


BACKEND_TOOLS = [search_tile_products, get_tile_filters, show_video]

# ── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Roomy, a friendly and knowledgeable Help Center assistant for Floor & Decor.

## Your Role
You are the primary help center assistant — customers come to you with questions about flooring products, installation, care & maintenance, orders, returns, design services, and more.

## Your Capabilities
1. **Product Search** — You can search Floor & Decor's catalog of 1,192+ tile products (porcelain, ceramic, glass) with real prices and images using the `search_tile_products` tool.
3. **Video Tutorials** — You can show relevant how-to videos using the `show_video` tool. Use this whenever a customer asks about installation, how-to, or DIY topics.
2. **Help Center Knowledge** — You provide expert guidance on:
   - **Installation**: Step-by-step instructions for installing tile, tools needed, surface preparation, grouting, and best practices
   - **Care & Maintenance**: How to clean and maintain different tile types, recommended products, stain removal
   - **Orders & Shipping**: Order status, shipping options, delivery timelines
   - **Returns & Cancellations**: Return policy (90-day return window for most items), process for returns
   - **Design Services**: Free in-store design consultations, online design tools
   - **Pro Premier Services**: Benefits for contractors and professionals
   - **Workshops**: Free in-store DIY workshops held the first Saturday of each month — hands-on learning for tile installation, backsplash projects, and more. Register at flooranddecor.com/vhtc.html

## How to Handle Product Requests
When a customer asks about products (browsing, searching, comparing):
1. Use the `search_tile_products` tool to find matching tiles.
   - Extract relevant filters from their question (material, color, price range, finish, etc.)
   - For price mentions like "under $5" → set max_price=5
   - For material mentions like "porcelain" → set material="Porcelain"
   - For style mentions like "subway" or "hexagon" → include in query
2. Present results with a brief helpful summary: name, material, price/sqft, size, brand.

## How to Handle Help Center Questions
For non-product questions (installation, care, orders, etc.):
1. Give a clear, step-by-step answer
2. Link to relevant Floor & Decor resources when applicable:
   - Tile category page: https://www.flooranddecor.com/tile
   - Installation materials: https://www.flooranddecor.com/installation-materials
   - Installation videos: https://www.flooranddecor.com/videos/v/floor-decor-workshop-how-to-install-tile-stone/227571108
   - In-store workshops: https://www.flooranddecor.com/vhtc.html
   - Design services: https://www.flooranddecor.com/design-services
   - Return policy: https://www.flooranddecor.com/return-policy.html
3. Point customers to in-store workshops or design consultations when relevant

## Follow-up Questions
ALWAYS end your response with 2-3 suggested follow-up questions the customer might want to ask next. Format them as a short list. For example, after answering about tile installation:
- "What type of tile is best suited for a beginner DIY project?"
- "Can you recommend the essential tools needed for a tile installation project?"
- "What are the steps to properly prepare a surface before installing tiles?"

## Response Style
- Warm, encouraging, and concise — like a knowledgeable store associate
- Use the customer's language (don't be overly technical unless they are)
- For installation/care topics, give practical step-by-step guidance
- Always mention relevant Floor & Decor services (workshops, design help, in-store experts)

## Important Rules
- ALWAYS use the search tool before showing products — never make up product data
- Only show real Floor & Decor products from search results
- Never fabricate URLs, prices, or product names
- For questions outside your knowledge, suggest the customer call 1-877-675-0002 or visit their local store"""


# ── Graph Nodes ──────────────────────────────────────────────────────────────

def route_after_chat(state: RoomyState):
    """Check if the last message has tool calls."""
    messages = state.get("messages", [])
    if not messages:
        return END
    last = messages[-1]
    if hasattr(last, "tool_calls") and last.tool_calls:
        return "tools"
    return END


async def chat_node(state: RoomyState, config):
    """Main agent node — calls Claude via Anthropic API with backend tools."""
    messages = state.get("messages", [])

    llm = get_llm().bind_tools(BACKEND_TOOLS)

    safe_messages = sanitize_messages_for_claude(messages)
    full_messages = [SystemMessage(content=SYSTEM_PROMPT)] + safe_messages

    response = await llm.ainvoke(full_messages, config)
    return {"messages": [response]}


# ── Build the Graph ──────────────────────────────────────────────────────────

def create_agent_graph():
    """Create the LangGraph agent with a tool-calling loop + checkpointer."""
    tool_node = ToolNode(BACKEND_TOOLS)

    builder = StateGraph(RoomyState)
    builder.add_node("chat", chat_node)
    builder.add_node("tools", tool_node)

    builder.set_entry_point("chat")
    builder.add_conditional_edges("chat", route_after_chat, {
        "tools": "tools",
        END: END,
    })
    builder.add_edge("tools", "chat")

    # MemorySaver is REQUIRED — ag_ui_langgraph calls graph.aget_state()
    return builder.compile(checkpointer=MemorySaver())


graph = create_agent_graph()
