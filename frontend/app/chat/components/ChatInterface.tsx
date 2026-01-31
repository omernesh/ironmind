"use client";

import { useState, useRef, useEffect } from "react";
import { apiClient, ApiError } from "@/lib/api-client";
import { CitationList } from "./CitationCard";

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

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations?: Citation[];
  synthesis_mode?: boolean;
  source_doc_count?: number;
}

interface ChatResponse {
  answer: string;
  citations: Citation[];
  request_id: string;
  synthesis_mode: boolean;
  source_doc_count: number;
  diagnostics?: {
    total_latency_ms: number;
  };
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: "user",
      content: input.trim(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);
    setError(null);

    try {
      // Build conversation history for context
      const history = messages.slice(-10).map(m => ({
        role: m.role,
        content: m.content,
      }));

      const response = await apiClient.post<ChatResponse>("/api/chat", {
        question: userMessage.content,
        user_id: "current", // Backend extracts from auth token
        history,
      });

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: "assistant",
        content: response.answer,
        citations: response.citations,
        synthesis_mode: response.synthesis_mode,
        source_doc_count: response.source_doc_count,
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (err) {
      const message = err instanceof ApiError
        ? getErrorMessage(err.status)
        : "Failed to get response. Please try again.";
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <EmptyState />
        ) : (
          messages.map(message => (
            <MessageBubble key={message.id} message={message} />
          ))
        )}

        {isLoading && <LoadingIndicator />}

        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <form onSubmit={handleSubmit} className="border-t p-4 bg-white">
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question about your documents..."
            className="flex-1 border rounded-lg px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 placeholder:text-gray-500"
            aria-label="Chat message input"
            disabled={isLoading}
            maxLength={2000}
          />
          <button
            type="submit"
            disabled={isLoading || !input.trim()}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isLoading ? "..." : "Send"}
          </button>
        </div>
        <p className="text-xs text-gray-400 mt-1">
          {input.length}/2000 characters
        </p>
      </form>
    </div>
  );
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-[85%] rounded-lg p-4 ${
          isUser
            ? "bg-blue-600 text-white"
            : "bg-gray-100 text-gray-900"
        }`}
      >
        {/* Message content with citation markers rendered inline */}
        <div className="prose prose-sm max-w-none">
          {isUser ? (
            message.content
          ) : (
            <AnswerWithCitations content={message.content} />
          )}
        </div>

        {/* Synthesis indicator */}
        {message.synthesis_mode && (
          <p className="text-xs text-blue-600 mt-2 flex items-center gap-1">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path d="M9 2a1 1 0 000 2h2a1 1 0 100-2H9z" />
              <path fillRule="evenodd" d="M4 5a2 2 0 012-2 3 3 0 003 3h2a3 3 0 003-3 2 2 0 012 2v11a2 2 0 01-2 2H6a2 2 0 01-2-2V5zm3 4a1 1 0 000 2h.01a1 1 0 100-2H7zm3 0a1 1 0 000 2h3a1 1 0 100-2h-3zm-3 4a1 1 0 100 2h.01a1 1 0 100-2H7zm3 0a1 1 0 100 2h3a1 1 0 100-2h-3z" clipRule="evenodd" />
            </svg>
            Multi-source synthesis from {message.source_doc_count} documents
          </p>
        )}

        {/* Citations */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <CitationList citations={message.citations} />
        )}
      </div>
    </div>
  );
}

function AnswerWithCitations({ content }: { content: string }) {
  // Render citation markers like [1], [2] as styled badges
  const parts = content.split(/(\[\d+(?:-\d+)?\])/g);

  return (
    <span>
      {parts.map((part, index) => {
        const match = part.match(/^\[(\d+(?:-\d+)?)\]$/);
        if (match) {
          return (
            <span
              key={index}
              className="inline-flex items-center justify-center min-w-[1.25rem] h-5 px-1 bg-blue-100 text-blue-700 text-xs rounded font-medium mx-0.5"
            >
              {match[1]}
            </span>
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </span>
  );
}

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full text-center text-gray-500">
      <svg className="w-16 h-16 mb-4 text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
      </svg>
      <h3 className="text-lg font-medium text-gray-700">Ask a question</h3>
      <p className="mt-1 max-w-sm">
        Ask questions about your uploaded documents. I'll provide answers with source citations.
      </p>
      <div className="mt-4 text-sm text-gray-400">
        Try: "What are the main components described in the documents?"
      </div>
    </div>
  );
}

function LoadingIndicator() {
  return (
    <div className="flex justify-start">
      <div className="bg-gray-100 rounded-lg p-4">
        <div className="flex space-x-2">
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
          <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
        </div>
      </div>
    </div>
  );
}

function getErrorMessage(status: number): string {
  const messages: Record<number, string> = {
    400: "Invalid question. Please try rephrasing.",
    401: "Session expired. Please log in again.",
    404: "No documents found. Please upload documents first.",
    500: "Server error. Please try again later.",
  };
  return messages[status] || "Something went wrong. Please try again.";
}
