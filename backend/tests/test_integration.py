"""A00062 全链路集成测试脚本

测试完整核心链路：注册 → 登录 → 发需求 → Agent注册 → 创建API Key → 撮合 → 接单 → 交付 → 验收

运行方式（需先 docker compose up -d 启动服务）:
    python3 tests/test_integration.py

依赖：Python 3.11+, httpx
"""

import asyncio
import httpx
import sys

BASE_URL = "http://localhost:8000/api/v1"

# 测试数据
TEST_PHONE = f"138{__import__('random').randint(10000000, 99999999)}"
TEST_PASSWORD = "Test@123456"

class Colors:
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    RESET = "\033[0m"
    BOLD = "\033[1m"

passed = 0
failed = 0

def assert_status(resp, expected, label):
    global passed, failed
    if resp.status_code in (expected if isinstance(expected, (list, tuple)) else [expected]):
        passed += 1
        print(f"  {Colors.GREEN}✅ PASS{Colors.RESET}: {label} (status={resp.status_code})")
    else:
        failed += 1
        body = resp.text[:200]
        print(f"  {Colors.RED}❌ FAIL{Colors.RESET}: {label} (status={resp.status_code} != {expected})\n     Body: {body}")

def assert_json_key(resp, key, label):
    global passed, failed
    try:
        data = resp.json()
        if key in data:
            passed += 1
            print(f"  {Colors.GREEN}✅ PASS{Colors.RESET}: {label} (found '{key}')")
            return data
        else:
            failed += 1
            print(f"  {Colors.RED}❌ FAIL{Colors.RESET}: {label} (missing '{key}')")
    except Exception as e:
        failed += 1
        print(f"  {Colors.RED}❌ FAIL{Colors.RESET}: {label} ({e})")
    return {}

async def run_tests():
    global passed, failed
    token = None
    user_id = None
    agent_api_key = None
    requirement_id = None
    order_id = None

    async with httpx.AsyncClient(timeout=30.0) as client:
        # ═══════════════════════════════════════════════
        # Phase 1: 用户注册 + 登录
        # ═══════════════════════════════════════════════
        print(f"\n{Colors.BOLD}═══ Phase 1: 用户认证 ═══{Colors.RESET}")

        # 注册
        resp = await client.post(f"{BASE_URL}/auth/register", json={
            "phone": TEST_PHONE,
            "password": TEST_PASSWORD,
            "nickname": "测试用户"
        })
        data = assert_json_key(resp, "access_token", "POST /auth/register")
        token = data.get("access_token")
        assert_status(resp, 200, "POST /auth/register")

        # 登录
        resp = await client.post(f"{BASE_URL}/auth/login", json={
            "phone": TEST_PHONE,
            "password": TEST_PASSWORD,
        })
        data = assert_json_key(resp, "access_token", "POST /auth/login")
        token = data.get("access_token") or token
        assert_status(resp, 200, "POST /auth/login")

        # 获取用户信息
        headers = {"Authorization": f"Bearer {token}"}
        resp = await client.get(f"{BASE_URL}/auth/me", headers=headers)
        data = assert_json_key(resp, "id", "GET /auth/me")
        user_id = data.get("id")
        assert_status(resp, 200, "GET /auth/me")

        # Token 刷新
        refresh_token = data.get("refresh_token", "")
        resp = await client.post(f"{BASE_URL}/auth/refresh", json={
            "refresh_token": refresh_token if refresh_token else token
        })
        assert_status(resp, 200, "POST /auth/refresh")

        # ═══════════════════════════════════════════════
        # Phase 2: 发布需求
        # ═══════════════════════════════════════════════
        print(f"\n{Colors.BOLD}═══ Phase 2: 需求发布 ═══{Colors.RESET}")

        resp = await client.post(f"{BASE_URL}/requirements/", headers=headers, json={
            "title": "测试需求：设计一个logo",
            "description": "帮我设计一个简约风格的咖啡店logo，需要包含咖啡元素，配色以棕色和白色为主",
            "budget": 50.0,
            "urgency": 1,
            "match_mode": "auto"
        })
        data = assert_json_key(resp, "id", "POST /requirements/")
        requirement_id = data.get("id")
        assert_status(resp, 201, "POST /requirements/")

        # 需求列表
        resp = await client.get(f"{BASE_URL}/requirements/")
        assert_status(resp, 200, "GET /requirements/ (public)")

        resp = await client.get(f"{BASE_URL}/requirements/mine", headers=headers)
        assert_status(resp, 200, "GET /requirements/mine")

        # 需求详情
        if requirement_id:
            resp = await client.get(f"{BASE_URL}/requirements/{requirement_id}")
            assert_status(resp, 200, "GET /requirements/{id}")

        # ═══════════════════════════════════════════════
        # Phase 3: Agent 注册 + API Key
        # ═══════════════════════════════════════════════
        print(f"\n{Colors.BOLD}═══ Phase 3: Agent 注册 ═══{Colors.RESET}")

        resp = await client.post(f"{BASE_URL}/agents/register", headers=headers, json={
            "agent": {
                "name": "测试Agent-Logo设计",
                "description": "专业AI Logo设计服务，支持多种风格",
                "tags": ["图像设计", "AI生图", "Logo设计", "咖啡"],
                "capabilities": {"style": ["简约", "日系", "欧美"]},
                "base_price": 30.0,
                "auto_accept": False,
                "daily_limit": 10
            }
        })
        assert_status(resp, 200, "POST /agents/register")
        assert_json_key(resp, "id", "POST /agents/register")

        # 创建 API Key
        resp = await client.post(f"{BASE_URL}/agents/api-keys", headers=headers, json={
            "key_name": "集成测试Key",
            "scope": "full",
            "is_sandbox": False
        })
        data = assert_json_key(resp, "full_key", "POST /agents/api-keys")
        agent_api_key = data.get("full_key")
        assert_status(resp, 200, "POST /agents/api-keys")

        # 获取 API Key 列表
        resp = await client.get(f"{BASE_URL}/agents/api-keys", headers=headers)
        assert_status(resp, 200, "GET /agents/api-keys")

        # 获取 Agent 信息
        resp = await client.get(f"{BASE_URL}/agents/me", headers=headers)
        assert_status(resp, 200, "GET /agents/me")

        # ═══════════════════════════════════════════════
        # Phase 4: 撮合匹配
        # ═══════════════════════════════════════════════
        if requirement_id:
            print(f"\n{Colors.BOLD}═══ Phase 4: 撮合匹配 ═══{Colors.RESET}")
            resp = await client.post(
                f"{BASE_URL}/requirements/{requirement_id}/match",
                headers=headers,
                params={"limit": 5}
            )
            assert_status(resp, 200, "POST /requirements/{id}/match")

        # ═══════════════════════════════════════════════
        # Phase 5: Agent 接单 + 交付
        # ═══════════════════════════════════════════════
        if agent_api_key and requirement_id:
            print(f"\n{Colors.BOLD}═══ Phase 5: Agent 接单 + 交付 ═══{Colors.RESET}")

            # 接单
            resp = await client.post(f"{BASE_URL}/agents/api/accept_order", json={
                "api_key": agent_api_key,
                "requirement_id": requirement_id
            })
            data = assert_json_key(resp, "order_id", "POST /agents/api/accept_order")
            order_id = data.get("order_id")
            assert_status(resp, 200, "POST /agents/api/accept_order")

            # 提交交付物
            if order_id:
                resp = await client.post(f"{BASE_URL}/agents/api/submit_delivery", json={
                    "api_key": agent_api_key,
                    "order_id": order_id,
                    "deliverables": ["https://example.com/logo-v1.png"],
                    "delivery_message": "设计完成，简约咖啡店logo"
                })
                assert_status(resp, 200, "POST /agents/api/submit_delivery")

                # 查询订单
                resp = await client.get(
                    f"{BASE_URL}/agents/api/orders/{order_id}",
                    params={"api_key": agent_api_key}
                )
                assert_status(resp, 200, "GET /agents/api/orders/{id}")

        # ═══════════════════════════════════════════════
        # Phase 6: 验收确认
        # ═══════════════════════════════════════════════
        if order_id:
            print(f"\n{Colors.BOLD}═══ Phase 6: 验收确认 ═══{Colors.RESET}")

            resp = await client.post(
                f"{BASE_URL}/orders/{order_id}/confirm",
                headers=headers
            )
            assert_status(resp, 200, "POST /orders/{id}/confirm")

            # 查询订单状态
            resp = await client.get(
                f"{BASE_URL}/orders/{order_id}/status",
                headers=headers
            )
            assert_status(resp, 200, "GET /orders/{id}/status")

        # ═══════════════════════════════════════════════
        # Phase 7: 管理后台
        # ═══════════════════════════════════════════════
        print(f"\n{Colors.BOLD}═══ Phase 7: 管理后台 ═══{Colors.RESET}")
        resp = await client.get(f"{BASE_URL}/admin/dashboard", headers=headers)
        assert_status(resp, [200, 403], "GET /admin/dashboard")  # 200 if admin, 403 if not

    # ═══════════════════════════════════════════════
    # 结果汇总
    # ═══════════════════════════════════════════════
    total = passed + failed
    print(f"\n{Colors.BOLD}{'='*60}{Colors.RESET}")
    print(f"{Colors.BOLD}测试结果汇总{Colors.RESET}")
    print(f"  ✅ 通过: {passed}/{total}")
    print(f"  ❌ 失败: {failed}/{total}")
    if failed == 0:
        print(f"\n  {Colors.GREEN}{Colors.BOLD}🎉 全链路集成测试通过！{Colors.RESET}")
    else:
        print(f"\n  {Colors.RED}💥 有 {failed} 个测试失败，请检查日志{Colors.RESET}")
    print(f"{Colors.BOLD}{'='*60}{Colors.RESET}")

    return failed == 0

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    sys.exit(0 if success else 1)
