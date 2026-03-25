"""
FastAPI server for the Roomy agent.
Simple SSE streaming endpoint — no CopilotKit or AG-UI dependencies.
"""

import json
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage

from agent import graph

app = FastAPI(title="Roomy Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://www.flooranddecor.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    thread_id: str


async def stream_agent(user_message: str, thread_id: str):
    """Stream agent events as SSE."""
    input_msg = {"messages": [HumanMessage(content=user_message)]}
    config = {"configurable": {"thread_id": thread_id}}

    try:
        async for event in graph.astream_events(input_msg, config, version="v2"):
            kind = event["event"]

            # Stream text tokens
            if kind == "on_chat_model_stream":
                chunk = event["data"]["chunk"]
                if hasattr(chunk, "content") and chunk.content:
                    # Handle both string content and list content
                    content = chunk.content
                    if isinstance(content, list):
                        for block in content:
                            if isinstance(block, dict) and block.get("type") == "text":
                                text = block.get("text", "")
                                if text:
                                    yield f"event: token\ndata: {json.dumps({'content': text})}\n\n"
                    elif isinstance(content, str) and content:
                        yield f"event: token\ndata: {json.dumps({'content': content})}\n\n"

            # Tool call started
            elif kind == "on_tool_start":
                yield f"event: tool_call\ndata: {json.dumps({'name': event['name'], 'args': event['data'].get('input', {})})}\n\n"

            # Tool call finished
            elif kind == "on_tool_end":
                raw = event["data"]["output"]
                # ToolMessage object → extract content string
                if hasattr(raw, "content"):
                    result = raw.content
                else:
                    result = str(raw)
                yield f"event: tool_result\ndata: {json.dumps({'name': event['name'], 'result': result})}\n\n"

    except Exception as e:
        yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    yield "event: done\ndata: {}\n\n"


@app.post("/chat")
async def chat(req: ChatRequest):
    return StreamingResponse(
        stream_agent(req.message, req.thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "roomy_assistant"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
