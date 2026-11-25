"""`boost shop-order` / `boost shop-return` — every order and return of a shop, read live from TikTok.

Not to be confused with `boost order list`, which is affiliate orders only.
"""

from __future__ import annotations

import datetime

from .. import render
from ..core import Command, Flag
from ..errors import UsageError
from . import common

WINDOW_MAX_DAYS = 90
DEFAULT_DAYS = 30
RETURN_LIMIT_MIN, RETURN_LIMIT_MAX, RETURN_LIMIT_DEFAULT = 10, 50, 20

ORDER_STATUSES = (
    "UNPAID", "ON_HOLD", "AWAITING_SHIPMENT", "PARTIALLY_SHIPPING", "AWAITING_COLLECTION",
    "IN_TRANSIT", "DELIVERED", "COMPLETED", "CANCELLED",
)
RETURN_TYPES = ("REFUND", "RETURN_AND_REFUND", "REPLACEMENT", "EXCHANGE")
RETURN_STATUSES = (
    "RETURN_OR_REFUND_REQUEST_PENDING", "REFUND_OR_RETURN_REQUEST_REJECT", "AWAITING_BUYER_SHIP",
    "BUYER_SHIPPED_ITEM", "REJECT_RECEIVE_PACKAGE", "RETURN_OR_REFUND_REQUEST_SUCCESS",
    "RETURN_OR_REFUND_REQUEST_CANCEL", "RETURN_OR_REFUND_REQUEST_COMPLETE", "REPLACEMENT_REQUEST_PENDING",
    "REPLACEMENT_REQUEST_REJECT", "REPLACEMENT_REQUEST_REFUND_SUCCESS", "REPLACEMENT_REQUEST_CANCEL",
    "REPLACEMENT_REQUEST_COMPLETE", "AWAITING_BUYER_RESPONSE", "EXCHANGE_REQUEST_PENDING",
    "EXCHANGE_REQUEST_REFUND_SUCCESS", "EXCHANGE_REQUEST_CANCEL", "EXCHANGE_REQUEST_COMPLETE",
)

ORDER_FIELDS = ("channel_order_id", "status", "created_at", "ship_by", "lines", "buyer_paid", "tracking_number")
RETURN_FIELDS = ("channel_return_id", "channel_order_id", "type", "status", "created_at", "seller_todo", "refund_total")


# --- arguments ---------------------------------------------------------------

def _window(opts, *, required: bool = True) -> tuple[str, str, str] | None:
    """-> (time field, from, to) for created (--from/--to) or updated (--updated-from/--updated-to).

    Missing bounds default to now and DEFAULT_DAYS before the upper bound. Returns
    None when no window is given and none is required (returns looked up by --order).
    """
    created = opts.get("from") or opts.get("to")
    updated = opts.get("updated_from") or opts.get("updated_to")
    if created and updated:
        raise UsageError(
            "use either --from/--to (order time) or --updated-from/--updated-to (update time), not both",
        )
    if updated:
        field, lo, hi = "updated", "--updated-from", "--updated-to"
        lo_v, hi_v = opts.get("updated_from"), opts.get("updated_to")
    elif created or required:
        field, lo, hi = "created", "--from", "--to"
        lo_v, hi_v = opts.get("from"), opts.get("to")
    else:
        return None
    now = datetime.datetime.now(datetime.timezone.utc)
    to = common.parse_when(hi_v, hi, now=now) or common.iso(now)
    b = datetime.datetime.fromisoformat(to.replace("Z", "+00:00"))
    frm = common.parse_when(lo_v, lo, now=now) or common.iso(b - datetime.timedelta(days=DEFAULT_DAYS))
    a = datetime.datetime.fromisoformat(frm.replace("Z", "+00:00"))
    if a >= b:
        raise UsageError(f"{lo} {frm} must be earlier than {hi} {to}")
    if b - a > datetime.timedelta(days=WINDOW_MAX_DAYS):
        raise UsageError(
            f"window {frm} ~ {to} is longer than {WINDOW_MAX_DAYS} days",
            [f"Split it into several windows of at most {WINDOW_MAX_DAYS} days"],
        )
    return field, frm, to


def _window_params(win) -> dict:
    if not win:
        return {}
    field, frm, to = win
    return {f"{field}_from": frm, f"{field}_to": to}


def _window_flags(win) -> list:
    if not win:
        return []
    field, frm, to = win
    if field == "updated":
        return common.flag_pairs(updated_from=frm, updated_to=to)
    return common.flag_pairs(**{"from": frm, "to": to})


def _choices(value: str | None, flag: str, known: tuple, *, single: bool = False) -> str | None:
    """Comma list -> upper-cased, de-duplicated, comma-joined; unknown or empty items are usage errors."""
    if value is None:
        return None
    items = [p.strip().upper() for p in value.split(",")]
    if any(not p for p in items):
        raise UsageError(f"{flag} has an empty item: '{value}'")
    if single and len(items) > 1:
        raise UsageError(f"{flag} takes one value, got {len(items)}", ["Run once per status"])
    bad = [p for p in items if p not in known]
    if bad:
        raise UsageError(f"unknown {flag} value(s): {', '.join(bad)}", [f"valid values: {' '.join(known)}"])
    return ",".join(dict.fromkeys(items))


def _time_flags(what: str) -> list[Flag]:
    return [
        Flag("--from", f"{what} time from: 7d | yyyy-MM-dd | ISO (default {DEFAULT_DAYS} days before --to)", metavar="WHEN"),
        Flag("--to", f"{what} time until, exclusive (default now)", metavar="WHEN"),
        Flag("--updated-from", "filter by update time instead (incremental sync); not with --from/--to", metavar="WHEN"),
        Flag("--updated-to", "update time until, exclusive (default now)", metavar="WHEN"),
    ]


SORT_FLAG = Flag("--sort", "by the chosen time field (server default desc; asc for incremental sync)",
                 choices=("asc", "desc"))


# --- shop-order list ---------------------------------------------------------

def _order_row(o: dict) -> dict:
    return {
        "channel_order_id": o.get("channel_order_id"),
        "status": o.get("status"),
        "created_at": o.get("created_at"),
        "ship_by": (o.get("deadlines") or {}).get("ship_sla_at"),
        "lines": len(o.get("line_items") or []),
        "buyer_paid": common.money((o.get("payment") or {}).get("total_amount")),
        "tracking_number": o.get("tracking_number"),
    }


def shop_orders(cfg, opts, args):
    shop = common.shop(cfg, opts)
    win = _window(opts)
    status = _choices(opts.get("status"), "--status", ORDER_STATUSES, single=True)
    cancel = "true" if opts.get("buyer_cancel_requested") else None
    params = {"shop_id": shop, **_window_params(win), "status": status,
              "buyer_cancel_requested": cancel, "sort": opts.get("sort")}
    rows, cursor, pages = common.fetch_pages(cfg, "/shop-orders", params, opts)
    if opts.get("json"):
        common.dump_json({"data": rows, "next_cursor": cursor})
        return 0
    base = common.again(
        "shop-order list",
        *common.flag_pairs(shop=shop), *_window_flags(win), *common.flag_pairs(status=status, sort=opts.get("sort")),
        "--buyer-cancel-requested" if cancel else None,
    )
    field, frm, to = win
    if not rows:
        render.emit_empty("shop_orders", f"shop {shop}, {field} {frm} ~ {to}", common.page_hints(rows, cursor, pages, base, opts, []))
        return 0
    render.emit_table("shop_orders", [_order_row(o) for o in rows], ORDER_FIELDS)
    tally: dict = {}
    for o in rows:
        tally[o.get("status")] = tally.get(o.get("status"), 0) + 1
    hints = [
        f"{len(rows)} orders · statuses: " + ", ".join(f"{k} {v}" for k, v in sorted(tally.items(), key=lambda kv: -kv[1])),
        "All orders of the shop (not only affiliate ones — those are `boost order list`); live from TikTok, not stored",
        "ship_by = deadlines.ship_sla_at; add --json for every deadline, line items, payment breakdown",
    ]
    render.emit_help(common.page_hints(rows, cursor, pages, base, opts, hints))
    return 0


# --- shop-return list ----------------------------------------------------------

def _todo(actions) -> str | None:
    if not actions:
        return None
    return "; ".join(
        f"{a.get('action')} by {a.get('deadline')}" if a.get("deadline") else str(a.get("action"))
        for a in actions if isinstance(a, dict)
    ) or None


def _return_row(r: dict) -> dict:
    return {
        "channel_return_id": r.get("channel_return_id"),
        "channel_order_id": r.get("channel_order_id"),
        "type": r.get("type"),
        "status": r.get("status"),
        "created_at": r.get("created_at"),
        "seller_todo": _todo(r.get("seller_actions")),
        "refund_total": common.money((r.get("refund") or {}).get("total")),
    }


def shop_returns(cfg, opts, args):
    shop = common.shop(cfg, opts)
    limit = int(opts.get("limit") or RETURN_LIMIT_DEFAULT)
    if not RETURN_LIMIT_MIN <= limit <= RETURN_LIMIT_MAX:
        raise UsageError(f"--limit must be {RETURN_LIMIT_MIN}-{RETURN_LIMIT_MAX} for returns, got {limit}")
    order = (opts.get("order") or "").strip() or None
    if order is not None and not order.isdigit():
        raise UsageError(f"--order must be a TikTok order id (digits), got '{order}'")
    win = _window(opts, required=order is None)
    status = _choices(opts.get("status"), "--status", RETURN_STATUSES)
    rtype = _choices(opts.get("type"), "--type", RETURN_TYPES)
    params = {"shop_id": shop, **_window_params(win), "channel_order_id": order, "status": status,
              "type": rtype, "sort": opts.get("sort")}
    rows, cursor, pages = common.fetch_pages(cfg, "/shop-returns", params, dict(opts, limit=limit),
                                             max_limit=RETURN_LIMIT_MAX)
    if opts.get("json"):
        common.dump_json({"data": rows, "next_cursor": cursor})
        return 0
    base = common.again(
        "shop-return list",
        *common.flag_pairs(shop=shop), *_window_flags(win),
        *common.flag_pairs(order=order, status=status, type=rtype, sort=opts.get("sort")),
    )
    if not rows:
        ctx = f"shop {shop}" + (f", {win[0]} {win[1]} ~ {win[2]}" if win else "") + (f", order {order}" if order else "")
        render.emit_empty("shop_returns", ctx, common.page_hints(rows, cursor, pages, base, opts, []))
        return 0
    render.emit_table("shop_returns", [_return_row(r) for r in rows], RETURN_FIELDS)
    hints = [
        f"{len(rows)} returns · {sum(1 for r in rows if r.get('seller_actions'))} wait for the seller (seller_todo)",
        "Refunds, returns, replacements and exchanges; to count, keep only rows whose channel_next_return_id is "
        "empty (--json)",
    ]
    render.emit_help(common.page_hints(rows, cursor, pages, base, opts, hints))
    return 0


COMMANDS = [
    Command(
        path="shop-order list",
        summary="All orders of a shop (not only affiliate): status, ship-by deadline, lines, buyer paid, tracking",
        handler=shop_orders,
        flags=[
            common.shop_flag(),
            *_time_flags("order"),
            Flag("--status", "one order status: " + " ".join(ORDER_STATUSES), metavar="STATUS"),
            Flag("--buyer-cancel-requested", "only orders with a buyer cancellation request", kind="flag", default=False),
            SORT_FLAG,
            *common.page_flags(default_limit=50),
        ],
        examples=[
            "boost shop-order list --shop <SHOP_ID> --from 1d --all",
            "boost shop-order list --shop <SHOP_ID> --status AWAITING_SHIPMENT --all",
            "boost shop-order list --shop <SHOP_ID> --updated-from 1h --sort asc --all",
        ],
    ),
    Command(
        path="shop-return list",
        summary="Returns / refunds / replacements of a shop: status, what the seller must do and by when, refund",
        handler=shop_returns,
        flags=[
            common.shop_flag(),
            *_time_flags("request"),
            Flag("--status", "return status(es), comma-separated: " + " ".join(RETURN_STATUSES), metavar="STATUS"),
            Flag("--type", "comma-separated: " + " ".join(RETURN_TYPES), metavar="TYPE"),
            Flag("--order", "only this TikTok order (channel_order_id); no time window needed", metavar="ORDER_ID"),
            SORT_FLAG,
            Flag("--limit", f"rows per page ({RETURN_LIMIT_MIN}-{RETURN_LIMIT_MAX})", kind="int",
                 default=RETURN_LIMIT_DEFAULT, min=RETURN_LIMIT_MIN, max=RETURN_LIMIT_MAX),
            *common.page_flags(max_limit=RETURN_LIMIT_MAX)[1:],
        ],
        examples=[
            "boost shop-return list --shop <SHOP_ID> --from 7d --all",
            "boost shop-return list --shop <SHOP_ID> --order <CHANNEL_ORDER_ID>",
        ],
    ),
]
