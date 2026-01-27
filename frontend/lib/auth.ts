import { betterAuth } from "better-auth";
import Database from "better-sqlite3";

export const auth = betterAuth({
  database: new Database(process.env.DATABASE_PATH || "./auth.db"),  // SQLite for POC simplicity
  emailAndPassword: {
    enabled: true,
    requireEmailVerification: false,  // Disable for POC speed
    minPasswordLength: 8,
  },
  session: {
    expiresIn: 60 * 60 * 24 * 7,  // 7 days
    updateAge: 60 * 60 * 24,  // Update session every 24 hours
    cookieCache: {
      enabled: true,
      maxAge: 60 * 5,  // 5 minute cookie cache
    },
  },
  trustedOrigins: [
    process.env.NEXT_PUBLIC_APP_URL || "http://localhost:3000",
  ],
});
