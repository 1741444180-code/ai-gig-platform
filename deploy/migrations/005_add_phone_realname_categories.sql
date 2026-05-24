-- Migration: 005 - 手机号验证+实名认证+类目表
-- Date: 2026-05-23
-- Description: users表新增手机号验证和实名认证字段，新增agent类目和展示表

-- ========================
-- Part 1: users 表字段新增/修改
-- ========================

-- 新增 phone_verified 字段
ALTER TABLE users ADD COLUMN IF NOT EXISTS phone_verified BOOLEAN DEFAULT FALSE;

-- 新增 real_name 字段（预留，实名认证后填充）
ALTER TABLE users ADD COLUMN IF NOT EXISTS real_name VARCHAR(64);

-- 新增 real_name_verified 字段（预留）
ALTER TABLE users ADD COLUMN IF NOT EXISTS real_name_verified BOOLEAN DEFAULT FALSE;

-- 新增 id_card_hash 字段（预留，身份证号哈希）
ALTER TABLE users ADD COLUMN IF NOT EXISTS id_card_hash VARCHAR(64);

-- phone 改为 NOT NULL（MVP阶段无已有生产数据，直接执行）
ALTER TABLE users ALTER COLUMN phone SET NOT NULL;
ALTER TABLE users ALTER COLUMN phone SET DEFAULT '';

-- ========================
-- Part 2: agent_categories 类目表
-- ========================

CREATE TABLE IF NOT EXISTS agent_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(64) NOT NULL UNIQUE,
    code VARCHAR(32) NOT NULL UNIQUE,
    description TEXT,
    icon VARCHAR(256),
    sort_order INTEGER DEFAULT 0,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 插入初始类目数据
INSERT INTO agent_categories (name, code, description, sort_order) VALUES
    ('文案生成', 'copywriting', '文案撰写、翻译、报告等', 1),
    ('图像生成', 'image_generation', '文生图、图生图、设计等', 2),
    ('视频制作', 'video', '短视频、剪辑、短剧等', 3),
    ('代码开发', 'development', '小程序、网页、脚本等', 4),
    ('数据分析', 'data_analysis', '数据分析、可视化、爬虫等', 5),
    ('设计', 'design', 'Logo、海报、UI设计等', 6),
    ('翻译', 'translation', '中英互译等', 7),
    ('其他', 'other', '其他类型需求', 8)
ON CONFLICT (code) DO NOTHING;

-- ========================
-- Part 3: agent_category_relations Agent-类目关联表
-- ========================

CREATE TABLE IF NOT EXISTS agent_category_relations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_profiles(user_id),
    category_id UUID NOT NULL REFERENCES agent_categories(id),
    confidence FLOAT DEFAULT 1.0,
    price_min FLOAT,
    price_max FLOAT,
    max_concurrent INTEGER DEFAULT 5,
    delivery_hours FLOAT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(agent_id, category_id)
);

CREATE INDEX idx_agent_category_relations_agent ON agent_category_relations(agent_id);
CREATE INDEX idx_agent_category_relations_category ON agent_category_relations(category_id);

-- ========================
-- Part 4: agent_showcase Agent展示页（双向市场）
-- ========================

CREATE TABLE IF NOT EXISTS agent_showcase (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL UNIQUE REFERENCES agent_profiles(user_id),
    portfolio JSONB DEFAULT '[]',
    service_description TEXT,
    tags JSONB DEFAULT '[]',
    rating_display BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
