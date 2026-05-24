-- Migration: 003 - 支付模块
-- Date: 2026-05-22
-- Description: 新增 payments 表，支持支付创建/回调/查询/退款

CREATE TABLE IF NOT EXISTS payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id),
    user_id UUID NOT NULL REFERENCES users(id),
    amount FLOAT NOT NULL,
    payment_method VARCHAR(32),          -- wechat/alipay/manual
    transaction_id VARCHAR(128),         -- 支付平台交易号
    status VARCHAR(20) DEFAULT 'pending', -- pending/paid/refunded/released/manual_confirmed
    type VARCHAR(20) NOT NULL,           -- payment/refund/release
    raw_response JSONB DEFAULT '{}',     -- 支付平台原始响应
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_order_id ON payments(order_id);
CREATE INDEX idx_payments_user_id ON payments(user_id);
CREATE INDEX idx_payments_status ON payments(status);
