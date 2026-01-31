"""Database migration: Add demo flag and entity/relationship counts to documents table."""
import asyncio
import aiosqlite
import structlog

logger = structlog.get_logger(__name__)


async def migrate_database(db_path: str) -> None:
    """Add is_demo, entity_count, and relationship_count columns to documents table.

    Args:
        db_path: Path to SQLite database file
    """
    async with aiosqlite.connect(db_path) as db:
        # Check if columns already exist
        async with db.execute("PRAGMA table_info(documents)") as cursor:
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

        # Add is_demo column if it doesn't exist
        if "is_demo" not in column_names:
            logger.info("adding_is_demo_column")
            await db.execute("""
                ALTER TABLE documents
                ADD COLUMN is_demo INTEGER DEFAULT 0
            """)
            logger.info("is_demo_column_added")
        else:
            logger.info("is_demo_column_already_exists")

        # Add entity_count column if it doesn't exist
        if "entity_count" not in column_names:
            logger.info("adding_entity_count_column")
            await db.execute("""
                ALTER TABLE documents
                ADD COLUMN entity_count INTEGER
            """)
            logger.info("entity_count_column_added")
        else:
            logger.info("entity_count_column_already_exists")

        # Add relationship_count column if it doesn't exist
        if "relationship_count" not in column_names:
            logger.info("adding_relationship_count_column")
            await db.execute("""
                ALTER TABLE documents
                ADD COLUMN relationship_count INTEGER
            """)
            logger.info("relationship_count_column_added")
        else:
            logger.info("relationship_count_column_already_exists")

        await db.commit()
        logger.info("migration_completed")


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python migrate_add_demo_flag.py <db_path>")
        sys.exit(1)

    db_path = sys.argv[1]
    asyncio.run(migrate_database(db_path))
    print(f"Migration completed for {db_path}")
