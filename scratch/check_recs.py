import asyncio
from app.core.database import AsyncSessionLocal
from sqlalchemy import select
from app.models.user import User
from app.api.v1.endpoints.connect import get_ai_partner_recommendations

async def main():
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(User).where(User.email == 'amirtha2009@gmail.com'))
        u = res.scalars().first()
        print(f"User: {u.id}, {u.email}, {u.full_name}")

        recs = await get_ai_partner_recommendations(current_user=u, db=db)
        print(f"Total Recommendations returned: {len(recs)}")
        for r in recs:
            print(f" -> Rec: {r.full_name} ({r.user_id}), Score: {r.matching_score}, Institution: {r.institution_name}, Status: {r.connection_status}")

if __name__ == "__main__":
    asyncio.run(main())
