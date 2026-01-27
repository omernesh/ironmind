import { NextRequest, NextResponse } from "next/server";
import { auth } from "@/lib/auth";
import { headers } from "next/headers";
import { SignJWT } from "jose";

/**
 * Token Exchange Endpoint
 *
 * Converts a valid Better Auth session into a JWT token that the backend can validate.
 *
 * Flow:
 * 1. Client calls this endpoint with Better Auth session cookie
 * 2. We validate the session server-side via Better Auth
 * 3. We create a JWT with the user's ID using the shared secret
 * 4. Client uses this JWT for backend API calls
 *
 * Security:
 * - JWT uses same secret as backend (BETTER_AUTH_SECRET = JWT_SECRET_KEY)
 * - JWT expires in 15 minutes (short-lived for security)
 * - User must have valid Better Auth session to get a backend token
 */

export async function GET(request: NextRequest) {
  try {
    // Get the current session from Better Auth
    const session = await auth.api.getSession({
      headers: await headers(),
    });

    if (!session || !session.user) {
      return NextResponse.json(
        { error: "Not authenticated" },
        { status: 401 }
      );
    }

    // Get shared secret from environment
    const secret = process.env.BETTER_AUTH_SECRET;
    if (!secret) {
      console.error("BETTER_AUTH_SECRET not configured");
      return NextResponse.json(
        { error: "Server configuration error" },
        { status: 500 }
      );
    }

    // Create JWT for backend using jose library
    // Must match backend expectations:
    // - Algorithm: HS256
    // - Claim: "sub" contains user_id
    const secretKey = new TextEncoder().encode(secret);

    const token = await new SignJWT({ sub: session.user.id })
      .setProtectedHeader({ alg: "HS256" })
      .setIssuedAt()
      .setExpirationTime("15m")  // Short-lived token
      .sign(secretKey);

    return NextResponse.json({
      token,
      expiresIn: 900,  // 15 minutes in seconds
      userId: session.user.id,
    });
  } catch (error) {
    console.error("Token exchange error:", error);
    return NextResponse.json(
      { error: "Token exchange failed" },
      { status: 500 }
    );
  }
}
