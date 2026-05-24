-- Migration: 001 - 添加密码哈希字段到 users 表
-- Date: 2026-05-22
-- Description: JWT 认证模块新增手机号+密码注册/登录功能，需要 password_hash 列

ALTER TABLE users
ADD COLUMN IF NOT EXISTS password_hash VARCHAR(256) NULL COMMENT '密码哈希(bcrypt)';

-- 索引已在原 phone 列上，无需额外索引
