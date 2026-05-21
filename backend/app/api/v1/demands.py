"""Demand API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.engine import get_db
from app.models.demand import Demand
from app.schemas.demand import DemandCreate, DemandResponse

router = APIRouter()


@router.post("/", response_model=DemandResponse)
async def create_demand(demand_in: DemandCreate, db: AsyncSession = Depends(get_db)):
    """Publish a new demand."""
    demand = Demand(
        user_id="temp-user-id",  # TODO: from auth token
        title=demand_in.title,
        description=demand_in.description,
        budget=demand_in.budget,
        attachments=str(demand_in.attachments) if demand_in.attachments else None,
        deadline=demand_in.deadline,
    )
    db.add(demand)
    await db.commit()
    await db.refresh(demand)
    # TODO: trigger AI structuring + matching
    return demand


@router.get("/", response_model=list[DemandResponse])
async def list_demands(db: AsyncSession = Depends(get_db)):
    """List all open demands."""
    result = await db.execute(
        select(Demand).where(Demand.status == "open").order_by(Demand.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{demand_id}", response_model=DemandResponse)
async def get_demand(demand_id: str, db: AsyncSession = Depends(get_db)):
    """Get demand by ID."""
    result = await db.execute(select(Demand).where(Demand.id == demand_id))
    demand = result.scalar_one_or_none()
    if not demand:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Demand not found")
    return demand
