/**
 * API Client for Backend Communication
 *
 * Uses token exchange pattern:
 * 1. Fetch backend token from /api/auth/backend-token (validates Better Auth session)
 * 2. Cache token until near expiry
 * 3. Attach token as Bearer header to all backend requests
 */

// Backend API URL - browser requests go to localhost
const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

interface FetchOptions extends RequestInit {
  skipAuth?: boolean;
}

// Token cache
let cachedToken: string | null = null;
let tokenExpiry: number = 0;

/**
 * Get or refresh the backend token.
 * Caches token until 1 minute before expiry.
 */
async function getBackendToken(): Promise<string | null> {
  const now = Date.now();
  const bufferMs = 60 * 1000; // Refresh 1 minute before expiry

  // Return cached token if still valid
  if (cachedToken && tokenExpiry > now + bufferMs) {
    return cachedToken;
  }

  try {
    // Fetch new token from exchange endpoint
    const response = await fetch("/api/auth/backend-token", {
      credentials: "include", // Include Better Auth session cookie
    });

    if (!response.ok) {
      if (response.status === 401) {
        // Not authenticated - clear cache and return null
        cachedToken = null;
        tokenExpiry = 0;
        return null;
      }
      throw new Error(`Token exchange failed: ${response.status}`);
    }

    const data = await response.json();

    // Cache the token
    cachedToken = data.token;
    tokenExpiry = now + (data.expiresIn * 1000);

    return cachedToken;
  } catch (error) {
    console.error("Failed to get backend token:", error);
    return null;
  }
}

/**
 * Clear the token cache (call on logout).
 */
export function clearTokenCache(): void {
  cachedToken = null;
  tokenExpiry = 0;
}

/**
 * Fetch wrapper that attaches authentication token.
 */
export async function fetchWithAuth(
  endpoint: string,
  options: FetchOptions = {}
): Promise<Response> {
  const { skipAuth = false, headers: customHeaders, ...restOptions } = options;

  const headers = new Headers(customHeaders);

  if (!skipAuth) {
    const token = await getBackendToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
    }
  }

  // Always set JSON content type for API requests
  if (!headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const url = endpoint.startsWith("/") ? `${API_URL}${endpoint}` : endpoint;

  return fetch(url, {
    ...restOptions,
    headers,
  });
}

/**
 * API client with convenience methods.
 */
export const apiClient = {
  async get<T>(endpoint: string, options?: FetchOptions): Promise<T> {
    const response = await fetchWithAuth(endpoint, { ...options, method: "GET" });

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  },

  async post<T>(endpoint: string, data?: unknown, options?: FetchOptions): Promise<T> {
    const response = await fetchWithAuth(endpoint, {
      ...options,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    });

    if (!response.ok) {
      throw new ApiError(response.status, await response.text());
    }

    return response.json();
  },
};

class ApiError extends Error {
  constructor(public status: number, public body: string) {
    super(`API Error ${status}: ${body}`);
    this.name = "ApiError";
  }
}

export { ApiError };
