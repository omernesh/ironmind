"use client";

import { useSession, signOut } from "@/lib/auth-client";
import { apiClient, ApiError, clearTokenCache } from "@/lib/api-client";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

interface ProtectedResponse {
  message: string;
  user_id: string;
}

export default function DashboardPage() {
  const { data: session, isPending } = useSession();
  const router = useRouter();
  const [backendResponse, setBackendResponse] = useState<ProtectedResponse | null>(null);
  const [backendError, setBackendError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isPending && !session) {
      router.push("/login");
    }
  }, [session, isPending, router]);

  // Test backend integration
  const testBackendAuth = async () => {
    setLoading(true);
    setBackendError(null);
    setBackendResponse(null);

    try {
      const response = await apiClient.get<ProtectedResponse>("/api/protected");
      setBackendResponse(response);
    } catch (error) {
      if (error instanceof ApiError) {
        setBackendError(`Backend returned ${error.status}: ${error.body}`);
      } else {
        setBackendError("Failed to connect to backend");
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSignOut = async () => {
    clearTokenCache(); // Clear backend token cache
    await signOut();
    router.push("/");
  };

  if (isPending) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-lg">Loading...</div>
      </div>
    );
  }

  if (!session) {
    return null;
  }

  return (
    <main className="p-8 max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">IRONMIND Dashboard</h1>

      {/* Session Info */}
      <div className="bg-gray-50 rounded-lg p-4 mb-6">
        <h2 className="font-semibold mb-2">Session Info</h2>
        <p className="text-sm">
          <span className="text-gray-600">Name:</span> {session.user.name || "Not set"}
        </p>
        <p className="text-sm">
          <span className="text-gray-600">Email:</span> {session.user.email}
        </p>
        <p className="text-sm">
          <span className="text-gray-600">User ID:</span>{" "}
          <code className="bg-gray-200 px-1 rounded">{session.user.id}</code>
        </p>
      </div>

      {/* Backend Integration Test */}
      <div className="bg-blue-50 rounded-lg p-4 mb-6">
        <h2 className="font-semibold mb-2">Backend Integration</h2>
        <button
          onClick={testBackendAuth}
          disabled={loading}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
        >
          {loading ? "Testing..." : "Test Protected Endpoint"}
        </button>

        {backendResponse && (
          <div className="mt-4 p-3 bg-green-100 border border-green-400 rounded">
            <p className="text-green-700 font-medium">Backend Auth Working!</p>
            <p className="text-sm">
              Backend user_id: <code>{backendResponse.user_id}</code>
            </p>
            <p className="text-sm text-gray-600">{backendResponse.message}</p>
          </div>
        )}

        {backendError && (
          <div className="mt-4 p-3 bg-red-100 border border-red-400 rounded">
            <p className="text-red-700 font-medium">Backend Auth Failed</p>
            <p className="text-sm">{backendError}</p>
          </div>
        )}
      </div>

      {/* Sign Out */}
      <button
        onClick={handleSignOut}
        className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"
      >
        Sign Out
      </button>
    </main>
  );
}
