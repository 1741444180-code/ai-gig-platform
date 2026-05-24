-- Migration: 004 - Agent API Key 管理 + 沙箱环境
-- Date: 2026-05-22
-- Description: 新增 agent_api_keys 表，支持多Key、SHA-256存储、Scope权限、沙箱环境

CREATE TABLE IF NOT EXISTS agent_api_keys (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id UUID NOT NULL REFERENCES agent_profiles(user_id),
    key_name VARCHAR(64),
    key_prefix VARCHAR(8) NOT NULL,
    key_hash VARCHAR(64) NOT NULL UNIQUE,  -- SHA-256 哈希值
    scope VARCHAR(32) DEFAULT 'full',       -- full / read / sandbox / sandbox_test
    is_active BOOLEAN DEFAULT TRUE,
    is_sandbox BOOLEAN DEFAULT FALSE,
    last_used_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_api_keys_agent_id ON agent_api_keys(agent_id);
CREATE INDEX idx_api_keys_hash ON agent_api_keys(key_hash);
CREATE INDEX idx_api_keys_active ON agent_api_keys(is_active);
