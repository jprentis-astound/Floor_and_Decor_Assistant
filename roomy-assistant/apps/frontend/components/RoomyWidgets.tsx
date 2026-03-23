"use client";
import { useRenderToolCall } from "@copilotkit/react-core";

// ── Tile Product Card Widget ─────────────────────────────────────────────────

interface TileResult {
  name: string;
  brand: string;
  material: string;
  finish: string;
  color: string;
  size: string;
  price_sqft: string;
  price_box: string;
  image_url: string;
  product_url: string;
}

interface SearchPayload {
  results: TileResult[];
  count: number;
}

function TileProductCard({ tile }: { tile: TileResult }) {
  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden shadow-sm bg-white w-[340px] flex-shrink-0">
      {/* Tile Image */}
      <div className="relative h-40 bg-gray-100 overflow-hidden">
        {tile.image_url ? (
          <img
            src={tile.image_url}
            alt={tile.name}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <svg width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        )}
        {/* Material badge */}
        <span className="absolute top-2 left-2 bg-black/70 text-white text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide">
          {tile.material}
        </span>
      </div>

      {/* Product Info */}
      <div className="p-3">
        <p className="font-semibold text-sm text-gray-900 leading-tight">{tile.name}</p>
        <p className="text-xs text-gray-500 mt-1">
          {tile.brand}
          {tile.finish ? ` · ${tile.finish}` : ""}
          {tile.size ? ` · ${tile.size}` : ""}
        </p>

        {/* Pricing */}
        <div className="flex items-baseline gap-2 mt-2">
          <span className="text-lg font-bold text-gray-900">{tile.price_sqft}</span>
          <span className="text-xs text-gray-500">/sq ft</span>
          {tile.price_box && tile.price_box !== "N/A" && (
            <span className="text-xs text-gray-400 ml-auto">{tile.price_box}/box</span>
          )}
        </div>

        {/* CTA */}
        <a
          href={tile.product_url}
          target="_blank"
          rel="noreferrer"
          className="mt-3 block text-center bg-[#CC0000] text-white text-xs font-semibold px-4 py-2 rounded-full hover:bg-[#aa0000] transition-colors"
        >
          View Product
        </a>
      </div>
    </div>
  );
}

function ToolLoading({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 py-3 px-4 text-sm text-gray-500">
      <div className="animate-spin h-4 w-4 border-2 border-gray-300 border-t-[#1B5E20] rounded-full" />
      {label}
    </div>
  );
}

// ── Hook: register Roomy widgets via useRenderToolCall ──────────────────────

export function useRoomyWidgets() {
  useRenderToolCall({
    name: "search_tile_products",
    render: ({ status, result }) => {
      if (status !== "complete") {
        return <ToolLoading label="Searching tiles..." />;
      }

      // Parse the tool result
      let payload: SearchPayload;
      try {
        payload = typeof result === "string" ? JSON.parse(result) : result;
      } catch {
        return <></>;
      }

      if (!payload?.results?.length) {
        return (
          <div className="py-2 px-4 text-sm text-gray-500 italic">
            No tiles found matching your search.
          </div>
        );
      }

      return (
        <div className="flex gap-3 overflow-x-auto py-2 px-1 -mx-1">
          {payload.results.map((tile, i) => (
            <TileProductCard key={i} tile={tile} />
          ))}
        </div>
      );
    },
  });

  useRenderToolCall({
    name: "get_tile_filters",
    render: ({ status, result }) => {
      if (status !== "complete") {
        return <ToolLoading label="Loading filter options..." />;
      }

      let filters: { materials: string[]; finishes: string[]; brands: string[]; price_min: number; price_max: number };
      try {
        filters = typeof result === "string" ? JSON.parse(result) : result;
      } catch {
        return <></>;
      }

      return (
        <div className="bg-gray-50 rounded-xl border border-gray-200 p-4 my-2 text-sm">
          <p className="font-semibold text-gray-900 mb-2">Available Filters</p>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Materials</p>
              <div className="flex flex-wrap gap-1">
                {filters.materials.map((m) => (
                  <span key={m} className="bg-white border px-2 py-0.5 rounded text-xs">{m}</span>
                ))}
              </div>
            </div>
            <div>
              <p className="text-xs font-medium text-gray-500 mb-1">Finishes</p>
              <div className="flex flex-wrap gap-1">
                {filters.finishes.map((f) => (
                  <span key={f} className="bg-white border px-2 py-0.5 rounded text-xs">{f}</span>
                ))}
              </div>
            </div>
          </div>
          <p className="text-xs text-gray-400 mt-2">
            Price range: ${filters.price_min?.toFixed(2)} – ${filters.price_max?.toFixed(2)} /sq ft
          </p>
        </div>
      );
    },
  });
}
