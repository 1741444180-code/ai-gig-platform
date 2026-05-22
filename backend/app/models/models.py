from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, Float, JSON, ForeignKey, SmallInteger
from sqlalchemy.dialects.postgresql import UUID
from pgvector.sqlalchemy import Vector
from app.db.database import Base
from datetime import datetime, timezone
import uuid


class BaseModel(Base):
    """抽象基类"""
    __abstract__ = True
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))


# ==================== 用户系统 ====================

class User(BaseModel):
    """用户表"""
    __tablename__ = "users"

    openid = Column(String(128), unique=True, nullable=True, comment="微信openid")
    unionid = Column(String(128), nullable=True, comment="微信unionid")
    phone = Column(String(20), unique=True, nullable=False, comment="手机号")
    phone_verified = Column(Boolean, default=False, comment="手机号是否已验证")
    password_hash = Column(String(256), nullable=True, comment="密码哈希(bcrypt)")
    nickname = Column(String(64), nullable=True, comment="昵称")
    avatar = Column(String(512), nullable=True, comment="头像URL")
    role = Column(String(16), default="user", comment="role: user/agent/admin")
    status = Column(SmallInteger, default=1, comment="1=正常 0=禁用")
    balance = Column(Float, default=0.0, comment="余额")
    credit_score = Column(Integer, default=100, comment="信誉分")
    # 实名认证预留字段
    real_name = Column(String(64), nullable=True, comment="实名认证姓名（预留）")
    real_name_verified = Column(Boolean, default=False, comment="是否已实名认证（预留）")
    id_card_hash = Column(String(64), nullable=True, comment="身份证号SHA-256哈希（预留，不存明文）")


class AgentApiKey(BaseModel):
    """Agent API Key 管理表（多Key + SHA-256 存储 + Scope 权限）"""
    __tablename__ = "agent_api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_profiles.user_id"), nullable=False)
    key_name = Column(String(64), nullable=True, comment="Key 名称/备注")
    key_prefix = Column(String(8), nullable=False, comment="Key 前缀（展示用）")
    key_hash = Column(String(64), nullable=False, unique=True, comment="SHA-256 哈希值（存储用）")
    scope = Column(String(32), default="full", comment="权限范围: full=read_write sandbox=只读 sandbox_test=沙箱")
    is_active = Column(Boolean, default=True, comment="是否启用")
    is_sandbox = Column(Boolean, default=False, comment="是否沙箱 Key")
    last_used_at = Column(DateTime(timezone=True), nullable=True, comment="最后使用时间")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))


class AgentProfile(BaseModel):
    """Agent能力卡"""
    __tablename__ = "agent_profiles"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, unique=True)
    name = Column(String(128), nullable=False, comment="Agent名称")
    description = Column(Text, nullable=True, comment="能力描述")
    tags = Column(JSON, default=list, comment="能力标签")
    capabilities = Column(JSON, default=dict, comment="能力详情JSON")
    base_price = Column(Float, nullable=True, comment="基础报价")
    api_key = Column(String(256), unique=True, nullable=False, comment="API Key")
    webhook_url = Column(String(512), nullable=True, comment="回调地址")
    auto_accept = Column(Boolean, default=False, comment="自动接单开关")
    daily_limit = Column(Integer, default=0, comment="每日接单上限，0=不限")
    description_vec = Column(Vector(1536), nullable=True, comment="Agent能力描述向量(语义匹配)")
    today_orders = Column(Integer, default=0, comment="今日已接单数")
    status = Column(SmallInteger, default=0, comment="0=待审核 1=正常 2=暂停")


# ==================== 需求系统 ====================

class Requirement(BaseModel):
    """需求表"""
    __tablename__ = "requirements"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title = Column(String(256), nullable=False, comment="需求标题")
    description = Column(Text, nullable=False, comment="需求描述")
    category = Column(String(64), nullable=True, comment="AI自动分类")
    tags = Column(JSON, default=list, comment="需求标签")
    attachments = Column(JSON, default=list, comment="附件URL列表")
    budget = Column(Float, nullable=True, comment="预算金额")
    urgency = Column(SmallInteger, default=1, comment="紧急度 1=普通 2=加急 3=特急")
    structured_data = Column(JSON, default=dict, comment="AI结构化后的数据")
    status = Column(String(32), default="draft",
                    comment="状态: draft/open/matched/accepted/in_progress/delivered/completed/cancelled/disputed")
    match_mode = Column(String(16), default="auto", comment="auto=自动匹配 manual=手动")
    embedding = Column(Vector(1536), nullable=True, comment="需求文本embedding向量（通义千问text-embedding-v3）")


class RequirementQuote(BaseModel):
    """报价表"""
    __tablename__ = "requirement_quotes"

    requirement_id = Column(UUID(as_uuid=True), ForeignKey("requirements.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_profiles.user_id"), nullable=False)
    price = Column(Float, nullable=False, comment="报价金额")
    delivery_hours = Column(Float, nullable=True, comment="预计交付时间(小时)")
    message = Column(Text, nullable=True, comment="报价说明")
    status = Column(String(16), default="pending", comment="pending/accepted/rejected")


# ==================== 订单系统 ====================

class Order(BaseModel):
    """订单表"""
    __tablename__ = "orders"

    requirement_id = Column(UUID(as_uuid=True), ForeignKey("requirements.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, comment="需求方")
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_profiles.user_id"), nullable=False, comment="接单Agent")
    amount = Column(Float, nullable=False, comment="订单金额")
    platform_fee = Column(Float, default=0.0, comment="平台费")
    agent_income = Column(Float, nullable=False, comment="Agent收入")
    status = Column(String(32), default="pending",
                    comment="pending/paid/processing/delivered/reviewing/completed/cancelled/refunded/disputed")
    payment_method = Column(String(32), nullable=True, comment="wechat/alipay")
    payment_id = Column(String(128), nullable=True, comment="支付平台流水号")
    deliverables = Column(JSON, default=list, comment="交付物URL列表")
    delivery_message = Column(Text, nullable=True, comment="交付说明")
    ai_review_score = Column(Float, nullable=True, comment="AI验收评分")
    user_confirm = Column(SmallInteger, nullable=True, comment="1=确认 0=拒绝")
    modify_count = Column(Integer, default=0, comment="修改次数")
    completed_at = Column(DateTime(timezone=True), nullable=True)


# ==================== 评价系统 ====================

class Review(BaseModel):
    """评价表"""
    __tablename__ = "reviews"

    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_profiles.user_id"), nullable=False)
    rating = Column(SmallInteger, nullable=False, comment="1-5星")
    comment = Column(Text, nullable=True, comment="评价内容")
    is_anonymous = Column(Boolean, default=False)


# ==================== 信誉系统 ====================

class CreditRecord(BaseModel):
    """信誉记录表"""
    __tablename__ = "credit_records"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    change = Column(Integer, nullable=False, comment="信誉分变化(正/负)")
    reason = Column(String(256), nullable=False, comment="变化原因")
    before_score = Column(Integer, nullable=False)
    after_score = Column(Integer, nullable=False)


# ==================== 支付系统 ====================

class Payment(BaseModel):
    """支付记录表"""
    __tablename__ = "payments"

    order_id = Column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    amount = Column(Float, nullable=False, comment="支付金额")
    payment_method = Column(String(32), nullable=True, comment="wechat/alipay/manual")
    transaction_id = Column(String(128), nullable=True, comment="支付平台交易号")
    status = Column(String(20), default="pending", comment="pending/paid/refunded/released/manual_confirmed")
    type = Column(String(20), nullable=False, comment="payment/refund/release")
    raw_response = Column(JSON, default=dict, comment="支付平台原始响应JSON")


# ==================== Webhook 推送记录 ====================

class WebhookLog(BaseModel):
    """Webhook 推送记录表"""
    __tablename__ = "webhook_logs"

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_profiles.user_id"), nullable=False)
    event_type = Column(String(32), nullable=False, comment="demand_pushed / order_status_changed / etc")
    order_id = Column(UUID(as_uuid=True), nullable=True, comment="关联订单/需求 ID")
    webhook_url = Column(String(512), nullable=False)
    payload = Column(JSON, default=dict, comment="推送数据")
    status = Column(String(16), default="pending", comment="pending/success/failed")
    attempts = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    idempotency_key = Column(String(64), nullable=True, comment="幂等性 Key")
    response_code = Column(Integer, nullable=True)
    response_body = Column(Text, nullable=True)


# ==================== Agent 类目系统 ====================

class AgentCategory(BaseModel):
    """Agent 类目定义表"""
    __tablename__ = "agent_categories"

    name = Column(String(64), nullable=False, unique=True, comment="类目名称，如'文案生成'")
    code = Column(String(32), nullable=False, unique=True, comment="类目代码，如'copywriting'")
    description = Column(Text, nullable=True, comment="类目描述")
    icon = Column(String(256), nullable=True, comment="图标URL")
    sort_order = Column(Integer, default=0, comment="排序权重")
    is_active = Column(Boolean, default=True, comment="是否启用")


class AgentCategoryRelation(BaseModel):
    """Agent 与类目的多对多关联表"""
    __tablename__ = "agent_category_relations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_profiles.user_id"), nullable=False)
    category_id = Column(UUID(as_uuid=True), ForeignKey("agent_categories.id"), nullable=False)
    confidence = Column(Float, default=1.0, comment="Agent在该类目的置信度")
    price_min = Column(Float, nullable=True, comment="该类目最低接单价")
    price_max = Column(Float, nullable=True, comment="该类目最高接单价")
    max_concurrent = Column(Integer, default=5, comment="该类目最大并发数")
    delivery_hours = Column(Float, nullable=True, comment="该类目预计交付时间(小时)")


class AgentShowcase(BaseModel):
    """Agent 能力展示/双向市场表"""
    __tablename__ = "agent_showcase"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                        onupdate=lambda: datetime.now(timezone.utc))

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agent_profiles.user_id"), nullable=False, unique=True)
    portfolio = Column(JSON, default=list, comment="作品集URL列表")
    service_description = Column(Text, nullable=True, comment="服务描述（用于展示页）")
    tags = Column(JSON, default=list, comment="展示标签")
    rating_display = Column(Boolean, default=True, comment="是否显示评分")
