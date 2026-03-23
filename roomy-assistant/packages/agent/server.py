"""
FastAPI server for the Roomy agent.
Uses ag_ui_langgraph to expose the LangGraph agent via the AG-UI protocol.
"""

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from ag_ui_langgraph import LangGraphAgent, add_langgraph_fastapi_endpoint
from agent import graph

app = FastAPI(title="Roomy Agent API")

# CORS — allow the Next.js frontend (dev + production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3001",
        "https://www.flooranddecor.com",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the agent — name must match frontend CopilotKit agent= prop
roomy_agent = LangGraphAgent(
    name="roomy_assistant",
    graph=graph,
)

add_langgraph_fastapi_endpoint(app, roomy_agent, "/copilotkit")


@app.get("/health")
async def health():
    return {"status": "ok", "agent": "roomy_assistant"}


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8080, reload=True)
