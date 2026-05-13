import asyncio
import logging
from app.core.database import Base, engine
import app.domain.inventory
import app.domain.sales
import app.domain.purchases
import app.domain.user
import app.domain.tenant

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def migrate_db():
    logger.info("Starting WMS Migration...")
    async with engine.begin() as conn:
        # In a real environment we would use Alembic, 
        # but for this setup we will recreate the tables to ensure WMS compatibility.
        logger.info("Dropping existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        logger.info("Creating new WMS tables...")
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Migration complete.")

if __name__ == "__main__":
    asyncio.run(migrate_db())
