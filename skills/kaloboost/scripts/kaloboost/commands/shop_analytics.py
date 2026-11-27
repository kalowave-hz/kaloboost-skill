"""`boost shop-performance` / `boost product-performance` / `boost sku-performance` — a shop's own
performance as TikTok Shop Analytics reports it (TikTok's official numbers, read live; nothing is
stored in Kaloboost). Read-only.

Dates are the shop's registered-timezone calendar days, `--to` is exclusive, the span is at most 90
days, and the data lags one day: read `latest_available_date` before trusting the last day.

Money is always the shop's local currency (each amount carries its ISO code). There is no USD option:
TikTok's `currency=USD` did not fully take effect when tested on SG Dev (2026-11-27), so it is not offered.
"""

from __future__ import annotations

import datetime
import re

from .. import api, render
from ..core import Command, Flag
from ..errors import UsageError
from . import common

GRANULARITIES = ("ALL", "DAY")
ORDERS = ("DESC", "ASC")
PRODUCT_STATUSES = ("LIVE", "INACTIVE", "ALL")
PRODUCT_SORTS = ("gmv", "items_sold", "orders")
SKU_SORTS = ("gmv", "sku_orders", "units_sold")
DEFAULT_DAYS = 7
MAX_SPAN_DAYS = 90
IDS_MAX = 100

_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_RELATIVE_DAYS = re.compile(r"(\d{1,3})d")
_OBJECT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")

SHOP_FIELDS = ("start_date", "end_date", "gmv", "orders", "items_sold", "customers", "aov", "refunds",
               "product_impressions", "product_clicks", "conversion_rate")
PRODUCT_FIELDS = ("channel_product_id", "gmv", "orders", "items_sold", "sku_orders", "product_impressions",
                  "product_clicks", "ctr", "click_order_rate", "refunds")
SKU_FIELDS = ("channel_sku_id", "channel_product_id", "gmv", "sku_orders", "units_sold")
PRODUCT_PASS_THROUGH = (
    "seller_live_performance", "seller_video_performance", "seller_product_card_performance",
    "affiliate_total_performance", "affiliate_live_performance", "affiliate_video_performance",
    "shop_tab_performance",
)

RATE_HINT = "rates are decimal strings: \"0.0843\" = 8.43%"
LAG_HINT = ("TikTok's official Shop Analytics (data lags a day — not the same numbers as KaloData's T+1 "
            "estimates); dates are the shop's timezone, --to exclusive")


# --- argument helpers ----------------------------------------------------------

def _today() -> datetime.date:
    return datetime.date.today()


def _date(value: str, flag: str) -> datetime.date:
    v = value.strip()
    try:
        if not _DATE.fullmatch(v):
            raise ValueError
        return datetime.date.fromisoformat(v)
    except ValueError:
        raise UsageError(f"invalid {flag} '{value}'",
                         ["expected yyyy-MM-dd (the shop's timezone)" + (", or Nd = N days before --to"
                                                                         if flag == "--from" else "")]) from None


def date_range(opts) -> tuple[str, str]:
    """--from / --to -> (start_date, end_date). Default: the last 7 days, --to = today (local date).

    `--from 30d` = 30 days before --to. --to is exclusive; to > from; span ≤ 90 days.
    """
    raw_to = (opts.get("to") or "").strip()
    raw_from = (opts.get("from") or "").strip()
    end = _date(raw_to, "--to") if raw_to else _today()
    m = _RELATIVE_DAYS.fullmatch(raw_from)
    if not raw_from:
        start = end - datetime.timedelta(days=DEFAULT_DAYS)
    elif m:
        start = end - datetime.timedelta(days=int(m.group(1)))
    else:
        start = _date(raw_from, "--from")
    if end <= start:
        raise UsageError(f"--to ({end}) must be after --from ({start}) — --to is exclusive",
                         ["For the single day D use --from D --to D+1"])
    span = (end - start).days
    if span > MAX_SPAN_DAYS:
        raise UsageError(f"the date range is {span} days; at most {MAX_SPAN_DAYS} per call",
                         ["Split it into windows of ≤90 days"])
    return start.isoformat(), end.isoformat()


def enum(value: str | None, flag: str, allowed: tuple, *, lower: bool = False) -> str | None:
    if value is None or not value.strip():
        return None
    v = value.strip().lower() if lower else value.strip().upper()
    if v not in allowed:
        raise UsageError(f"unsupported {flag} '{value}'", [f"valid values: {' '.join(allowed)}"])
    return v


def id_list(value: str | None, flag: str) -> str | None:
    """Comma list of TikTok ids ([A-Za-z0-9_-]{1,64}), de-duplicated, ≤ 100."""
    if value is None:
        return None
    items = [p.strip() for p in value.split(",")]
    if any(not p for p in items):
        raise UsageError(f"{flag} has an empty item: '{value}'")
    for p in items:
        if not _OBJECT_ID.fullmatch(p):
            raise UsageError(f"{flag} ids must match [A-Za-z0-9_-]{{1,64}}, got '{p}'")
    items = list(dict.fromkeys(items))
    if len(items) > IDS_MAX:
        raise UsageError(f"{flag} takes at most {IDS_MAX} ids, got {len(items)}")
    return ",".join(items)


def _lag_hint(latest: str | None, end: str) -> str | None:
    if not latest:
        return None
    if latest < (datetime.date.fromisoformat(end) - datetime.timedelta(days=1)).isoformat():
        return (f"latest_available_date = {latest}: days after it are not complete yet (TikTok data lags about "
                "a day)")
    return f"latest_available_date = {latest}"


def _date_flags() -> list[Flag]:
    return [
        Flag("--from", "start date yyyy-MM-dd, inclusive (shop timezone), or Nd = N days before --to "
                       "(default 7d)", metavar="DATE"),
        Flag("--to", "end date yyyy-MM-dd, exclusive (default: today); span ≤ 90 days", metavar="DATE"),
    ]


def _list_flags(sorts: tuple) -> list[Flag]:
    return [
        Flag("--sort", "sort by: " + " ".join(sorts) + " (default gmv)", metavar="FIELD"),
        Flag("--order", "DESC (default) or ASC", metavar="ORDER"),
        Flag("--categories", "comma-separated TikTok category ids (≤100)", metavar="IDS"),
        Flag("--status", "product status: " + " ".join(PRODUCT_STATUSES) + " (default ALL)", metavar="STATUS"),
    ]


# --- shop performance ------------------------------------------------------------

def _shop_row(iv: dict) -> dict:
    sales = iv.get("sales") or {}
    traffic = iv.get("traffic") or {}
    return {
        "start_date": iv.get("start_date"),
        "end_date": iv.get("end_date"),
        "gmv": common.money(sales.get("gmv")),
        "orders": sales.get("orders_count"),
        "items_sold": sales.get("items_sold"),
        "customers": sales.get("customers_count"),
        "aov": common.money(sales.get("avg_order_value")),
        "refunds": common.money(sales.get("refunds")),
        "product_impressions": traffic.get("product_impressions"),
        "product_clicks": traffic.get("product_clicks"),
        "conversion_rate": traffic.get("avg_conversation_rate"),
    }


def shop_performance(cfg, opts, args):
    shop = common.shop(cfg, opts)
    start, end = date_range(opts)
    granularity = enum(opts.get("granularity"), "--granularity", GRANULARITIES)
    env = api.request(cfg, "GET", "/shop-performance",
                      params={"shop_id": shop, "start_date": start, "end_date": end, "granularity": granularity})
    item = env.get("data") or {}
    if opts.get("json"):
        common.dump_json(item)
        return 0
    intervals = item.get("intervals") or []
    if not intervals:
        render.emit_empty("shop_performance", f"shop {shop}, {start} to {end} (exclusive)",
                          [_lag_hint(item.get("latest_available_date"), end), LAG_HINT])
        return 0
    render.emit_table("shop_performance", [_shop_row(iv) for iv in intervals], SHOP_FIELDS)
    render.emit_help([
        _lag_hint(item.get("latest_available_date"), end),
        LAG_HINT,
        "conversion_rate is traffic.avg_conversation_rate (daily average) · " + RATE_HINT,
        "add --json for the full sales / traffic / breakdowns objects (live / video / product card GMV, "
        "creator vs seller, shipping, tax, cancellations; raw TikTok keys)",
        "Daily rows: add --granularity DAY" if granularity != "DAY" else None,
    ])
    return 0


# --- product / SKU performance -----------------------------------------------------

def _product_row(p: dict) -> dict:
    t = p.get("total_performance") or {}
    return {
        "channel_product_id": p.get("channel_product_id"),
        "gmv": common.money(t.get("gmv")),
        "orders": t.get("orders"),
        "items_sold": t.get("items_sold"),
        "sku_orders": t.get("sku_orders"),
        "product_impressions": t.get("product_impressions"),
        "product_clicks": t.get("product_clicks"),
        "ctr": t.get("ctr"),
        "click_order_rate": t.get("click_order_rate"),
        "refunds": common.money(t.get("refunds")),
    }


def _sku_row(s: dict) -> dict:
    return {
        "channel_sku_id": s.get("channel_sku_id"),
        "channel_product_id": s.get("channel_product_id"),
        "gmv": common.money(s.get("gmv")),
        "sku_orders": s.get("sku_orders"),
        "units_sold": s.get("units_sold"),
    }


def _empty_page_hint(rows: list, cursor: str | None) -> list[str]:
    if not rows and cursor:
        return ["This page is empty but TikTok says there is more — only a null next_cursor ends the list"]
    return []


def _performance_list(cfg, opts, *, command: str, path: str, noun: str, sorts: tuple, sku: bool):
    shop = common.shop(cfg, opts)
    start, end = date_range(opts)
    sort = enum(opts.get("sort"), "--sort", sorts, lower=True)
    order = enum(opts.get("order"), "--order", ORDERS)
    categories = id_list(opts.get("categories"), "--categories")
    status = enum(opts.get("status"), "--status", PRODUCT_STATUSES)
    products = id_list(opts.get("products"), "--products") if sku else None
    params = {"shop_id": shop, "start_date": start, "end_date": end, "sort": sort,
              "order": order, "category_ids": categories, "product_status": status, "product_ids": products}
    rows, cursor, pages = common.fetch_pages(cfg, path, params, opts)
    if opts.get("json"):
        common.dump_json({"data": rows, "next_cursor": cursor})
        return 0
    base = common.again(command, *common.flag_pairs(
        shop=shop, **{"from": start}, to=end, sort=sort, order=order, categories=categories,
        status=status, products=products))
    latest = next((r.get("latest_available_date") for r in rows if r.get("latest_available_date")), None)
    context = f"shop {shop}, {start} to {end} (exclusive)"
    if not rows:
        render.emit_empty(noun, context, common.page_hints(
            rows, cursor, pages, base, opts, _empty_page_hint(rows, cursor) + [_lag_hint(latest, end), LAG_HINT]))
        return 0
    if sku:
        render.emit_table(noun, [_sku_row(r) for r in rows], SKU_FIELDS)
        hints = [
            f"{len(rows)} SKUs, {context}, sorted by {sort or 'gmv'} {order or 'DESC'}",
            _lag_hint(latest, end),
            LAG_HINT,
            "channel_sku_id / channel_product_id are decimal strings that can exceed 2^53 — keep them as text",
        ]
    else:
        render.emit_table(noun, [_product_row(r) for r in rows], PRODUCT_FIELDS)
        hints = [
            f"{len(rows)} products, {context}, sorted by {sort or 'gmv'} {order or 'DESC'} · numbers are "
            "total_performance (all channels)",
            _lag_hint(latest, end),
            LAG_HINT,
            RATE_HINT,
            "add --json for the other total_performance fields and the per-channel objects ("
            + ", ".join(PRODUCT_PASS_THROUGH) + "; raw TikTok sub-objects, shape may change)",
            "SKUs of these products: `boost sku-performance --shop " + shop + " --products <id,id>`",
        ]
    render.emit_help(common.page_hints(rows, cursor, pages, base, opts, hints))
    return 0


def product_performance(cfg, opts, args):
    return _performance_list(cfg, opts, command="product-performance", path="/shop-product-performance",
                             noun="product_performance", sorts=PRODUCT_SORTS, sku=False)


def sku_performance(cfg, opts, args):
    return _performance_list(cfg, opts, command="sku-performance", path="/shop-sku-performance",
                             noun="sku_performance", sorts=SKU_SORTS, sku=True)


COMMANDS = [
    Command(
        path="shop-performance",
        summary="TikTok Shop Analytics for one shop: GMV, orders, buyers, AOV, refunds, traffic; ≤90 days, "
                "data lags a day; read-only",
        handler=shop_performance,
        flags=[
            common.shop_flag(),
            *_date_flags(),
            Flag("--granularity", "ALL = one total row (default), DAY = one row per day", metavar="GRANULARITY"),
        ],
        examples=[
            "boost shop-performance --shop <SHOP_ID>",
            "boost shop-performance --shop <SHOP_ID> --from 2026-11-01 --to 2026-12-01 --granularity DAY",
        ],
    ),
    Command(
        path="product-performance",
        summary="Product ranking by TikTok Shop Analytics: GMV, orders, items sold, impressions, CTR, conversion; "
                "read-only",
        handler=product_performance,
        flags=[
            common.shop_flag(),
            *_date_flags(),
            *_list_flags(PRODUCT_SORTS),
            *common.page_flags(),
        ],
        examples=[
            "boost product-performance --shop <SHOP_ID>",
            "boost product-performance --shop <SHOP_ID> --from 30d --sort items_sold --status LIVE --limit 50",
        ],
    ),
    Command(
        path="sku-performance",
        summary="SKU ranking by TikTok Shop Analytics: GMV, SKU orders, units sold; --products narrows to "
                "products; read-only",
        handler=sku_performance,
        flags=[
            common.shop_flag(),
            *_date_flags(),
            *_list_flags(SKU_SORTS),
            Flag("--products", "only SKUs of these TikTok product ids, comma-separated (≤100)", metavar="IDS"),
            *common.page_flags(),
        ],
        examples=[
            "boost sku-performance --shop <SHOP_ID>",
            "boost sku-performance --shop <SHOP_ID> --products <id,id> --sort units_sold",
        ],
    ),
]
