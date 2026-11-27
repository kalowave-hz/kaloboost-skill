"""Verify real MCP discovery/calls against the local Kaloboost mock."""

import json
import os
import sys
from pathlib import Path

import pytest

pytest.importorskip("mcp")

import anyio
from conftest import err, page
from mcp import Client
from mcp.client.stdio import StdioServerParameters

from kaloboost.mcp_server import TOOLS, create_server

DM = {"ids": ["111", "222"], "shop": "s", "operator": "a@b.com", "template": "T1"}


def call(name, arguments):
    async def go():
        async with Client(create_server()) as client:
            return await client.call_tool(name, arguments)

    return anyio.run(go)


def test_discovery_and_list(env, capsys):
    env.responses["/outreach-tasks"] = page([{"outreach_task_id": "t1"}], cursor="c2")

    async def check():
        async with Client(create_server()) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            assert set(tools) == set(TOOLS)
            assert not any(name.startswith("config_") for name in tools)
            assert {"resolve_job_create", "webhook_rotate_secret"} <= set(tools)
            schema = tools["outreach_list"].input_schema
            assert schema["additionalProperties"] is False
            assert "json" not in schema["properties"]
            limit = schema["properties"]["limit"]
            assert (limit["minimum"], limit["maximum"]) == (1, 100)
            assert "file" not in tools["creator_resolve"].input_schema["properties"]
            assert tools["creator_get"].input_schema["required"] == ["ids"]
            assert tools["outreach_get"].input_schema["required"] == ["outreach_task_id"]
            assert tools["outreach_list"].annotations.read_only_hint
            assert not tools["outreach_create"].annotations.read_only_hint
            assert tools["outreach_cancel"].annotations.destructive_hint
            result = await client.call_tool("outreach_list", {"shop": "s", "limit": 5})
            assert not result.is_error
            assert result.structured_content == {
                "data": {"data": [{"outreach_task_id": "t1"}], "next_cursor": "c2"}
            }
            assert json.loads(result.content[0].text) == result.structured_content

    anyio.run(check)
    assert capsys.readouterr().out == ""
    method, path, query, headers, _ = env.requests[0]
    assert (method, path) == ("GET", "/outreach-tasks")
    assert headers["secret-key"] == "test-key"
    assert query["shop_id"] == "s" and query["limit"] == "5"


@pytest.mark.parametrize("arguments", [
    {"shop": "s", "limit": "five"}, {"shop": "s", "unknown": True}, {"shop": "s", "json": True},
    {"shop": "s", "limit": 0}, {"shop": "s", "limit": 101}, {"shop": "s", "status": "NOPE"},
])
def test_invalid_arguments_do_not_query(env, arguments):
    assert call("sample_list", arguments).is_error
    assert env.requests == []


def test_missing_shop_is_usage_error(env):
    result = call("outreach_list", {})
    assert result.is_error
    assert result.structured_content["kind"] == "parameter"
    assert any("boost shops" in line for line in result.structured_content["help"])
    assert env.requests == []


def test_write_is_dry_run_until_yes(env, capsys):
    result = call("outreach_create", DM)
    assert not result.is_error
    assert env.requests == []
    preview = result.structured_content["data"]["dry_run"]
    ext = preview["body"]["external_task_id"]
    assert preview["idempotency_key"] == ext
    assert f"external_id='{ext}'" in result.structured_content["next"]

    env.responses["/outreach-tasks"] = (202, {"data": {"outreach_task_id": "t9", "total_count": 2}})
    sent = call("outreach_create", dict(DM, yes=True, external_id=ext))
    assert not sent.is_error
    assert sent.structured_content == {"data": {"outreach_task_id": "t9", "total_count": 2}}
    _, path, _, headers, body = env.requests[0]
    assert path == "/outreach-tasks" and headers["idempotency-key"] == ext
    assert [r["creator_oecuid"] for r in body["recipients"]] == ["111", "222"]
    assert capsys.readouterr().out == ""


def test_webhook_dry_run_names_idempotency_key(env):
    result = call("webhook_rotate_secret", {"endpoint_id": "e1"})
    key = result.structured_content["data"]["dry_run"]["idempotency_key"]
    assert f"idempotency_key='{key}'" in result.structured_content["next"]
    assert env.requests == []


def test_create_template_dry_run_needs_only_yes(env):
    result = call("outreach_create_template", {"shop": "s", "name": "T", "text": ["hi"]})
    assert result.structured_content["data"]["dry_run"]["body"]["dm"] == {"segments": [{"type": "TEXT", "text": "hi"}]}
    assert result.structured_content["next"].endswith("plus yes=true")
    assert env.requests == []


def test_missing_key_is_actionable(env, monkeypatch):
    monkeypatch.delenv("KALODATA_API_KEY")
    result = call("capabilities", {})
    assert result.is_error
    assert result.structured_content["kind"] == "auth"
    assert result.structured_content["help"]
    assert env.requests == []


def test_upstream_error_is_tool_error(env):
    env.responses["/capabilities"] = err(401, "INVALID_API_KEY")
    result = call("capabilities", {})
    assert result.is_error
    assert result.structured_content["kind"] == "auth"


def test_concurrent_calls_keep_results_separate(env):
    env.responses["/shops"] = page([{"shop_id": "s1"}])
    env.responses["/capabilities"] = {"data": {"capabilities": {"outreach": "AVAILABLE"}}}

    async def check():
        async with Client(create_server()) as client:
            results = {}

            async def run(name):
                results[name] = (await client.call_tool(name, {})).structured_content

            async with anyio.create_task_group() as group:
                group.start_soon(run, "shops")
                group.start_soon(run, "capabilities")
            assert results == {
                "shops": {"data": {"data": [{"shop_id": "s1"}], "next_cursor": None}},
                "capabilities": {"data": {"capabilities": {"outreach": "AVAILABLE"}}},
            }

    anyio.run(check)


@pytest.mark.parametrize("mode", ["auto", "legacy"])
def test_real_stdio_process(env, mode):
    env.responses["/capabilities"] = {"data": {"shop_regions": ["US"]}}
    scripts = Path(__file__).resolve().parents[1] / "skills" / "kaloboost" / "scripts"
    process_env = dict(os.environ, PYTHONPATH=str(scripts))

    async def check():
        async with Client(StdioServerParameters(
            command=sys.executable, args=["-m", "kaloboost.mcp_server"], env=process_env,
        ), mode=mode) as client:
            assert len((await client.list_tools()).tools) == len(TOOLS)
            result = await client.call_tool("capabilities", {})
            assert not result.is_error
            assert result.structured_content == {"data": {"shop_regions": ["US"]}}

    anyio.run(check)


def test_shop_order_tools(env):
    assert {"shop_order_list", "shop_return_list", "shop_auth_create"} <= set(TOOLS)
    env.responses["/shop-orders"] = page([{"channel_order_id": "o1"}], cursor="c9")
    env.responses["/shop-authorization-links"] = {"data": {"authorization_url": "https://x", "expires_at": "t"}}

    async def check():
        async with Client(create_server()) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            limit = tools["shop_return_list"].input_schema["properties"]["limit"]
            assert (limit["minimum"], limit["maximum"], limit["default"]) == (10, 50, 20)
            assert tools["shop_order_list"].annotations.read_only_hint
            assert not tools["shop_auth_create"].annotations.read_only_hint
            assert not tools["shop_auth_create"].annotations.destructive_hint
            result = await client.call_tool("shop_order_list", {"shop": "s", "status": "DELIVERED"})
            assert result.structured_content == {"data": {"data": [{"channel_order_id": "o1"}], "next_cursor": "c9"}}
            result = await client.call_tool("shop_auth_create", {"shop": "806"})
            assert not result.is_error
            assert result.structured_content == {"data": {"authorization_url": "https://x", "expires_at": "t"}}
            bad = await client.call_tool("shop_return_list", {"shop": "s", "limit": 9})
            assert bad.is_error

    anyio.run(check)
    assert [r[1] for r in env.requests] == ["/shop-orders", "/shop-authorization-links"]
    assert env.requests[0][2]["status"] == "DELIVERED"
    assert env.requests[1][4] == {"shop_id": "806"}


def test_coupon_promotion_diagnose_tools(env):
    assert {"coupon_list", "coupon_get", "promotion_list", "promotion_get", "product_diagnose"} <= set(TOOLS)
    env.responses["/shop-coupons"] = page([{"channel_coupon_id": "c1"}], cursor="c2")

    async def check():
        async with Client(create_server()) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            for name in ("coupon_list", "coupon_get", "promotion_list", "promotion_get", "product_diagnose"):
                assert tools[name].annotations.read_only_hint, name  # everything in WP-24 is read-only
            result = await client.call_tool("coupon_list", {"shop": "s", "status": "ONGOING"})
            assert result.structured_content == {"data": {"data": [{"channel_coupon_id": "c1"}], "next_cursor": "c2"}}
            bad = await client.call_tool("product_diagnose", {"shop": "s", "products": "a%2F"})
            assert bad.is_error

    anyio.run(check)
    assert env.requests[0][2]["status"] == "ONGOING"


def test_campaign_open_collab_tools(env):
    names = {"campaign_groups", "campaign_list", "campaign_get", "campaign_registered", "campaign_counts",
             "open_collab_settings", "open_collab_sample_rules"}
    assert names <= set(TOOLS)
    env.responses["/campaign-groups"] = page([{"channel_campaign_group_id": "1"}], cursor="g2")
    env.responses["/campaigns/7400000000000000101"] = {"data": {"channel_campaign_id": "7400000000000000101"}}

    async def check():
        async with Client(create_server()) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            for name in names:
                assert tools[name].annotations.read_only_hint, name  # everything in WP-24 is read-only
            result = await client.call_tool("campaign_groups", {"shop": "s", "invited_only": True})
            assert result.structured_content == {"data": {"data": [{"channel_campaign_group_id": "1"}],
                                                          "next_cursor": "g2"}}
            got = await client.call_tool("campaign_get", {"shop": "s", "CAMPAIGN_ID": "7400000000000000101",
                                                          "type": "PRODUCT"})
            assert not got.is_error
            bad = await client.call_tool("campaign_get", {"shop": "s", "CAMPAIGN_ID": "1", "type": "UNMAPPED"})
            assert bad.is_error
            bad = await client.call_tool("open_collab_sample_rules", {"shop": "s", "products": "a%2F"})
            assert bad.is_error

    anyio.run(check)
    assert env.requests[0][2]["invited_only"] == "true"
    assert env.requests[1][2] == {"shop_id": "s", "type": "PRODUCT"}
