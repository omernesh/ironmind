"use client";

import { useState } from "react";

interface Citation {
  id: number;
  doc_id: string;
  filename: string;
  page_range: string;
  section_title?: string;
  snippet: string;
  score?: number;
  source: "document" | "graph";
  multi_source?: boolean;
}

interface CitationCardProps {
  citation: Citation;
  isExpanded: boolean;
  onToggle: () => void;
}

export function CitationCard({ citation, isExpanded, onToggle }: CitationCardProps) {
  return (
    <div className="border rounded-lg overflow-hidden">
      {/* Header - always visible */}
      <button
        onClick={onToggle}
        className="w-full px-3 py-2 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors text-left"
      >
        <div className="flex items-center gap-2 min-w-0">
          <span className="flex-shrink-0 w-6 h-6 bg-blue-600 text-white text-xs rounded-full flex items-center justify-center font-medium">
            {citation.id}
          </span>
          <span className="truncate font-medium text-sm">{citation.filename}</span>
          <span className="text-xs text-gray-500 flex-shrink-0">p.{citation.page_range}</span>
          {citation.source === "graph" && (
            <span className="text-xs bg-purple-100 text-purple-700 px-1.5 py-0.5 rounded">
              Graph
            </span>
          )}
        </div>
        <svg
          className={`w-4 h-4 text-gray-400 transition-transform ${isExpanded ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Expanded content */}
      {isExpanded && (
        <div className="px-3 py-2 border-t bg-white">
          {citation.section_title && (
            <p className="text-xs text-gray-500 mb-1">
              Section: {citation.section_title}
            </p>
          )}
          <p className="text-sm text-gray-700 leading-relaxed">
            "{citation.snippet}"
          </p>
          {citation.multi_source && (
            <p className="text-xs text-blue-600 mt-2">
              Part of multi-source synthesis
            </p>
          )}
        </div>
      )}
    </div>
  );
}

interface CitationListProps {
  citations: Citation[];
}

export function CitationList({ citations }: CitationListProps) {
  const [expandedId, setExpandedId] = useState<number | null>(null);

  if (citations.length === 0) return null;

  return (
    <div className="mt-4 space-y-2">
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">
        Sources ({citations.length})
      </p>
      <div className="space-y-2">
        {citations.map(citation => (
          <CitationCard
            key={citation.id}
            citation={citation}
            isExpanded={expandedId === citation.id}
            onToggle={() => setExpandedId(expandedId === citation.id ? null : citation.id)}
          />
        ))}
      </div>
    </div>
  );
}

// Inline citation marker component
export function CitationMarker({ id, onClick }: { id: number; onClick?: () => void }) {
  return (
    <button
      onClick={onClick}
      className="inline-flex items-center justify-center w-5 h-5 bg-blue-100 text-blue-700 text-xs rounded-full hover:bg-blue-200 font-medium mx-0.5"
      title={`View source ${id}`}
    >
      {id}
    </button>
  );
}
