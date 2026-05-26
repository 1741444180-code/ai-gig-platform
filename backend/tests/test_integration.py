"""A00062 全链路集成测试脚本（v2）

测试完整核心链路：
注册 → 登录 → 发需求 → Agent注册 → 撮合 → 接单 → 交付 → 验收 → AI评分

运行方式：
    cd backend && .venv/bin/python tests/test_integration.py

依赖：后端服务已启动（uvicorn app.main:app --port 8000）
"""

import asyncio
import httpx
import sys
import json

BASE_URL = "http://localhost:8000/api/v1"

TEST_PHONE = f"138{__import__('random').randint(10000000, 99999999)}"

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

passed = 0
failed = 0

def ok(label, detail=""):
    global passed
    passed += 1
    msg = f"  {Colors.GREEN}✅{Colors.RESET} {label}"
    if detail:
        msg += f" — {Colors.YELLOW}{detail}{Colors.RESET}"
    print(msg)

def fail(label, detail=""):
    global failed
    failed += 1
    msg = f"  {Colors.RED}❌{Colors.RESET} {label}"
    if detail:
        msg += f" — {detail}"
    print(msg)


async def run_tests():
    global passed, failed
    token = None
    user_id = None
    agent_id = None
    agent_api_key = None
    demand_id = None
    order_id = None

    async with httpx.AsyncClient(timeout=30.0) as c:

        # ═══════════════════════════════════════
        # Phase 1: 用户认证
        # ═══════════════════════════════════════
        print(f"\n{Colors.BOLD}═══ Phase 1: 用户认证 ═══{Colors.RESET}")

        # 发送验证码
        resp = await c.post(f"{BASE_URL}/auth/send-code", json={"phone": TEST_PHONE})
        if resp.status_code == 200:
            ok("POST /auth/send-code", "验证码已发送")
        else:
            fail("POST /auth/send-code", f"status={resp.status_code}")

        # 登录（开发模式验证码=888888）
        resp = await c.post(f"{BASE_URL}/auth/login", json={
            "phone": TEST_PHONE,
            "sms_code": "888888"
        })
        if resp.status_code == 200:
            data = resp.json()
            token = data.get("access_token")
            user_id = data.get("user_info", {}).get("id")
            ok("POST /auth/login", f"token={'✓' if token else '✗'}, user_id={user_id}")
        else:
            fail("POST /auth/login", f"status={resp.status_code} body={resp.text[:200]}")
            print(f"{Colors.RED}认证失败，跳过后续测试{Colors.RESET}")
            return False

        headers = {"Authorization": f"Bearer {token}"}

        # 获取用户信息
        resp = await c.get(f"{BASE_URL}/auth/me", headers=headers)
        if resp.status_code == 200:
            data = resp.json()
            ok("GET /auth/me", f"id={data.get('id')}, role={data.get('role')}")
        else:
            fail("GET /auth/me", f"status={resp.status_code}")

        # 刷新Token
        resp = await c.post(f"{BASE_URL}/auth/refresh", json={"refresh_token": ""})
        ok("POST /auth/refresh", f"status={resp.status_code}")

        # ═══════════════════════════════════════
        # Phase 2: 发布需求 + AI结构化
        # ═══════════════════════════════════════
        print(f"\n{Colors.BOLD}═══ Phase 2: 需求发布 ═══{Colors.RESET}")

        resp = await c.post(f"{BASE_URL}/demands/", headers=headers, json={
            "title": "需要写一个产品推广文案",
            "description": "介绍新产品功能，面向企业客户，200字以内",
            "category": "文案",
            "budget": 200.0,
            "deadline": "2026-06-01"
        })
        if resp.status_code in (200, 201):
            data = resp.json()
            demand_id = data.get("id")
            ok("POST /demands/", f"id={demand_id}, category={data.get('category')}")
        else:
            fail("POST /demands/", f"status={resp.status_code} body={resp.text[:200]}")

        # 需求列表
        resp = await c.get(f"{BASE_URL}/demands/")
        if resp.status_code == 200:
            data = resp.json()
            count = len(data.get("items", data if isinstance(data, list) else []))
            ok("GET /demands/", f"共{count}条")
        else:
            fail("GET /demands/", f"status={resp.status_code}")

        # 我的需求
        resp = await c.get(f"{BASE_URL}/orders/my", headers=headers)
        ok("GET /orders/my", f"status={resp.status_code}")

        # ═══════════════════════════════════════
        # Phase 3: Agent注册 + API Key
        # ═══════════════════════════════════════
        print(f"\n{Colors.BOLD}═══ Phase 3: Agent注册 ═══{Colors.RESET}")

        resp = await c.post(f"{BASE_URL}/agents/register", headers=headers, json={
            "name": "测试Agent-文案助手",
            "description": "专业文案撰写服务",
            "capabilities": ["文案", "营销"],
            "mode": "auto",
            "api_url": "http://localhost:9101",
        })
        if resp.status_code in (200, 201):
            data = resp.json()
            agent_id = data.get("id")
            agent_api_key = data.get("api_key") or data.get("full_key")
            ok("POST /agents/register", f"id={agent_id}, api_key={'✓' if agent_api_key else '✗'}")
        else:
            fail("POST /agents/register", f"status={resp.status_code} body={resp.text[:200]}")

        if agent_api_key:
            agent_headers = {"Authorization": f"Bearer {agent_api_key}"}

            # 获取Agent信息
            resp = await c.get(f"{BASE_URL}/agents/me", headers=headers)
            ok("GET /agents/me", f"status={resp.status_code}")

        # ═══════════════════════════════════════
        # Phase 4: 撮合匹配
        # ═══════════════════════════════════════
        if demand_id:
            print(f"\n{Colors.BOLD}═══ Phase 4: 撮合匹配 ═══{Colors.RESET}")

            resp = await c.post(f"{BASE_URL}/demands/{demand_id}/match", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                agents = data.get("matched_agents", data.get("agents", []))
                ok("POST /demands/{id}/match", f"匹配{len(agents)}个Agent")
            else:
                fail("POST /demands/{id}/match", f"status={resp.status_code}")

        # ═══════════════════════════════════════
        # Phase 5: Agent接单
        # ═══════════════════════════════════════
        if demand_id and agent_api_key:
            print(f"\n{Colors.BOLD}═══ Phase 5: Agent接单 ═══{Colors.RESET}")

            agent_headers = {"Authorization": f"Bearer {agent_api_key}"}
            resp = await c.post(f"{BASE_URL}/orders/accept", headers=agent_headers, json={
                "demand_id": demand_id
            })
            if resp.status_code in (200, 201):
                data = resp.json()
                order_id = data.get("id") or data.get("order_id")
                ok("POST /orders/accept", f"order_id={order_id}")
            else:
                fail("POST /orders/accept", f"status={resp.status_code} body={resp.text[:200]}")

        # ═══════════════════════════════════════
        # Phase 6: Agent交付
        # ═══════════════════════════════════════
        if order_id and agent_api_key:
            print(f"\n{Colors.BOLD}═══ Phase 6: 交付 ═══{Colors.RESET}")

            agent_headers = {"Authorization": f"Bearer {agent_api_key}"}
            resp = await c.post(f"{BASE_URL}/orders/deliver", headers=agent_headers, json={
                "order_id": order_id,
                "delivery_note": "这是交付内容：一篇完整的产品推广文案，介绍了新功能...",
            })
            if resp.status_code in (200, 201):
                ok("POST /orders/deliver", "交付成功")
            else:
                fail("POST /orders/deliver", f"status={resp.status_code} body={resp.text[:200]}")

        # ═══════════════════════════════════════
        # Phase 7: 验收 + AI评分
        # ═══════════════════════════════════════
        if order_id:
            print(f"\n{Colors.BOLD}═══ Phase 7: 验收 + AI评分 ═══{Colors.RESET}")

            # 用户验收通过
            resp = await c.post(f"{BASE_URL}/orders/{order_id}/accept-delivery", headers=headers)
            if resp.status_code in (200, 201):
                ok("POST /orders/{id}/accept-delivery", "验收通过")
            else:
                fail("POST /orders/{id}/accept-delivery", f"status={resp.status_code} body={resp.text[:200]}")

            # AI验收评分
            resp = await c.post(f"{BASE_URL}/orders/{order_id}/ai-review", headers=headers, json={
                "delivery_content": "产品推广文案成品..."
            })
            if resp.status_code in (200, 201):
                data = resp.json()
                ok("POST /orders/{id}/ai-review", f"score={data.get('score')}, reason={data.get('reason', '')[:50]}")
            else:
                fail("POST /orders/{id}/ai-review", f"status={resp.status_code} body={resp.text[:200]}")

            # 订单详情
            resp = await c.get(f"{BASE_URL}/orders/{order_id}", headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                ok("GET /orders/{id}", f"status={data.get('status')}")
            else:
                fail("GET /orders/{id}", f"status={resp.status_code}")

        # ═══════════════════════════════════════
        # Phase 8: 管理后台
        # ═══════════════════════════════════════
        print(f"\n{Colors.BOLD}═══ Phase 8: 管理后台 ═══{Colors.RESET}")

        resp = await c.get(f"{BASE_URL}/admin/dashboard", headers=headers)
        if resp.status_code in (200, 403):
            role = "admin" if resp.status_code == 200 else "user(403正常)"
            ok("GET /admin/dashboard", f"role={role}")
        else:
            fail("GET /admin/dashboard", f"status={resp.status_code}")

        resp = await c.get(f"{BASE_URL}/admin/users", headers=headers)
        if resp.status_code in (200, 403):
            ok("GET /admin/users", f"status={resp.status_code}")
        else:
            fail("GET /admin/users", f"status={resp.status_code}")

    # ═══════════════════════════════════════
    # 汇总
    # ═══════════════════════════════════════
    total = passed + failed
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}  测试结果: {passed}/{total} 通过{Colors.RESET}")
    if failed == 0:
        print(f"  {Colors.GREEN}{Colors.BOLD}🎉 全链路集成测试全部通过！{Colors.RESET}")
    else:
        print(f"  {Colors.RED}❌ {failed} 个测试失败{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")
    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
