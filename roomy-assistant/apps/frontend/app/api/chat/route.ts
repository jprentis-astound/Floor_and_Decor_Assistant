import { NextRequest } from "next/server";

const BACKEND_URL = process.env.AGENT_URL ?? "http://localhost:8080";

export async function POST(req: NextRequest) {
  const body = await req.json();

  const response = await fetch(`${BACKEND_URL}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    return new Response(
      JSON.stringify({ error: `Backend error: ${response.status}` }),
      { status: response.status, headers: { "Content-Type": "application/json" } }
    );
  }

  return new Response(response.body, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
