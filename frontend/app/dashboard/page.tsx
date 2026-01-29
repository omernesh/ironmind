"use client";

import { useSession, signOut } from "@/lib/auth-client";
import { apiClient, clearTokenCache } from "@/lib/api-client";
import { useRouter } from "next/navigation";
import { useEffect, useState, useCallback } from "react";
import { DocumentUpload } from "./components/DocumentUpload";
import { DocumentList } from "./components/DocumentList";

const MAX_DOCUMENTS = 10;
const POLL_INTERVAL = 3000; // 3 seconds

interface Document {
  doc_id: string;
  filename: string;
  status: string;
  file_type: string;
  created_at: string;
  page_count?: number;
  chunk_count?: number;
  error?: string;
}

export default function DashboardPage() {
  const { data: session, isPending } = useSession();
  const router = useRouter();
  const [documents, setDocuments] = useState<Document[]>([]);
  const [loading, setLoading] = useState(true);

  // Fetch documents
  const fetchDocuments = useCallback(async () => {
    try {
      const docs = await apiClient.get<Document[]>("/api/documents");
      setDocuments(docs);
    } catch (error) {
      console.error("Failed to fetch documents:", error);
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch and polling for processing documents
  useEffect(() => {
    if (session) {
      fetchDocuments();

      // Poll while any document is processing
      const interval = setInterval(() => {
        const hasProcessing = documents.some(d =>
          !["Done", "Failed"].includes(d.status)
        );
        if (hasProcessing) {
          fetchDocuments();
        }
      }, POLL_INTERVAL);

      return () => clearInterval(interval);
    }
  }, [session, fetchDocuments, documents]);

  // Auth redirect
  useEffect(() => {
    if (!isPending && !session) {
      router.push("/login");
    }
  }, [session, isPending, router]);

  const handleSignOut = async () => {
    clearTokenCache();
    await signOut();
    router.push("/");
  };

  const handleDelete = (docId: string) => {
    setDocuments(prev => prev.filter(d => d.doc_id !== docId));
  };

  const indexedCount = documents.filter(d => d.status === "Done").length;

  if (isPending || !session) {
    return <div className="min-h-screen flex items-center justify-center">Loading...</div>;
  }

  return (
    <main className="max-w-4xl mx-auto p-6">
      {/* Header */}
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-2xl font-bold">Documents</h1>
          <p className="text-gray-600">
            {documents.length} of {MAX_DOCUMENTS} documents · {indexedCount} indexed
          </p>
        </div>
        <div className="flex gap-3">
          {indexedCount > 0 && (
            <button
              onClick={() => router.push("/chat")}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
            >
              Start Chatting
            </button>
          )}
          <button
            onClick={handleSignOut}
            className="px-4 py-2 text-gray-600 hover:text-gray-900"
          >
            Sign Out
          </button>
        </div>
      </div>

      {/* Upload Section */}
      <div className="mb-8">
        <h2 className="text-lg font-semibold mb-3">Upload Documents</h2>
        <DocumentUpload
          onUploadComplete={fetchDocuments}
          documentCount={documents.length}
          maxDocuments={MAX_DOCUMENTS}
        />
      </div>

      {/* Document List */}
      <div>
        <h2 className="text-lg font-semibold mb-3">Your Documents</h2>
        {loading ? (
          <div className="text-center py-8 text-gray-500">Loading...</div>
        ) : (
          <DocumentList
            documents={documents}
            onRefresh={fetchDocuments}
            onDelete={handleDelete}
          />
        )}
      </div>
    </main>
  );
}
