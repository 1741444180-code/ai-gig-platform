"""需求模块 - 发布、列表、详情、修改、撮合匹配、报价"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_active_user
from app.db.database import get_db
from app.models.models import User, Requirement, RequirementQuote, AgentProfile
from app.schemas.requirement import (
    RequirementCreate,
    RequirementResponse,
    RequirementListResponse,
    RequirementUpdate,
    QuoteCreate,
    QuoteResponse,
    MatchResponse,
)
from app.services.ai_service import structure_requirement, generate_embedding, match_agents, match_agents_hybrid

logger = logging.getLogger(__name__)

router = APIRouter()


# ==================== 辅助函数 ====================

def _to_response(req: Requirement) -> dict:
    """将 ORM 对象转换为响应字典"""
    return {
        "id": req.id,
        "user_id": req.user_id,
        "title": req.title,
        "description": req.description,
        "category": req.category,
        "tags": req.tags or [],
        "attachments": req.attachments or [],
        "budget": req.budget,
        "urgency": req.urgency,
        "structured_data": req.structured_data or {},
        "status": req.status,
        "match_mode": req.match_mode,
        "created_at": req.created_at,
        "updated_at": req.updated_at,
    }


async def _get_requirement_or_404(
    req_id: str,
    db: AsyncSession,
    status_filter: Optional[str] = None,
) -> Requirement:
    """获取需求对象，不存在时抛404"""
    try:
        import uuid as _uuid
        req_uuid = _uuid.UUID(req_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="无效的需求ID格式")

    stmt = select(Requirement).where(Requirement.id == req_uuid)
    if status_filter:
        stmt = stmt.where(Requirement.status == status_filter)

    result = await db.execute(stmt)
    req = result.scalar_one_or_none()

    if not req:
        raise HTTPException(status_code=404, detail="需求不存在")
    return req


# ==================== 1. 需求发布 ====================

@router.post(
    "/",
    response_model=RequirementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="发布需求",
)
async def create_requirement(
    req_data: RequirementCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """发布新需求

    需Bearer token认证。
    - 自动调用通义千问AI进行需求结构化分析
    - 生成embedding向量存入pgvector
    - 初始状态为 open
    - AI调用失败不影响发布（使用默认值兜底）
    """
    # 1. AI结构化分析（失败不影响发布）
    structured = await structure_requirement(req_data.description)

    # 2. 生成embedding向量（失败不影响发布）
    embedding = await generate_embedding(req_data.description)

    # 3. 创建需求记录
    requirement = Requirement(
        user_id=current_user.id,
        title=req_data.title,
        description=req_data.description,
        category=structured.get("category"),
        tags=structured.get("tags", []),
        attachments=req_data.attachments or [],
        budget=req_data.budget,
        urgency=req_data.urgency,
        structured_data=structured,
        status="open",
        match_mode=req_data.match_mode,
        embedding=embedding,
    )

    db.add(requirement)
    await db.flush()
    await db.refresh(requirement)

    # 自动撮合：match_mode == "auto" 时立即触发
    if requirement.match_mode == "auto":
        try:
            matches = await match_agents_hybrid(db, requirement)
            if matches:
                requirement.status = "matched"
                # 将匹配结果存入 structured_data
                if requirement.structured_data is None:
                    requirement.structured_data = {}
                requirement.structured_data["matched_agents"] = matches
                await db.flush()
                logger.info(
                    f"自动撮合完成，需求 {requirement.id} 状态变更为 matched，"
                    f"找到 {len(matches)} 个匹配Agent"
                )
            else:
                logger.info(f"自动撮合完成但未找到匹配Agent，需求 {requirement.id} 保持 open")
        except Exception as e:
            # AI撮合失败不影响需求创建
            logger.warning(f"需求 {requirement.id} 自动撮合失败（不影响发布）: {e}")

    logger.info(f"用户 {current_user.id} 发布需求: {requirement.id}")
    return RequirementResponse.model_validate(requirement)


# ==================== 2. 需求列表 ====================

@router.get("/", response_model=RequirementListResponse, summary="需求列表")
async def list_requirements(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    category: Optional[str] = Query(default=None, description="按类别筛选"),
    status: Optional[str] = Query(default=None, description="按状态筛选"),
    db: AsyncSession = Depends(get_db),
):
    """获取公开需求列表（分页）

    支持按 category 和 status 筛选。
    不需要认证。
    """
    offset = (page - 1) * page_size

    # 构建基础查询条件：默认只返回公开的需求
    base_conditions = []

    if category:
        base_conditions.append(Requirement.category == category)
    if status:
        base_conditions.append(Requirement.status == status)

    # 查询总数
    count_stmt = select(func.count(Requirement.id))
    if base_conditions:
        count_stmt = count_stmt.where(and_(*base_conditions))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 查询列表
    query = select(Requirement)
    if base_conditions:
        query = query.where(and_(*base_conditions))
    query = query.order_by(Requirement.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    requirements = result.scalars().all()

    return RequirementListResponse(
        requirements=[RequirementResponse.model_validate(r) for r in requirements],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/mine", response_model=RequirementListResponse, summary="我的需求")
async def list_my_requirements(
    page: int = Query(default=1, ge=1, description="页码"),
    page_size: int = Query(default=20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(default=None, description="按状态筛选"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """获取我发布的需求列表

    需Bearer token认证。
    """
    offset = (page - 1) * page_size

    base_conditions = [Requirement.user_id == current_user.id]
    if status:
        base_conditions.append(Requirement.status == status)

    # 查询总数
    count_stmt = select(func.count(Requirement.id)).where(and_(*base_conditions))
    total_result = await db.execute(count_stmt)
    total = total_result.scalar() or 0

    # 查询列表
    query = select(Requirement).where(and_(*base_conditions))
    query = query.order_by(Requirement.created_at.desc()).offset(offset).limit(page_size)

    result = await db.execute(query)
    requirements = result.scalars().all()

    return RequirementListResponse(
        requirements=[RequirementResponse.model_validate(r) for r in requirements],
        total=total,
        page=page,
        page_size=page_size,
    )


# ==================== 3. 需求详情 ====================

@router.get("/{req_id}", response_model=RequirementResponse, summary="需求详情")
async def get_requirement(
    req_id: str,
    db: AsyncSession = Depends(get_db),
):
    """获取需求详情

    不需要认证。
    """
    requirement = await _get_requirement_or_404(req_id, db)
    return RequirementResponse.model_validate(requirement)


# ==================== 4. 需求修改 ====================

@router.put("/{req_id}", response_model=RequirementResponse, summary="修改需求")
async def update_requirement(
    req_id: str,
    req_data: RequirementUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """修改需求

    需Bearer token认证。
    仅需求发布者可操作，且仅在未接单前（status = open）可修改。
    """
    requirement = await _get_requirement_or_404(req_id, db)

    # 权限校验：仅发布者
    if requirement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有需求发布者可以修改")

    # 状态校验：未接单前才可修改
    if requirement.status != "open":
        raise HTTPException(
            status_code=400,
            detail="需求已被接单，无法修改",
        )

    # 更新字段（只更新非None的字段）
    if req_data.title is not None:
        requirement.title = req_data.title
    if req_data.description is not None:
        requirement.description = req_data.description
    if req_data.attachments is not None:
        requirement.attachments = req_data.attachments
    if req_data.budget is not None:
        requirement.budget = req_data.budget
    if req_data.urgency is not None:
        requirement.urgency = req_data.urgency
    if req_data.match_mode is not None:
        requirement.match_mode = req_data.match_mode

    # 如果描述被修改，重新做AI结构化和embedding
    if req_data.description is not None:
        structured = await structure_requirement(req_data.description)
        requirement.category = structured.get("category")
        requirement.tags = structured.get("tags", [])
        requirement.structured_data = structured

        embedding = await generate_embedding(req_data.description)
        requirement.embedding = embedding

    await db.flush()
    await db.refresh(requirement)

    logger.info(f"用户 {current_user.id} 修改需求: {requirement.id}")
    return RequirementResponse.model_validate(requirement)


# ==================== 5. 需求取消 ====================

@router.delete("/{req_id}", status_code=status.HTTP_204_NO_CONTENT, summary="取消需求")
async def cancel_requirement(
    req_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """取消需求

    需Bearer token认证。
    仅需求发布者可操作，且仅在未接单前（status = open）可取消。
    """
    requirement = await _get_requirement_or_404(req_id, db)

    # 权限校验：仅发布者
    if requirement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有需求发布者可以取消")

    # 状态校验：未接单前才可取消
    if requirement.status != "open":
        raise HTTPException(
            status_code=400,
            detail="需求已被接单，无法取消",
        )

    requirement.status = "cancelled"
    await db.flush()

    logger.info(f"用户 {current_user.id} 取消需求: {requirement.id}")


# ==================== 6. 智能撮合 ====================

@router.post("/{req_id}/match", summary="需求撮合匹配")
async def match_requirement(
    req_id: str,
    limit: int = Query(default=10, ge=1, le=50, description="返回匹配数量"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """手动触发需求匹配

    需Bearer token认证。
    使用pgvector cosine similarity查找最匹配的Agent。
    """
    requirement = await _get_requirement_or_404(req_id, db)

    # 权限校验：仅发布者
    if requirement.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只有需求发布者可以触发匹配")

    # 检查需求是否有embedding
    if not requirement.embedding:
        # 没有embedding则重新生成
        embedding = await generate_embedding(requirement.description)
        if embedding:
            requirement.embedding = embedding
            await db.flush()
        else:
            raise HTTPException(
                status_code=500,
                detail="无法生成需求向量，请检查AI服务配置",
            )

    # 执行混合匹配（规则 + 向量）
    matches = await match_agents_hybrid(db, requirement, limit)

    # 记录匹配结果到 structured_data
    if requirement.structured_data is None:
        requirement.structured_data = {}
    requirement.structured_data["matched_agents"] = matches

    # 更新需求状态
    if matches:
        requirement.status = "matched"
        await db.flush()

    return {
        "requirement_id": str(requirement.id),
        "match_count": len(matches),
        "matches": matches,
    }


# ==================== 7. 需求预览（AI 结构化确认） ====================

@router.post(
    "/preview",
    summary="需求预览（AI 结构化确认）",
)
async def preview_requirement(
    req_data: RequirementCreate,
    current_user: User = Depends(get_current_active_user),
):
    """需求发布前的预览确认

    调用 AI 进行需求结构化分析，返回结构化结果供用户确认。
    用户可以修改后再正式发布。

    需 Bearer token 认证。
    不创建数据库记录，仅返回 AI 分析结果。
    """
    # 1. AI 结构化分析
    structured = await structure_requirement(req_data.description)

    # 2. 尝试生成 embedding
    embedding = await generate_embedding(req_data.description)

    return {
        "title": req_data.title,
        "description": req_data.description,
        "category": structured.get("category", "其他"),
        "tags": structured.get("tags", []),
        "suggested_budget": structured.get("suggested_budget", req_data.budget),
        "urgency": structured.get("urgency", req_data.urgency),
        "has_embedding": embedding is not None,
        "structured_data": structured,
        "message": "请确认以上 AI 分析结果，确认后再正式发布",
    }


# ==================== 7. 报价 ====================

@router.post(
    "/{req_id}/quote",
    response_model=QuoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="提交报价",
)
async def submit_quote(
    req_id: str,
    quote_data: QuoteCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """对需求提交报价

    需Bearer token认证。
    仅Agent用户可以报价。
    """
    requirement = await _get_requirement_or_404(req_id, db)

    # 状态校验：只有open或matched状态的需求可以报价
    if requirement.status not in ("open", "matched"):
        raise HTTPException(
            status_code=400,
            detail=f"需求当前状态为 {requirement.status}，无法报价",
        )

    # 身份校验：必须是Agent
    if current_user.role not in ("agent", "admin"):
        raise HTTPException(
            status_code=403,
            detail="只有Agent用户可以提交报价",
        )

    # 检查Agent档案
    agent_result = await db.execute(
        select(AgentProfile).where(
            AgentProfile.user_id == current_user.id,
            AgentProfile.status == 1,
        )
    )
    agent_profile = agent_result.scalar_one_or_none()

    if not agent_profile:
        raise HTTPException(
            status_code=400,
            detail="您需要先创建并通过Agent审核才能报价",
        )

    # 检查是否已报价
    existing_quote = await db.execute(
        select(RequirementQuote).where(
            RequirementQuote.requirement_id == requirement.id,
            RequirementQuote.agent_id == current_user.id,
            RequirementQuote.status == "pending",
        )
    )
    if existing_quote.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="您已经对该需求提交过报价，请勿重复提交",
        )

    # 创建报价记录
    quote = RequirementQuote(
        requirement_id=requirement.id,
        agent_id=current_user.id,
        price=quote_data.price,
        delivery_hours=quote_data.delivery_hours,
        message=quote_data.message,
        status="pending",
    )

    db.add(quote)
    await db.flush()
    await db.refresh(quote)

    logger.info(f"Agent {current_user.id} 对需求 {requirement.id} 报价: {quote_data.price}元")
    return QuoteResponse.model_validate(quote)
