import { auth } from "../lib/auth";

// Initialize Better Auth database schema
// Better Auth uses an ORM-like approach and auto-creates tables on first API call
async function initDatabase() {
  try {
    console.log("Initializing Better Auth database schema...");

    // Trigger schema creation by making an API call
    // This will auto-create all necessary tables
    await auth.api.listSessions({ headers: new Headers() });

    console.log("✓ Database schema initialized successfully");
    process.exit(0);
  } catch (error) {
    console.error("✗ Database initialization failed:", error);
    process.exit(1);
  }
}

initDatabase();
