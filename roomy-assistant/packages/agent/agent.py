"""
LangGraph agent for Roomy — Floor & Decor tile assistant.
Uses a ReAct tool-calling loop with Claude via AWS Bedrock + SQLite search.
"""

import json
import os
from typing import Optional

import boto3
from dotenv import load_dotenv
from langchain_aws import ChatBedrock
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.tools import tool
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from langgraph.prebuilt import ToolNode

from copilotkit import CopilotKitState
from search import search_tiles, get_available_filters

load_dotenv()

MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")


# ── LLM Factory ──────────────────────────────────────────────────────────────

def get_llm():
    bedrock_client = boto3.client(
        service_name="bedrock-runtime",
        region_name=AWS_REGION,
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    return ChatBedrock(
        client=bedrock_client,
        model_id=MODEL_ID,
        model_kwargs={"max_tokens": 4096},
    )


# ── Agent State ──────────────────────────────────────────────────────────────

class RoomyState(CopilotKitState):
    """Agent state inherits CopilotKitState for AG-UI state sync."""
    pass


# ── Bedrock Message Sanitization ─────────────────────────────────────────────

def sanitize_messages_for_claude(messages: list) -> list:
    """
    Bedrock/Anthropic requires every AIMessage with tool_calls to be immediately
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


BACKEND_TOOLS = [search_tile_products, get_tile_filters]

# ── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are Roomy, a friendly and knowledgeable flooring assistant for Floor & Decor.

## Your Capabilities
You help customers find the perfect tile by searching Floor & Decor's product catalog.
You have access to 1,192 tile products (porcelain, ceramic, glass) with real prices and images.

## How to Handle Tile Search Requests
When a customer asks about tiles (browsing, searching, comparing):

1. Use the `search_tile_products` tool to find matching tiles.
   - Extract relevant filters from their question (material, color, price range, finish, etc.)
   - For price mentions like "under $5" → set max_price=5
   - For material mentions like "porcelain" → set material="Porcelain"
   - For style mentions like "subway" or "hexagon" → include in query

2. After getting search results, present them with a brief helpful summary.
   Mention the key details: name, material, price per sqft, size, and brand.

## Response Style
- Warm, encouraging, and concise
- Use the customer's language (don't be overly technical unless they are)
- If no results found, suggest broadening the search or offer alternatives
- Always mention that customers can visit a Floor & Decor store for hands-on experience

## Important Rules
- ALWAYS use the search tool before showing products — never make up product data
- Only show real Floor & Decor products from the search results
- Never fabricate URLs, prices, or product names"""


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
    """Main agent node — calls Claude via Bedrock with backend tools."""
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
