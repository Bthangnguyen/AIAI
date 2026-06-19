import asyncio
from app.database import AsyncSessionFactory
from sqlalchemy import select, func
from app.models.poi import PointOfInterest

async def main():
    async with AsyncSessionFactory() as session:
        # Total count
        cnt = await session.execute(select(func.count(PointOfInterest.uuid)))
        total_count = cnt.scalar()
        print(f"Total POIs in DB: {total_count}")
        
        # Count with priority > 0.65
        cnt_high = await session.execute(select(func.count(PointOfInterest.uuid)).where(PointOfInterest.priority_score > 0.65))
        print(f"POIs with priority > 0.65: {cnt_high.scalar()}")
        
        # Count with priority >= 0.65
        cnt_eq = await session.execute(select(func.count(PointOfInterest.uuid)).where(PointOfInterest.priority_score >= 0.65))
        print(f"POIs with priority >= 0.65: {cnt_eq.scalar()}")

if __name__ == "__main__":
    asyncio.run(main())
