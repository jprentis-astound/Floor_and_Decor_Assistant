"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import ReactMarkdown from "react-markdown";
import { TileSearchResults, TileResult, VideoResults, VideoResult } from "@/components/RoomyWidgets";

// ── Types ──────────────────────────────────────────────────────────────────

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  tileResults?: TileResult[];
  videoResults?: VideoResult[];
  done?: boolean;
}

// ── SSE Stream Parser ──────────────────────────────────────────────────────

async function streamChat(
  message: string,
  threadId: string,
  onToken: (text: string) => void,
  onToolCall: (name: string) => void,
  onToolResult: (name: string, result: string) => void,
  onDone: () => void,
  onError: (err: string) => void,
) {
  const res = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message, thread_id: threadId }),
  });
  if (!res.ok || !res.body) { onError(`Request failed: ${res.status}`); onDone(); return; }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const parts = buffer.split("\n\n");
    buffer = parts.pop() || "";
    for (const part of parts) {
      const lines = part.trim().split("\n");
      let eventType = "", data = "";
      for (const line of lines) {
        if (line.startsWith("event: ")) eventType = line.slice(7);
        if (line.startsWith("data: ")) data = line.slice(6);
      }
      if (!eventType || !data) continue;
      try {
        const parsed = JSON.parse(data);
        if (eventType === "token" && parsed.content) onToken(parsed.content);
        else if (eventType === "tool_call") onToolCall(parsed.name);
        else if (eventType === "tool_result") onToolResult(parsed.name, parsed.result);
        else if (eventType === "error") onError(parsed.error);
        else if (eventType === "done") { onDone(); return; }
      } catch {}
    }
  }
  onDone();
}

// ── Data ───────────────────────────────────────────────────────────────────

const CATEGORIES = [
  { label: "Product Questions", query: "What types of tile do you carry?", img: "https://i8.amplience.net/i/flooranddecor/design-services-re-design-centers?w=400&fmt=auto&qlt=80&sm=aspect&aspect=16:10&$poi$" },
  { label: "Installation Help", query: "How do I install tile?", img: "https://i8.amplience.net/i/flooranddecor/design-services-re-studios?w=400&fmt=auto&qlt=80&sm=aspect&aspect=16:10&$poi$" },
  { label: "Care & Cleaning", query: "How do I clean and maintain tile floors?", img: "https://i8.amplience.net/i/flooranddecor/design-services-re-any-style?w=400&fmt=auto&qlt=80&sm=aspect&aspect=16:10&$poi$" },
  { label: "Design Services", query: "Tell me about your free design services", img: "https://i8.amplience.net/i/flooranddecor/design-services-re-galleries?w=400&fmt=auto&qlt=80&sm=aspect&aspect=16:10&$poi$" },
];

const QUICK_LINKS = [
  { label: "Shipping & Delivery", query: "What are your shipping and delivery options?" },
  { label: "Payments & Pricing", query: "What payment options do you accept?" },
  { label: "Returns", query: "What is your return policy?" },
  { label: "Workshops", query: "Tell me about your free in-store workshops" },
  { label: "Pro Services", query: "What is Floor & Decor Pro Premier?" },
];

const TRENDING = [
  "How do I install tile?",
  "What type of tile is best for a beginner DIY project?",
  "How do I clean and maintain tile floors?",
  "Show me white porcelain tiles under $5/sqft",
  "What tools do I need for tile installation?",
  "Do you offer free in-store workshops?",
  "What glass mosaic tiles do you have?",
];

// ── Completed Markdown (used after streaming ends) ─────────────────────────

function CompletedMessage({ content }: { content: string }) {
  return (
    <div className="text-[14px] leading-[1.75] text-gray-700 prose prose-sm max-w-none prose-p:my-2 prose-li:my-0.5 prose-strong:text-gray-900 prose-a:text-[#CC0000] prose-a:underline prose-headings:text-gray-900 prose-headings:text-[14px] prose-ul:my-2 prose-ol:my-2">
      <ReactMarkdown
        components={{
          a: ({ href, children }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-[#CC0000] underline hover:text-[#ff3333]">{children}</a>
          ),
        }}
      >{content}</ReactMarkdown>
    </div>
  );
}

// ── Agent Status ───────────────────────────────────────────────────────────

function AgentStatus({ status }: { status: string }) {
  return (
    <div className="flex items-center gap-2 text-[12px] text-gray-500 py-0.5">
      <div className="flex gap-0.5">
        {[0, 1, 2].map((i) => (
          <div key={i} className="w-1 h-1 bg-[#CC0000] rounded-full animate-bounce" style={{ animationDelay: `${i * 150}ms` }} />
        ))}
      </div>
      {status === "searching" ? "Searching products..." : status === "video" ? "Finding videos..." : status === "writing" ? "Writing..." : "Thinking..."}
    </div>
  );
}

// ── Main App ───────────────────────────────────────────────────────────────

export default function RoomyApp() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isStreaming, setIsStreaming] = useState(false);
  const [agentStatus, setAgentStatus] = useState<string | null>(null);
  const [chatOpen, setChatOpen] = useState(false);
  const [threadId] = useState(() =>
    typeof crypto !== "undefined" && crypto.randomUUID ? crypto.randomUUID() : Math.random().toString(36).slice(2)
  );
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const streamingContentRef = useRef("");
  const streamingElRef = useRef<HTMLDivElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages, agentStatus]);
  useEffect(() => { if (chatOpen) setTimeout(() => { chatRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); inputRef.current?.focus(); }, 350); }, [chatOpen]);
  useEffect(() => { if (inputRef.current) { inputRef.current.style.height = "auto"; inputRef.current.style.height = Math.min(inputRef.current.scrollHeight, 120) + "px"; } }, [input]);

  const sendMessage = useCallback((text: string) => {
    if (!text.trim() || isStreaming) return;
    if (!chatOpen) setChatOpen(true);
    setMessages((prev) => [...prev, { role: "user", content: text.trim() }, { role: "assistant", content: "", done: false }]);
    setInput("");
    setIsStreaming(true);
    setAgentStatus("thinking");
    streamingContentRef.current = "";

    streamChat(text.trim(), threadId,
      (token) => {
        setAgentStatus(null);
        streamingContentRef.current += token;
        if (streamingElRef.current) {
          const html = streamingContentRef.current
            .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\[([^\]]+)\]\((https?:\/\/[^)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer" class="text-[#CC0000] underline">$1</a>')
            .replace(/^[-•] (.+)/gm, '<li class="ml-4 list-disc">$1</li>')
            .replace(/^(\d+)\. (.+)/gm, '<li class="ml-4 list-decimal">$2</li>')
            .replace(/\n\n/g, '<div class="h-2"></div>')
            .replace(/\n/g, "<br/>");
          streamingElRef.current.innerHTML = html + '<span class="inline-block w-1 h-3.5 bg-[#CC0000] ml-0.5 animate-pulse rounded-sm align-middle"></span>';
          messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        }
      },
      (name) => { setAgentStatus(name === "search_tile_products" ? "searching" : name === "show_video" ? "video" : "thinking"); },
      (name, result) => {
        setAgentStatus(null);
        if (name === "search_tile_products") {
          try { const p = JSON.parse(result); if (p.results?.length) setMessages((prev) => { const u = [...prev]; const l = u[u.length - 1]; if (l?.role === "assistant") u[u.length - 1] = { ...l, tileResults: p.results }; return u; }); } catch {}
        } else if (name === "show_video") {
          try { const p = JSON.parse(result); if (p.videos?.length) setMessages((prev) => { const u = [...prev]; const l = u[u.length - 1]; if (l?.role === "assistant") u[u.length - 1] = { ...l, videoResults: p.videos }; return u; }); } catch {}
        }
      },
      () => {
        setMessages((prev) => { const u = [...prev]; const l = u[u.length - 1]; if (l?.role === "assistant") u[u.length - 1] = { ...l, content: streamingContentRef.current, done: true }; return u; });
        streamingContentRef.current = "";
        setIsStreaming(false);
        setAgentStatus(null);
      },
      (err) => {
        console.error("Chat error:", err);
        setMessages((prev) => { const u = [...prev]; const l = u[u.length - 1]; if (l?.role === "assistant") u[u.length - 1] = { ...l, content: streamingContentRef.current || "Sorry, something went wrong.", done: true }; return u; });
        streamingContentRef.current = "";
        setIsStreaming(false);
        setAgentStatus(null);
      }
    );
  }, [isStreaming, threadId, chatOpen]);

  const handleSubmit = (e: React.FormEvent) => { e.preventDefault(); sendMessage(input); };
  const handleKeyDown = (e: React.KeyboardEvent) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(input); } };

  return (
    <div className="min-h-screen bg-white">
      {/* ─── Header ──────────────────────────────────────────────── */}
      <header className="bg-white border-b border-gray-100 sticky top-0 z-20">
        <div className="max-w-[1200px] mx-auto px-8 py-3.5 flex items-center justify-between">
          <div className="flex items-center gap-5">
            <img src="/fd-logo.svg" alt="Floor & Decor" className="h-9" />
            <span className="hidden md:block text-[11px] font-semibold text-gray-400 uppercase tracking-[0.15em]">Help Center</span>
          </div>
          <nav className="hidden md:flex items-center gap-6 text-[12px] font-medium text-gray-500">
            <a href="https://www.flooranddecor.com/tile" target="_blank" rel="noreferrer" className="hover:text-gray-900 transition-colors">Tile</a>
            <a href="https://www.flooranddecor.com/installation-materials" target="_blank" rel="noreferrer" className="hover:text-gray-900 transition-colors">Installation</a>
            <a href="https://www.flooranddecor.com/design-services" target="_blank" rel="noreferrer" className="hover:text-gray-900 transition-colors">Design</a>
            <a href="https://www.flooranddecor.com/vhtc.html" target="_blank" rel="noreferrer" className="hover:text-gray-900 transition-colors">Workshops</a>
            <a href="tel:18776750002" className="flex items-center gap-1.5 text-gray-400 hover:text-gray-900 transition-colors">
              <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 6.75c0 8.284 6.716 15 15 15h2.25a2.25 2.25 0 002.25-2.25v-1.372c0-.516-.351-.966-.852-1.091l-4.423-1.106c-.44-.11-.902.055-1.173.417l-.97 1.293c-.282.376-.769.542-1.21.38a12.035 12.035 0 01-7.143-7.143c-.162-.441.004-.928.38-1.21l1.293-.97c.363-.271.527-.734.417-1.173L6.963 3.102a1.125 1.125 0 00-1.091-.852H4.5A2.25 2.25 0 002.25 4.5v2.25z" /></svg>
              1-877-675-0002
            </a>
          </nav>
        </div>
      </header>

      {/* ─── Hero ─────────────────────────────────────────────────── */}
      <section className="relative h-[320px] md:h-[380px] overflow-hidden">
        <img src="https://i8.amplience.net/i/flooranddecor/design-services-re-hero-f0?w=1920&fmt=auto&qlt=85&sm=aspect&aspect=1920:400&$poi$" alt="" className="absolute inset-0 w-full h-full object-cover" />
        <div className="absolute inset-0 bg-gradient-to-r from-black/60 via-black/30 to-transparent" />
        <div className="relative max-w-[1200px] mx-auto px-8 h-full flex items-center">
          <div className="max-w-lg">
            <h2 className="text-3xl md:text-[42px] font-black text-white leading-tight tracking-tight">
              FREE DESIGN<br />SERVICES
            </h2>
            <p className="text-gray-200 text-base md:text-lg mt-2 font-light tracking-wide">AT YOUR LOCAL FLOOR &amp; DECOR</p>
            <a
              href="https://www.flooranddecor.com/design-services"
              target="_blank"
              rel="noreferrer"
              className="mt-5 inline-block border-2 border-white text-white font-bold text-sm uppercase tracking-[0.14em] px-10 py-3 hover:bg-[#CC0000] hover:border-[#CC0000] transition-all duration-200"
            >
              Schedule Now
            </a>
          </div>
        </div>
      </section>

      {/* ─── Greeting ────────────────────────────────────────────── */}
      <section className="relative bg-[#1a1a1a] overflow-hidden">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_50%_0%,rgba(204,0,0,0.08),transparent_70%)]" />
        <div className="relative max-w-[1200px] mx-auto px-8 py-16 md:py-20 text-center">
          <h1 className="text-[32px] md:text-[44px] font-bold text-white tracking-tight leading-tight">
            How can we help you?
          </h1>
          <p className="mt-3 text-gray-400 text-[16px] md:text-[18px] max-w-xl mx-auto leading-relaxed">
            Search our help center or ask <span className="text-[#CC0000] font-semibold">Roomy</span>, your AI assistant
          </p>
          <div className="mt-8 flex items-center justify-center gap-6 text-[12px] text-gray-500">
            <span className="flex items-center gap-1.5">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 .837.46 1.58 1.155 1.951m9.345-8.334V6.637c0-1.621-1.152-3.026-2.76-3.235A48.455 48.455 0 0011.25 3c-2.115 0-4.198.137-6.24.402-1.608.209-2.76 1.614-2.76 3.235v6.226c0 1.621 1.152 3.026 2.76 3.235.577.075 1.157.14 1.74.194V21l4.155-4.155" /></svg>
              AI-powered answers
            </span>
            <span className="flex items-center gap-1.5">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M3.75 6A2.25 2.25 0 016 3.75h2.25A2.25 2.25 0 0110.5 6v2.25a2.25 2.25 0 01-2.25 2.25H6a2.25 2.25 0 01-2.25-2.25V6z" /></svg>
              1,192 products
            </span>
            <span className="flex items-center gap-1.5">
              <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z" /></svg>
              Video tutorials
            </span>
          </div>
        </div>
      </section>

      {/* ─── Category Cards ──────────────────────────────────────── */}
      <section className="bg-[#f8f8f8] border-t border-b border-gray-100">
        <div className="max-w-[1200px] mx-auto px-8 py-10">
          <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.15em] mb-5">Browse by topic</p>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
            {CATEGORIES.map((cat) => (
              <button
                key={cat.label}
                onClick={() => sendMessage(cat.query)}
                className="group text-left bg-white rounded-lg overflow-hidden border border-gray-100 hover:shadow-xl hover:shadow-gray-200/50 hover:-translate-y-0.5 transition-all duration-300"
              >
                <div className="h-[130px] overflow-hidden">
                  <img src={cat.img} alt={cat.label} className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-500" />
                </div>
                <div className="px-4 py-3.5">
                  <span className="text-[13px] font-semibold text-gray-800 group-hover:text-[#CC0000] transition-colors">{cat.label}</span>
                </div>
              </button>
            ))}
          </div>
          <div className="flex flex-wrap gap-2 mt-6 justify-center">
            {QUICK_LINKS.map((ql) => (
              <button key={ql.label} onClick={() => sendMessage(ql.query)} className="px-4 py-2 bg-white border border-gray-100 hover:border-[#CC0000]/30 hover:bg-red-50 hover:text-[#CC0000] text-gray-500 text-[12px] font-medium rounded-full transition-all shadow-sm">
                {ql.label}
              </button>
            ))}
          </div>
        </div>
      </section>

      {/* ─── Trending Questions ───────────────────────────────────── */}
      <section className="max-w-[1200px] mx-auto px-8 py-10">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-0">
          <div>
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.15em] mb-4">Popular questions</p>
            <div className="divide-y divide-gray-100">
              {TRENDING.slice(0, 4).map((q) => (
                <button key={q} onClick={() => sendMessage(q)} className="w-full flex items-center justify-between py-3.5 group text-left">
                  <span className="text-[14px] text-gray-600 group-hover:text-gray-900 transition-colors">{q}</span>
                  <svg className="w-4 h-4 text-gray-200 group-hover:text-[#CC0000] flex-shrink-0 ml-4 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </button>
              ))}
            </div>
          </div>
          <div>
            <p className="text-[11px] font-semibold text-gray-400 uppercase tracking-[0.15em] mb-4 md:invisible">More</p>
            <div className="divide-y divide-gray-100">
              {TRENDING.slice(4).map((q) => (
                <button key={q} onClick={() => sendMessage(q)} className="w-full flex items-center justify-between py-3.5 group text-left">
                  <span className="text-[14px] text-gray-600 group-hover:text-gray-900 transition-colors">{q}</span>
                  <svg className="w-4 h-4 text-gray-200 group-hover:text-[#CC0000] flex-shrink-0 ml-4 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                  </svg>
                </button>
              ))}
            </div>
          </div>
        </div>
      </section>

      {/* ─── Resources ────────────────────────────────────────────── */}
      <section className="bg-[#f8f8f8] border-t border-b border-gray-100">
        <div className="max-w-[1200px] mx-auto px-8 py-14 grid grid-cols-1 md:grid-cols-3 gap-8">
          {[
            { title: "Installation Videos", sub: "Step-by-step how-to guides", href: "https://www.flooranddecor.com/videos/v/floor-decor-workshop-how-to-install-tile-stone/227571108", cta: "Watch Now", img: "https://i8.amplience.net/i/flooranddecor/design-services-re-blogs?w=300&fmt=auto&qlt=80&sm=aspect&aspect=16:10&$poi$" },
            { title: "Free Workshops", sub: "Hands-on learning, 1st Saturday monthly", href: "https://www.flooranddecor.com/vhtc.html", cta: "Register Free", img: "https://i8.amplience.net/i/flooranddecor/inspo-center-august-catalog-2025?w=300&fmt=auto&qlt=80&sm=aspect&aspect=16:10&$poi$" },
            { title: "Design Services", sub: "Free in-store consultations", href: "https://www.flooranddecor.com/design-services", cta: "Book Now", img: "https://i8.amplience.net/i/flooranddecor/design-services-re-galleries?w=300&fmt=auto&qlt=80&sm=aspect&aspect=16:10&$poi$" },
          ].map((r) => (
            <a key={r.title} href={r.href} target="_blank" rel="noreferrer" className="group block bg-white rounded-lg overflow-hidden border border-gray-100 hover:shadow-lg hover:-translate-y-0.5 transition-all duration-300">
              <div className="h-[140px] overflow-hidden">
                <img src={r.img} alt={r.title} className="w-full h-full object-cover group-hover:scale-[1.03] transition-transform duration-500" />
              </div>
              <div className="p-4">
                <h3 className="font-semibold text-[14px] text-gray-900">{r.title}</h3>
                <p className="text-gray-400 text-[12px] mt-0.5">{r.sub}</p>
                <span className="text-[#CC0000] text-[12px] font-semibold mt-2 inline-block group-hover:underline">{r.cta} &rarr;</span>
              </div>
            </a>
          ))}
        </div>
      </section>

      {/* Spacer so footer content isn't hidden behind fixed chat bar */}
      <div className="h-20" />

      {/* ─── Fixed Bottom Chat Bar + Drawer ───────────────────────── */}
      <div ref={chatRef} className="fixed bottom-0 left-0 right-0 z-30">
        {/* Chat drawer (slides up) */}
        <div
          className="mx-auto transition-all duration-500 ease-out overflow-hidden"
          style={{
            maxWidth: "860px",
            height: chatOpen ? "520px" : "0px",
            opacity: chatOpen ? 1 : 0,
          }}
        >
          <div className="h-full flex flex-col rounded-t-2xl shadow-2xl shadow-black/20 overflow-hidden">
            {/* Dark header with red accent glow */}
            <div className="relative bg-[#1a1a1a] text-white px-5 py-3.5 flex items-center justify-between rounded-t-2xl flex-shrink-0 overflow-hidden">
              <div className="absolute inset-0 bg-[radial-gradient(circle_at_30%_50%,rgba(204,0,0,0.12),transparent_60%)] pointer-events-none" />
              <div className="relative flex items-center gap-3">
                <div className="w-8 h-8 bg-gradient-to-br from-[#CC0000] to-[#8B0000] rounded-lg flex items-center justify-center shadow-md shadow-red-900/30">
                  <span className="font-bold text-[11px]">R</span>
                </div>
                <div>
                  <p className="font-semibold text-[13px] flex items-center gap-2">
                    Roomy
                    <span className="inline-flex items-center gap-1 text-[9px] font-medium bg-white/5 border border-white/10 px-1.5 py-0.5 rounded-full text-gray-400">
                      <span className="w-1 h-1 bg-emerald-400 rounded-full animate-pulse" />
                      AI
                    </span>
                  </p>
                  <p className="text-[10px] text-gray-500">Floor &amp; Decor Help Center</p>
                </div>
              </div>
              <button onClick={() => setChatOpen(false)} className="relative w-6 h-6 rounded bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors">
                <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" /></svg>
              </button>
            </div>

            {/* Messages */}
            <div className="flex-1 min-h-0 overflow-y-auto px-5 py-4 space-y-5 bg-[#f8f8f8]">
              {messages.length === 0 && (
                <div className="text-center py-10">
                  <p className="text-[14px] text-gray-400">Ask me anything about flooring, products, or services.</p>
                </div>
              )}
              {messages.map((msg, i) => {
                const isLast = i === messages.length - 1;
                const isStreamingMsg = isLast && msg.role === "assistant" && !msg.done && isStreaming;
                return (
                  <div key={i}>
                    <div className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"} items-start`}>
                      {msg.role === "assistant" && (
                        <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-gradient-to-br from-[#CC0000] to-[#8B0000] flex items-center justify-center mr-3 mt-0.5">
                          <span className="text-white text-[10px] font-bold">R</span>
                        </div>
                      )}
                      <div className={`max-w-[80%] ${
                        msg.role === "user"
                          ? "bg-[#CC0000] text-white rounded-2xl rounded-br-sm px-4 py-2.5"
                          : ""
                      }`}>
                        {msg.role === "assistant" ? (
                          isStreamingMsg ? (
                            <>
                              {agentStatus && !streamingContentRef.current && <AgentStatus status={agentStatus} />}
                              <div ref={streamingElRef} className="text-[14px] leading-[1.75] text-gray-700" />
                            </>
                          ) : msg.content ? (
                            <CompletedMessage content={msg.content} />
                          ) : agentStatus && isLast ? (
                            <AgentStatus status={agentStatus} />
                          ) : null
                        ) : (
                          <span className="text-[14px] leading-[1.6]">{msg.content}</span>
                        )}
                      </div>
                    </div>
                    {msg.done && msg.tileResults && msg.tileResults.length > 0 && (
                      <div className="mt-3 ml-10"><TileSearchResults results={msg.tileResults} /></div>
                    )}
                    {msg.done && msg.videoResults && msg.videoResults.length > 0 && (
                      <div className="mt-3 ml-10"><VideoResults videos={msg.videoResults} /></div>
                    )}
                  </div>
                );
              })}
              <div ref={messagesEndRef} />
            </div>
          </div>
        </div>

        {/* Always-visible bottom bar — white with dark input area */}
        <div className="bg-white border-t border-gray-200 shadow-[0_-4px_20px_rgba(0,0,0,0.06)]">
          <div className="max-w-[860px] mx-auto px-5 py-3">
            <form onSubmit={handleSubmit} className="flex items-end gap-3">
              <div
                id="roomy-chat-trigger"
                className="flex items-center gap-3 flex-shrink-0 cursor-pointer"
                onClick={() => { if (!chatOpen) { setChatOpen(true); setTimeout(() => inputRef.current?.focus(), 300); } }}
              >
                <div className="w-9 h-9 bg-gradient-to-br from-[#1a1a1a] to-[#333] rounded-lg flex items-center justify-center">
                  <span className="text-white text-xs font-bold">R</span>
                </div>
              </div>
              <textarea
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                onFocus={() => { if (!chatOpen) setChatOpen(true); }}
                placeholder="Ask Roomy a question..."
                rows={1}
                disabled={isStreaming}
                className="flex-1 rounded-xl border border-white/10 bg-[#1a1a1a]/70 backdrop-blur-md px-4 py-2.5 text-[14px] text-white outline-none resize-none leading-relaxed placeholder:text-gray-400 focus:border-[#CC0000]/50 disabled:opacity-40 transition-all"
                style={{ backgroundImage: "radial-gradient(circle at 20% 50%, rgba(204,0,0,0.1), transparent 60%)" }}
              />
              <button
                type="submit"
                disabled={!input.trim() || isStreaming}
                className="flex-shrink-0 w-9 h-9 bg-gradient-to-br from-[#CC0000] to-[#8B0000] hover:from-[#dd0000] hover:to-[#990000] disabled:from-gray-200 disabled:to-gray-300 disabled:cursor-not-allowed text-white rounded-xl flex items-center justify-center transition-all"
              >
                <svg width="15" height="15" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}><path strokeLinecap="round" strokeLinejoin="round" d="M4.5 10.5L12 3m0 0l7.5 7.5M12 3v18" /></svg>
              </button>
            </form>
            <div className="flex items-center justify-center gap-5 mt-2 text-[10px] text-gray-400">
              <span className="flex items-center gap-1">
                <span className="w-1 h-1 bg-emerald-400 rounded-full animate-pulse" />
                Powered by Roomy AI
              </span>
              <span>&middot;</span>
              <a href="https://www.flooranddecor.com" target="_blank" rel="noreferrer" className="hover:text-gray-600 transition-colors">flooranddecor.com</a>
            </div>
          </div>
        </div>
      </div>

      {/* ─── Footer ───────────────────────────────────────────────── */}
      <footer className="bg-white border-t border-gray-100 text-gray-400 text-[11px]">
        <div className="max-w-[1200px] mx-auto px-8 py-6 flex flex-col md:flex-row items-center justify-between gap-3">
          <p>&copy; 2014 &ndash; 2026 Floor &amp; Decor. All rights reserved.</p>
          <div className="flex gap-6">
            <a href="https://www.flooranddecor.com/customer-care" target="_blank" rel="noreferrer" className="hover:text-gray-900 transition-colors">Contact</a>
            <a href="https://www.flooranddecor.com/return-policy.html" target="_blank" rel="noreferrer" className="hover:text-gray-900 transition-colors">Returns</a>
            <a href="https://www.flooranddecor.com/privacy-policy.html" target="_blank" rel="noreferrer" className="hover:text-gray-900 transition-colors">Privacy</a>
          </div>
        </div>
      </footer>
    </div>
  );
}
