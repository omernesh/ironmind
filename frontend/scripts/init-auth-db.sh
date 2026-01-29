#!/bin/sh
# Better Auth Database Initialization Script
# Ensures database schema exists on container startup

set -e

DB_PATH="${DATABASE_PATH:-/app/data/auth.db}"
DB_DIR=$(dirname "$DB_PATH")

echo "Initializing Better Auth database at $DB_PATH..."

# Ensure data directory exists
mkdir -p "$DB_DIR"

# Check if database exists and has tables
if [ ! -f "$DB_PATH" ] || ! sqlite3 "$DB_PATH" ".tables" | grep -q "user"; then
    echo "Creating Better Auth schema..."

    sqlite3 "$DB_PATH" << 'EOF'
-- Better Auth v1.4.17+ Schema
-- Compatible with email/password authentication

CREATE TABLE IF NOT EXISTS user (
  id TEXT PRIMARY KEY,
  email TEXT NOT NULL UNIQUE,
  emailVerified INTEGER NOT NULL DEFAULT 0,
  name TEXT,
  image TEXT,
  createdAt INTEGER NOT NULL,
  updatedAt INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS session (
  id TEXT PRIMARY KEY,
  userId TEXT NOT NULL,
  expiresAt INTEGER NOT NULL,
  token TEXT,
  ipAddress TEXT,
  userAgent TEXT,
  createdAt INTEGER NOT NULL,
  updatedAt INTEGER NOT NULL,
  FOREIGN KEY (userId) REFERENCES user(id) ON DELETE CASCADE
);

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
  FOREIGN KEY (userId) REFERENCES user(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS verification (
  id TEXT PRIMARY KEY,
  identifier TEXT NOT NULL,
  value TEXT NOT NULL,
  expiresAt INTEGER NOT NULL,
  createdAt INTEGER NOT NULL,
  updatedAt INTEGER NOT NULL
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_user_email ON user(email);
CREATE INDEX IF NOT EXISTS idx_session_userId ON session(userId);
CREATE INDEX IF NOT EXISTS idx_session_token ON session(token);
CREATE INDEX IF NOT EXISTS idx_account_userId ON account(userId);

-- Enable WAL mode for better concurrency
PRAGMA journal_mode=WAL;
EOF

    echo "✓ Better Auth database schema created successfully"
else
    echo "✓ Better Auth database already initialized"

    # Add missing columns if upgrading from older schema
    # This ensures compatibility if schema evolves
    sqlite3 "$DB_PATH" << 'EOF' 2>/dev/null || true
ALTER TABLE session ADD COLUMN token TEXT;
ALTER TABLE user ADD COLUMN image TEXT;
ALTER TABLE account ADD COLUMN idToken TEXT;
EOF
fi

# Set proper permissions
chmod 644 "$DB_PATH"

echo "✓ Database initialization complete"
