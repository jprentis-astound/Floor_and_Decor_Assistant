"use client";

import { CopilotSidebar } from "@copilotkit/react-ui";
import { useRoomyWidgets } from "@/components/RoomyWidgets";

function RoomySidebar() {
  // Register tile product widgets — intercepts tool call results
  useRoomyWidgets();

  return (
    <CopilotSidebar
      defaultOpen={true}
      clickOutsideToClose={false}
      labels={{
        title: "Roomy — Floor & Decor",
        initial:
          'Hi! I\'m Roomy \ud83c\udfe0 Your Floor & Decor tile assistant.\n\nAsk me anything \u2014 try:\n\u2022 "Show me white porcelain tiles under $5"\n\u2022 "What glass mosaic tiles do you have?"\n\u2022 "Find matte subway tiles"',
        placeholder: "Search for tiles or ask a question...",
      }}
    >
      <MainContent />
    </CopilotSidebar>
  );
}

function MainContent() {
  return (
    <main className="min-h-screen bg-gray-50">
      <div className="bg-[#1B5E20] text-white">
        <div className="max-w-5xl mx-auto px-6 py-16">
          <h1 className="text-4xl font-bold tracking-tight">Floor & Decor</h1>
          <p className="mt-3 text-lg text-green-100 max-w-xl">
            Find the perfect tile for your project. Use the Roomy assistant to
            search our catalog of 1,192 tiles by style, color, material, and
            price.
          </p>
          <div className="mt-6 flex gap-3">
            {["Porcelain", "Ceramic", "Glass", "866+ styles"].map((tag) => (
              <span key={tag} className="bg-white/20 text-sm px-3 py-1 rounded-full">
                {tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-12">
        <h2 className="text-xl font-semibold text-gray-800 mb-6">
          Try asking Roomy...
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[
            { q: "Show me white porcelain tiles under $5/sqft", desc: "Filter by material, color, and price" },
            { q: "What glass mosaic tiles do you have?", desc: "Browse by material and style" },
            { q: "Find polished tiles from Maximo", desc: "Search by finish and brand" },
          ].map((example) => (
            <div key={example.q} className="bg-white rounded-xl border border-gray-200 p-4 hover:shadow-md transition-shadow">
              <p className="text-sm font-medium text-gray-900">&ldquo;{example.q}&rdquo;</p>
              <p className="text-xs text-gray-500 mt-2">{example.desc}</p>
            </div>
          ))}
        </div>

        <div className="mt-12 grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { label: "Tile Products", value: "1,192" },
            { label: "Brands", value: "40+" },
            { label: "Price Range", value: "$0.29 \u2013 $94.99" },
            { label: "Materials", value: "3 Types" },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <p className="text-2xl font-bold text-[#1B5E20]">{stat.value}</p>
              <p className="text-xs text-gray-500 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </main>
  );
}

export default function RoomyApp() {
  return <RoomySidebar />;
}
