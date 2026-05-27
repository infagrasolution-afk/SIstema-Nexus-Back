from typing import Generic, TypeVar, Type, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import Base

ModelType = TypeVar("ModelType", bound=Base)

class BaseRepository(Generic[ModelType]):
    def __init__(self, model: Type[ModelType]):
        self.model = model

    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        result = await db.execute(select(self.model).filter(self.model.id == id))
        return result.scalars().first()
        
    async def get_with_lock(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Fetches a record and locks it for update to prevent race conditions."""
        result = await db.execute(select(self.model).filter(self.model.id == id).with_for_update())
        return result.scalars().first()

    async def get_all(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[ModelType]:
        result = await db.execute(select(self.model).offset(skip).limit(limit))
        return list(result.scalars().all())

    async def create(self, db: AsyncSession, *, obj_in: dict) -> ModelType:
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        await db.flush()
        return db_obj

    async def update(self, db: AsyncSession, *, db_obj: ModelType, obj_in: dict) -> ModelType:
        for field, value in obj_in.items():
            setattr(db_obj, field, value)
        db.add(db_obj)
        await db.flush()
        return db_obj

    async def delete(self, db: AsyncSession, *, id: Any) -> ModelType:
        obj = await db.get(self.model, id)
        if obj:
            await db.delete(obj)
            await db.flush()
        return obj
