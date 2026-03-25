"use client";

export interface TileResult {
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

export function TileProductCard({ tile }: { tile: TileResult }) {
  return (
    <div className="rounded-xl border border-gray-200 overflow-hidden shadow-sm bg-white w-[280px] flex-shrink-0">
      <div className="relative h-36 bg-gray-100 overflow-hidden">
        {tile.image_url ? (
          <img
            src={tile.image_url}
            alt={tile.name}
            className="w-full h-full object-cover"
            loading="lazy"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-gray-400">
            <svg width="40" height="40" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </div>
        )}
        <span className="absolute top-2 left-2 bg-black/70 text-white text-[10px] font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide">
          {tile.material}
        </span>
      </div>
      <div className="p-3">
        <p className="font-semibold text-sm text-gray-900 leading-tight">{tile.name}</p>
        <p className="text-xs text-gray-500 mt-1">
          {tile.brand}{tile.finish ? ` · ${tile.finish}` : ""}{tile.size ? ` · ${tile.size}` : ""}
        </p>
        <div className="flex items-baseline gap-2 mt-2">
          <span className="text-lg font-bold text-gray-900">{tile.price_sqft}</span>
          <span className="text-xs text-gray-500">/sq ft</span>
        </div>
        <a
          href={tile.product_url}
          target="_blank"
          rel="noreferrer"
          className="mt-2.5 block text-center bg-[#CC0000] text-white text-xs font-semibold px-4 py-2 rounded-full hover:bg-[#aa0000] transition-colors"
        >
          View Product
        </a>
      </div>
    </div>
  );
}

export function TileSearchResults({ results }: { results: TileResult[] }) {
  if (!results.length) return null;
  return (
    <div className="flex gap-3 overflow-x-auto py-2 px-1 -mx-1 scrollbar-thin">
      {results.map((tile, i) => (
        <TileProductCard key={i} tile={tile} />
      ))}
    </div>
  );
}

// ── Video Card with Inline Player ──────────────────────────────────────────

import { useState } from "react";

export interface VideoResult {
  title: string;
  video_url: string;
  poster: string;
  duration: string;
  page_url: string;
}

function VideoCard({ video }: { video: VideoResult }) {
  const [playing, setPlaying] = useState(false);
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      className={`rounded-xl border border-gray-200 overflow-hidden bg-white flex-shrink-0 transition-all duration-300 ${
        expanded ? "w-full max-w-[540px] shadow-lg" : "w-[320px] shadow-sm"
      }`}
    >
      {/* Video area */}
      <div className={`relative bg-[#111] overflow-hidden transition-all duration-300 ${expanded ? "aspect-video" : "h-[180px]"}`}>
        {playing ? (
          <video
            src={video.video_url}
            poster={video.poster}
            controls
            autoPlay
            className="w-full h-full object-contain bg-black"
          />
        ) : (
          <button
            onClick={() => setPlaying(true)}
            className="w-full h-full relative group cursor-pointer"
          >
            <img
              src={video.poster}
              alt={video.title}
              className="w-full h-full object-cover group-hover:scale-[1.02] transition-transform duration-500"
              loading="lazy"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/50 via-transparent to-transparent" />
            {/* Play button */}
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="w-14 h-14 bg-white/95 rounded-full flex items-center justify-center shadow-xl group-hover:scale-110 transition-transform duration-200">
                <svg width="20" height="20" fill="#CC0000" viewBox="0 0 24 24" className="ml-1">
                  <path d="M8 5.14v14l11-7-11-7z" />
                </svg>
              </div>
            </div>
            {/* Badge */}
            <div className="absolute bottom-3 left-3 flex items-center gap-1.5">
              <span className="bg-[#CC0000] text-white text-[10px] font-semibold px-2 py-0.5 rounded">
                {video.duration}
              </span>
            </div>
          </button>
        )}
      </div>

      {/* Info bar */}
      <div className="px-3.5 py-2.5 flex items-center justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-[13px] text-gray-900 leading-snug truncate">{video.title}</p>
          <p className="text-[10px] text-gray-400 mt-0.5">Floor &amp; Decor Workshop</p>
        </div>
        <div className="flex items-center gap-1.5 flex-shrink-0">
          <button
            onClick={() => setExpanded(!expanded)}
            className="w-7 h-7 rounded-md bg-gray-50 hover:bg-gray-100 flex items-center justify-center transition-colors border border-gray-100"
            title={expanded ? "Collapse" : "Expand"}
          >
            {expanded ? (
              <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="#666" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 9V4.5M9 9H4.5M9 9L3.75 3.75M15 15h4.5M15 15v4.5m0-4.5l5.25 5.25" />
              </svg>
            ) : (
              <svg width="13" height="13" fill="none" viewBox="0 0 24 24" stroke="#666" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 3.75v4.5m0-4.5h4.5m-4.5 0L9 9m11.25 11.25v-4.5m0 4.5h-4.5m4.5 0L15 15" />
              </svg>
            )}
          </button>
          <a
            href={video.page_url}
            target="_blank"
            rel="noreferrer"
            className="w-7 h-7 rounded-md bg-gray-50 hover:bg-gray-100 flex items-center justify-center transition-colors border border-gray-100"
            title="Open on flooranddecor.com"
          >
            <svg width="12" height="12" fill="none" viewBox="0 0 24 24" stroke="#666" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-10.5 6L21 3m0 0h-5.25M21 3v5.25" />
            </svg>
          </a>
        </div>
      </div>
    </div>
  );
}

export function VideoResults({ videos }: { videos: VideoResult[] }) {
  if (!videos.length) return null;
  return (
    <div className="flex gap-3 overflow-x-auto py-2 px-1 -mx-1 scrollbar-thin">
      {videos.map((v, i) => (
        <VideoCard key={i} video={v} />
      ))}
    </div>
  );
}
