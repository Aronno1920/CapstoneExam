"""
Database table creation script.
Run this script to create tables in your SQL database.
For MongoDB, tables are created automatically when data is inserted.
"""

import asyncio
from shared.config.settings import get_settings
from infrastructure.database.connection import get_database_connection
from infrastructure.database.models import Base


async def create_tables():
    """Create database tables."""
    settings = get_settings()
    db_connection = get_database_connection(settings)
    
    print(f"Creating tables for {settings.database_type}...")
    
    if db_connection.is_sql_database():
        try:
            engine = await db_connection.get_sql_engine()
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            print("✅ Tables created successfully!")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
        finally:
            await db_connection.close_connections()
    
    elif db_connection.is_mongo_database():
        try:
            database = await db_connection.get_mongo_database()
            # Test connection
            await database.command("ping")
            print("✅ MongoDB connection successful! Collections will be created automatically when data is inserted.")
        except Exception as e:
            print(f"❌ Error connecting to MongoDB: {e}")
        finally:
            await db_connection.close_connections()
    
    else:
        print(f"❌ Unsupported database type: {settings.database_type}")


if __name__ == "__main__":
    asyncio.run(create_tables())