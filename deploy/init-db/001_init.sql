-- A00062 AI Gig Platform - 数据库初始化
-- PostgreSQL 16 + pgvector

-- 启用 pgvector 扩展
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    openid VARCHAR(128) UNIQUE,
    unionid VARCHAR(128),
    phone VARCHAR(20) UNIQUE,
    nickname VARCHAR(64),
    avatar VARCHAR(512),
    role VARCHAR(16) DEFAULT 'user',
    status SMALLINT DEFAULT 1,
    balance FLOAT DEFAULT 0.0,
    credit_score INTEGER DEFAULT 100,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent能力卡
CREATE TABLE IF NOT EXISTS agent_profiles (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    description TEXT,
    tags JSONB DEFAULT '[]',
    capabilities JSONB DEFAULT '{}',
    base_price FLOAT,
    api_key VARCHAR(256) UNIQUE NOT NULL,
    webhook_url VARCHAR(512),
    auto_accept BOOLEAN DEFAULT FALSE,
    daily_limit INTEGER DEFAULT 0,
    today_orders INTEGER DEFAULT 0,
    status SMALLINT DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE UNIQUE INDEX idx_agent_profiles_user_id ON agent_profiles(user_id);
CREATE INDEX idx_agent_profiles_api_key ON agent_profiles(api_key);
CREATE INDEX idx_agent_profiles_tags ON agent_profiles USING GIN(tags);
CREATE INDEX idx_agent_profiles_status ON agent_profiles(status);

-- 需求表
CREATE TABLE IF NOT EXISTS requirements (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    title VARCHAR(256) NOT NULL,
    description TEXT NOT NULL,
    category VARCHAR(64),
    tags JSONB DEFAULT '[]',
    attachments JSONB DEFAULT '[]',
    budget FLOAT,
    urgency SMALLINT DEFAULT 1,
    structured_data JSONB DEFAULT '{}',
    status VARCHAR(32) DEFAULT 'draft',
    match_mode VARCHAR(16) DEFAULT 'auto',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_requirements_user_id ON requirements(user_id);
CREATE INDEX idx_requirements_status ON requirements(status);
CREATE INDEX idx_requirements_category ON requirements(category);
CREATE INDEX idx_requirements_tags ON requirements USING GIN(tags);
CREATE INDEX idx_requirements_created ON requirements(created_at DESC);

-- 需求embedding向量（用于语义匹配）
CREATE TABLE IF NOT EXISTS requirement_embeddings (
    requirement_id UUID PRIMARY KEY REFERENCES requirements(id) ON DELETE CASCADE,
    embedding vector(1536),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Agent能力embedding向量
CREATE TABLE IF NOT EXISTS agent_embedding (
    agent_id UUID PRIMARY KEY REFERENCES agent_profiles(user_id) ON DELETE CASCADE,
    embedding vector(1536),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 报价表
CREATE TABLE IF NOT EXISTS requirement_quotes (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requirement_id UUID REFERENCES requirements(id),
    agent_id UUID REFERENCES users(id),
    price FLOAT NOT NULL,
    delivery_hours FLOAT,
    message TEXT,
    status VARCHAR(16) DEFAULT 'pending',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_requirement_quotes_requirement ON requirement_quotes(requirement_id);
CREATE INDEX idx_requirement_quotes_agent ON requirement_quotes(agent_id);

-- 订单表
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    requirement_id UUID REFERENCES requirements(id),
    user_id UUID REFERENCES users(id),
    agent_id UUID REFERENCES users(id),
    amount FLOAT NOT NULL,
    platform_fee FLOAT DEFAULT 0.0,
    agent_income FLOAT NOT NULL,
    status VARCHAR(32) DEFAULT 'pending',
    payment_method VARCHAR(32),
    payment_id VARCHAR(128),
    deliverables JSONB DEFAULT '[]',
    delivery_message TEXT,
    ai_review_score FLOAT,
    user_confirm SMALLINT,
    modify_count INTEGER DEFAULT 0,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_orders_user_id ON orders(user_id);
CREATE INDEX idx_orders_agent_id ON orders(agent_id);
CREATE INDEX idx_orders_requirement ON orders(requirement_id);
CREATE INDEX idx_orders_status ON orders(status);
CREATE INDEX idx_orders_created ON orders(created_at DESC);

-- 评价表
CREATE TABLE IF NOT EXISTS reviews (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_id UUID REFERENCES orders(id),
    user_id UUID REFERENCES users(id),
    agent_id UUID REFERENCES users(id),
    rating SMALLINT NOT NULL CHECK (rating >= 1 AND rating <= 5),
    comment TEXT,
    is_anonymous BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_reviews_order ON reviews(order_id);
CREATE INDEX idx_reviews_agent ON reviews(agent_id);

-- 信誉记录表
CREATE TABLE IF NOT EXISTS credit_records (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    user_id UUID REFERENCES users(id),
    order_id UUID REFERENCES orders(id),
    change INTEGER NOT NULL,
    reason VARCHAR(256) NOT NULL,
    before_score INTEGER NOT NULL,
    after_score INTEGER NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_credit_records_user ON credit_records(user_id);
CREATE INDEX idx_credit_records_created ON credit_records(created_at DESC);

-- 更新updated_at的触发器函数
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 为所有表添加触发器
CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agent_profiles_updated_at BEFORE UPDATE ON agent_profiles FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_requirements_updated_at BEFORE UPDATE ON requirements FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_requirement_quotes_updated_at BEFORE UPDATE ON requirement_quotes FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_orders_updated_at BEFORE UPDATE ON orders FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_reviews_updated_at BEFORE UPDATE ON reviews FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_requirement_embeddings_updated_at BEFORE UPDATE ON requirement_embeddings FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
CREATE TRIGGER update_agent_embedding_updated_at BEFORE UPDATE ON agent_embedding FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
