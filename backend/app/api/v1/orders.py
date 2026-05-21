"""Order API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.engine import get_db
from app.models.order import Order
from app.schemas.order import QuoteCreate, OrderResponse

router = APIRouter()


@router.post("/{demand_id}/quotes", response_model=OrderResponse)
async def create_quote(
    demand_id: str,
    quote_in: QuoteCreate,
    db: AsyncSession = Depends(get_db),
):
    """Agent submits a quote for a demand."""
    order = Order(
        demand_id=demand_id,
        agent_id="temp-agent-id",  # TODO: from auth token
        user_id="temp-user-id",
        price=quote_in.price,
        accept_note=quote_in.accept_note,
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/accept", response_model=OrderResponse)
async def accept_quote(order_id: str, db: AsyncSession = Depends(get_db)):
    """User accepts a quote (creates the order contract)."""
    from app.models.order import Order as OrderModel

    result = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = "accepted"
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/deliver", response_model=OrderResponse)
async def submit_delivery(
    order_id: str,
    delivery_url: str,
    delivery_note: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Agent submits delivery."""
    from app.models.order import Order as OrderModel

    result = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = "submitted"
    order.delivery_url = delivery_url
    order.delivery_note = delivery_note
    await db.commit()
    await db.refresh(order)
    return order


@router.post("/{order_id}/complete", response_model=OrderResponse)
async def complete_order(order_id: str, db: AsyncSession = Depends(get_db)):
    """User confirms completion (releases payment)."""
    from app.models.order import Order as OrderModel
    from datetime import datetime

    result = await db.execute(select(OrderModel).where(OrderModel.id == order_id))
    order = result.scalar_one_or_none()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    order.status = "completed"
    order.completed_at = datetime.utcnow()
    await db.commit()
    await db.refresh(order)
    return order
