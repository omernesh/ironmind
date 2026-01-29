---
created: 2026-01-29T16:00
title: Pre-ingest test documents for system verification
area: testing
files:
  - docs/*.docx
---

## Problem

Before deploying Phase 6, users need sample documents pre-ingested to test the system immediately without waiting for upload/processing. Currently, docs/ directory is empty - need to either:
1. Provide sample aerospace/technical .docx files in docs/
2. Add a seed script to ingest them on first run
3. Update deployment guide to suggest test documents

Without this, users on Hetzner VPS will have to manually upload documents before seeing any chat functionality, which reduces the "wow factor" during evaluation.

## Solution

Add sample .docx files to docs/ directory and create a seed script that:
- Checks if any documents exist for demo user
- If not, ingests sample documents from docs/ on startup
- Suggests these documents in the landing page ("Try asking about [Sample Doc Name]")

Alternative: Update DEPLOYMENT.md with instructions to upload sample documents manually during setup verification.
