"""Agent API endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.engine import get_db
from app.models.agent import Agent
from app.schemas.agent import AgentCreate, AgentResponse

router = APIRouter()


@router.post("/", response_model=AgentResponse)
async def create_agent(agent_in: AgentCreate, db: AsyncSession = Depends(get_db)):
    """Register a new Agent."""
    agent = Agent(
        user_id="temp-user-id",  # TODO: from auth token
        name=agent_in.name,
        description=agent_in.description,
        api_url=agent_in.api_url,
        api_key=agent_in.api_key,
        webhook_url=agent_in.webhook_url,
        capabilities=str(agent_in.capabilities) if agent_in.capabilities else None,
        mode=agent_in.mode,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent


@router.get("/", response_model=list[AgentResponse])
async def list_agents(db: AsyncSession = Depends(get_db)):
    """List all active agents."""
    result = await db.execute(select(Agent).where(Agent.status == "active"))
    return result.scalars().all()


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Get agent by ID."""
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent
