import Database from "better-sqlite3";

const dbPath = process.env.DATABASE_PATH || "./auth.db";
const db = new Database(dbPath);

// Enable WAL mode
db.pragma('journal_mode = WAL');

console.log("Creating Better Auth schema...");

// Create user table
db.exec(`
  CREATE TABLE IF NOT EXISTS user (
    id TEXT PRIMARY KEY,
    email TEXT UNIQUE NOT NULL,
    emailVerified INTEGER DEFAULT 0,
    name TEXT,
    image TEXT,
    createdAt INTEGER NOT NULL,
    updatedAt INTEGER NOT NULL
  );
`);

console.log("✓ Created user table");

// Create session table
db.exec(`
  CREATE TABLE IF NOT EXISTS session (
    id TEXT PRIMARY KEY,
    userId TEXT NOT NULL,
    expiresAt INTEGER NOT NULL,
    token TEXT UNIQUE NOT NULL,
    ipAddress TEXT,
    userAgent TEXT,
    createdAt INTEGER NOT NULL,
    updatedAt INTEGER NOT NULL,
    FOREIGN KEY (userId) REFERENCES user(id) ON DELETE CASCADE
  );
`);

console.log("✓ Created session table");

// Create account table (for OAuth, but we'll create it for completeness)
db.exec(`
  CREATE TABLE IF NOT EXISTS account (
    id TEXT PRIMARY KEY,
    userId TEXT NOT NULL,
    accountId TEXT NOT NULL,
    providerId TEXT NOT NULL,
    accessToken TEXT,
    refreshToken TEXT,
    idToken TEXT,
    expiresAt INTEGER,
    password TEXT,
    createdAt INTEGER NOT NULL,
    updatedAt INTEGER NOT NULL,
    FOREIGN KEY (userId) REFERENCES user(id) ON DELETE CASCADE,
    UNIQUE(providerId, accountId)
  );
`);

console.log("✓ Created account table");

// Create verification table
db.exec(`
  CREATE TABLE IF NOT EXISTS verification (
    id TEXT PRIMARY KEY,
    identifier TEXT NOT NULL,
    value TEXT NOT NULL,
    expiresAt INTEGER NOT NULL,
    createdAt INTEGER NOT NULL,
    updatedAt INTEGER
  );
`);

console.log("✓ Created verification table");

db.close();
console.log("\n✅ Database schema created successfully!");
console.log(`Database location: ${dbPath}`);
