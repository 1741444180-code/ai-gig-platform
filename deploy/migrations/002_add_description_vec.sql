-- Migration: 002 - 添加Agent能力描述向量字段
-- Date: 2026-05-22
-- Description: 匹配引擎需要 description_vec 列在 agent_profiles 表上做语义匹配

ALTER TABLE agent_profiles
ADD COLUMN IF NOT EXISTS description_vec vector(1536) NULL;
