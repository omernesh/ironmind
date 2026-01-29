"use client";

import { useState } from "react";
import { apiClient, ApiError } from "@/lib/api-client";

interface Document {
  doc_id: string;
  filename: string;
  status: string;  // "Uploading" | "Parsing" | "Chunking" | "Indexing" | "Done" | "Failed"
  file_type: string;
  created_at: string;
  page_count?: number;
  chunk_count?: number;
  error?: string;
}

interface DocumentListProps {
  documents: Document[];
  onRefresh: () => void;
  onDelete: (docId: string) => void;
}

export function DocumentList({ documents, onRefresh, onDelete }: DocumentListProps) {
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const handleDelete = async (docId: string, filename: string) => {
    if (!confirm(`Delete "${filename}"? This cannot be undone.`)) return;

    setDeletingId(docId);
    try {
      await apiClient.delete(`/api/documents/${docId}`);
      onDelete(docId);
    } catch (error) {
      alert("Failed to delete document. Please try again.");
    } finally {
      setDeletingId(null);
    }
  };

  if (documents.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        <p>No documents uploaded yet.</p>
        <p className="text-sm mt-1">Upload your first document to get started.</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {documents.map(doc => (
        <div
          key={doc.doc_id}
          className="border rounded-lg p-4 flex items-center justify-between hover:bg-gray-50"
        >
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-3">
              <FileIcon type={doc.file_type} />
              <div className="min-w-0">
                <p className="font-medium truncate">{doc.filename}</p>
                <p className="text-sm text-gray-500">
                  {doc.page_count ? `${doc.page_count} pages` : ""}
                  {doc.page_count && doc.chunk_count ? " · " : ""}
                  {doc.chunk_count ? `${doc.chunk_count} chunks` : ""}
                  {!doc.page_count && !doc.chunk_count && formatDate(doc.created_at)}
                </p>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-3 ml-4">
            <StatusBadge status={doc.status} error={doc.error} />
            <button
              onClick={() => handleDelete(doc.doc_id, doc.filename)}
              disabled={deletingId === doc.doc_id}
              className="p-1 text-gray-400 hover:text-red-600 disabled:opacity-50"
              title="Delete document"
            >
              {deletingId === doc.doc_id ? (
                <span className="animate-spin">...</span>
              ) : (
                <TrashIcon />
              )}
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

function StatusBadge({ status, error }: { status: string; error?: string }) {
  // Map internal status to display status (INGEST-10)
  let displayStatus = status;
  if (["Uploading", "Parsing", "Chunking", "Indexing", "GraphExtracting", "DocumentRelationships"].includes(status)) {
    displayStatus = "Processing";
  } else if (status === "Done") {
    displayStatus = "Indexed";
  }

  const config: Record<string, { label: string; className: string }> = {
    Processing: { label: "Processing", className: "bg-yellow-100 text-yellow-800" },
    Indexed: { label: "Indexed", className: "bg-green-100 text-green-800" },
    Failed: { label: "Failed", className: "bg-red-100 text-red-800" },
  };

  const { label, className } = config[displayStatus] || config.Processing;

  return (
    <span
      className={`px-2 py-1 text-xs rounded font-medium ${className}`}
      title={error || `Status: ${status}`}
    >
      {label}
    </span>
  );
}

function FileIcon({ type }: { type: string }) {
  const color = type === "pdf" ? "text-red-500" : "text-blue-500";
  return (
    <svg className={`h-8 w-8 ${color}`} fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd" />
    </svg>
  );
}

function TrashIcon() {
  return (
    <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
    </svg>
  );
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}
