import json
import uuid
"""Tests for error handler service (error-01~09).

Coverage: cancel_overdue_orders, arbitration, agent abandon, health check.
"""
import pytest
import pytest_asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from app.models.order import Order
from app.models.agent import Agent
from app.models.demand import Demand
from app.models.user import User
from app.services.error_handler_service import (
    cancel_overdue_orders,
    initiate_arbitration,
    resolve_arbitration,
    agent_abandon_order,
    check_agent_health,
)


class TestCancelOverdueOrders:
    """Test error-01: Agent超时未交付自动取消."""

    @pytest.mark.asyncio
    async def test_cancel_overdue_order(self, async_db, test_agent: Agent, test_user: User):
        """Order past ETA should be cancelled, credit score -10."""
        # Create an overdue accepted order
        order = Order(
            id=f"order-overdue-{uuid.uuid4().hex[:8]}",
            demand_id=f"demand-overdue-{uuid.uuid4().hex[:8]}",
            agent_id=test_agent.id,
            user_id=test_user.id,
            price=100.0,
            status="accepted",
            eta_hours=24,
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=72),  # 3 days ago
        )
        async_db.add(order)
        await async_db.commit()

        cancelled = await cancel_overdue_orders(async_db, hours_threshold=48)
        assert order.id in cancelled

        # Verify order is cancelled
        result = await async_db.execute(select(Order).where(Order.id == order.id))
        updated_order = result.scalar_one()
        assert updated_order.status == "cancelled"
        assert "超时" in updated_order.cancel_reason

    @pytest.mark.asyncio
    async def test_cancel_requeues_demand(self, async_db, test_agent: Agent, test_user: User):
        """Cancelled order should re-queue the demand."""
        demand = Demand(
            id=f"demand-overdue-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            title="Overdue demand",
            description="test",
            budget=100,
            status="matched",
            match_status="matched",
        )
        async_db.add(demand)
        await async_db.commit()

        order = Order(
            id=f"order-overdue-{uuid.uuid4().hex[:8]}",
            demand_id=demand.id,
            agent_id=test_agent.id,
            user_id=test_user.id,
            price=100.0,
            status="accepted",
            updated_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=72),
        )
        async_db.add(order)
        await async_db.commit()

        await cancel_overdue_orders(async_db, hours_threshold=48)

        result = await async_db.execute(select(Demand).where(Demand.id == demand.id))
        updated_demand = result.scalar_one()
        assert updated_demand.status == "open"

    @pytest.mark.asyncio
    async def test_cancel_no_overdue_orders(self, async_db):
        """No overdue orders should return empty list."""
        cancelled = await cancel_overdue_orders(async_db, hours_threshold=48)
        assert cancelled == []


class TestArbitration:
    """Test error-03: 仲裁流程."""

    @pytest.mark.asyncio
    async def test_initiate_arbitration(self, async_db, test_user: User):
        """Arbitration should set status=disputed."""
        order = Order(
            id=f"order-arb-{uuid.uuid4().hex[:8]}",
            demand_id=f"demand-arb-{uuid.uuid4().hex[:8]}",
            agent_id=f"agent-arb-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            price=100.0,
            status="delivered",
        )
        async_db.add(order)
        await async_db.commit()

        result = await initiate_arbitration(order.id, async_db, "Test dispute")
        assert result.status == "disputed"
        assert result.arbitration_status == "pending"

    @pytest.mark.asyncio
    async def test_resolve_arbitration_refund(self, async_db, test_user: User):
        """Resolution 'refund' should cancel order."""
        order = Order(
            id=f"order-arb-{uuid.uuid4().hex[:8]}",
            demand_id=f"demand-arb-{uuid.uuid4().hex[:8]}",
            agent_id=f"agent-arb-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            price=100.0,
            status="disputed",
            arbitration_status="pending",
        )
        async_db.add(order)
        await async_db.commit()

        result = await resolve_arbitration(order.id, async_db, "admin-1", "refund", "Full refund")
        assert result.status == "cancelled"
        assert result.arbitration_status == "resolved"

    @pytest.mark.asyncio
    async def test_resolve_arbitration_release_agent(self, async_db, test_agent: Agent, test_user: User):
        """Resolution 'release_agent' should complete order and +5 credit."""
        original_score = test_agent.credit_score
        order = Order(
            id=f"order-arb-{uuid.uuid4().hex[:8]}",
            demand_id=f"demand-arb-{uuid.uuid4().hex[:8]}",
            agent_id=test_agent.id,
            user_id=test_user.id,
            price=100.0,
            status="disputed",
            arbitration_status="pending",
        )
        async_db.add(order)
        await async_db.commit()

        result = await resolve_arbitration(order.id, async_db, "admin-1", "release_agent", "Release agent")
        assert result.status == "completed"
        
        # Check agent credit score increased
        agent_result = await async_db.execute(select(Agent).where(Agent.id == test_agent.id))
        updated_agent = agent_result.scalar_one()
        assert updated_agent.credit_score == original_score + 5

    @pytest.mark.asyncio
    async def test_resolve_arbitration_non_disputed_fails(self, async_db, test_user: User):
        """Resolving non-disputed order should fail."""
        order = Order(
            id=f"order-arb-{uuid.uuid4().hex[:8]}",
            demand_id=f"demand-arb-{uuid.uuid4().hex[:8]}",
            agent_id=f"agent-arb-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            price=100.0,
            status="completed",  # not disputed
        )
        async_db.add(order)
        await async_db.commit()

        with pytest.raises(ValueError, match="仅仲裁中订单可裁决"):
            await resolve_arbitration(order.id, async_db, "admin-1", "refund", "Should fail")

    @pytest.mark.asyncio
    async def test_initiate_arbitration_not_found(self, async_db):
        """Arbitration on non-existing order should fail."""
        with pytest.raises(ValueError, match="订单不存在"):
            await initiate_arbitration("non-existing", async_db, "Test")


class TestAgentAbandon:
    """Test error-07: Agent中途放弃."""

    @pytest.mark.asyncio
    async def test_agent_abandon_order(self, async_db, test_agent: Agent, test_user: User):
        """Abandoned order should cancel, credit score -5, demand re-queued."""
        demand = Demand(
            id=f"demand-abandon-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            title="Abandon demand",
            description="test",
            budget=100,
            status="matched",
        )
        async_db.add(demand)
        await async_db.commit()

        order = Order(
            id=f"order-abandon-{uuid.uuid4().hex[:8]}",
            demand_id=demand.id,
            agent_id=test_agent.id,
            user_id=test_user.id,
            price=100.0,
            status="accepted",
        )
        async_db.add(order)
        await async_db.commit()

        original_score = test_agent.credit_score
        result = await agent_abandon_order(order.id, async_db, test_agent.id, "Test abandon")
        
        assert result.status == "cancelled"
        assert "放弃" in result.cancel_reason
        
        # Credit score decreased
        agent_result = await async_db.execute(select(Agent).where(Agent.id == test_agent.id))
        updated_agent = agent_result.scalar_one()
        assert updated_agent.credit_score == original_score - 5
        
        # Demand re-queued
        demand_result = await async_db.execute(select(Demand).where(Demand.id == demand.id))
        updated_demand = demand_result.scalar_one()
        assert updated_demand.status == "open"


class TestAgentHealthCheck:
    """Test error-09: Agent健康监控."""

    @pytest.mark.asyncio
    async def test_health_check_no_issues(self, async_db, test_agent: Agent):
        """Healthy agent should not be flagged."""
        result = await check_agent_health(async_db)
        assert "inactive" in result
        assert "low_quality" in result
        assert "unreachable" in result
        # test_agent has completed_count=0 but was just created, so not 7 days old
        assert test_agent.id not in result["inactive"]

    @pytest.mark.asyncio
    async def test_health_check_flags_low_quality(self, async_db, test_agent: Agent):
        """Agent with failed_count >= 3 should be flagged as low_quality."""
        test_agent.failed_count = 3
        await async_db.commit()

        result = await check_agent_health(async_db)
        assert test_agent.id in result["low_quality"]

    @pytest.mark.asyncio
    async def test_health_check_flags_inactive(self, async_db, test_user: User):
        """Agent registered 7+ days ago with 0 completed should be flagged."""
        agent = Agent(
            id=f"agent-inactive-{uuid.uuid4().hex[:8]}",
            user_id=test_user.id,
            name="old_inactive_agent",
            api_url="https://example.com",
            capabilities=json.dumps(["文案"], ensure_ascii=False),
            completed_count=0,
            created_at=datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=8),
        )
        async_db.add(agent)
        await async_db.commit()

        result = await check_agent_health(async_db)
        assert agent.id in result["inactive"]
