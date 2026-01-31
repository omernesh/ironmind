"""Script to mark specific documents as demo documents."""
import asyncio
import aiosqlite
import structlog
from typing import List

logger = structlog.get_logger(__name__)


async def mark_documents_as_demo(db_path: str, doc_ids: List[str]) -> None:
    """Mark specified documents as demo documents.

    Args:
        db_path: Path to SQLite database file
        doc_ids: List of document IDs to mark as demo
    """
    async with aiosqlite.connect(db_path) as db:
        for doc_id in doc_ids:
            # Check if document exists
            async with db.execute(
                "SELECT filename FROM documents WHERE doc_id = ?",
                (doc_id,)
            ) as cursor:
                row = await cursor.fetchone()

            if row:
                filename = row[0]
                # Mark as demo
                await db.execute(
                    "UPDATE documents SET is_demo = 1 WHERE doc_id = ?",
                    (doc_id,)
                )
                logger.info("marked_as_demo", doc_id=doc_id, filename=filename)
                print(f"✓ Marked {filename} as demo")
            else:
                logger.warning("document_not_found", doc_id=doc_id)
                print(f"✗ Document {doc_id} not found")

        await db.commit()
        logger.info("demo_marking_completed", count=len(doc_ids))


async def list_indexed_documents(db_path: str) -> List[tuple]:
    """List all indexed documents for review.

    Args:
        db_path: Path to SQLite database file

    Returns:
        List of (doc_id, filename, chunk_count) tuples
    """
    async with aiosqlite.connect(db_path) as db:
        async with db.execute("""
            SELECT doc_id, filename, chunk_count, user_id
            FROM documents
            WHERE status = 'Done' OR status = 'Indexed'
            ORDER BY created_at DESC
        """) as cursor:
            rows = await cursor.fetchall()

    return rows


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage:")
        print("  python mark_as_demo.py <db_path> list              - List indexed documents")
        print("  python mark_as_demo.py <db_path> <doc_id> ...      - Mark documents as demo")
        sys.exit(1)

    db_path = sys.argv[1]

    if len(sys.argv) > 2 and sys.argv[2] == "list":
        # List indexed documents
        docs = asyncio.run(list_indexed_documents(db_path))
        print(f"\nFound {len(docs)} indexed documents:\n")
        for doc_id, filename, chunk_count, user_id in docs:
            print(f"  {doc_id}")
            print(f"    Filename: {filename}")
            print(f"    Chunks: {chunk_count}")
            print(f"    User: {user_id}")
            print()
    else:
        # Mark specified documents as demo
        doc_ids = sys.argv[2:]
        print(f"\nMarking {len(doc_ids)} documents as demo...\n")
        asyncio.run(mark_documents_as_demo(db_path, doc_ids))
        print(f"\n✓ Completed")
