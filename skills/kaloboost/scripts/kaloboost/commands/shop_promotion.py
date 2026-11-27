"""`boost coupon` / `boost promotion` / `boost product diagnose` — seller marketing tools and
product diagnoses of a shop, read live from TikTok (nothing is stored in Kaloboost).

Coupons are read-only here: creating one is only possible in Seller Center.
"""

from __future__ import annotations

from .. import api, render
from ..core import Command, Flag
from ..errors import UsageError
from . import common

COUPON_STATUSES = ("NOT_START", "ONGOING", "EXPIRED", "DEACTIVATED")
COUPON_FIELDS = ("channel_coupon_id", "title", "status", "claim_end", "redeem_by", "discount", "usage")
PROMOTION_TYPES = ("FIXED_PRICE", "DIRECT_DISCOUNT", "FLASHSALE", "SHIPPING_DISCOUNT",
                   "BUY_MORE_SAVE_MORE", "GIFT_WITH_PURCHASE", "BUY_X_GET_Y")
PROMOTION_STATUSES = ("NOT_START", "ONGOING", "EXPIRED", "DEACTIVATED")
PROMOTION_FIELDS = ("channel_promotion_id", "title", "type", "status", "begin_time", "end_time", "products")
DIAGNOSE_FIELDS = ("channel_product_id", "listing_quality", "issues", "image_issues")
PRODUCT_IDS_MIN, PRODUCT_IDS_MAX = 1, 200


def _csv(value: str | None, flag: str, *, single: bool = False) -> str | None:
    """Comma list -> upper-cased, de-duplicated, comma-joined (same convention as shop-order)."""
    if value is None:
        return None
    items = [p.strip().upper() for p in value.split(",")]
    if any(not p for p in items):
        raise UsageError(f"{flag} has an empty item: '{value}'")
    if single and len(items) > 1:
        raise UsageError(f"{flag} takes one value, got {len(items)}", ["Run once per value"])
    return ",".join(dict.fromkeys(items))


def _object_id(value: str, flag: str) -> str:
    """The public contract admits [A-Za-z0-9_-]{1,64} for object ids; anything else is a 400 there."""
    import re
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", value or ""):
        raise UsageError(f"{flag} must match [A-Za-z0-9_-]{{1,64}}, got '{value}'")
    return value


# --- coupon ------------------------------------------------------------------

def _money(obj) -> str | None:
    return common.money(obj)


def _coupon_discount(c: dict) -> str | None:
    d = c.get("discount") or {}
    kind = d.get("type")
    if not kind:
        return None
    if d.get("percentage"):
        return f"{kind} {d['percentage']}"
    amount = _money(d.get("reduction_amount"))
    cap = _money(d.get("max_discount"))
    out = f"{kind} {amount}" if amount else kind
    if cap:
        out += f" (max {cap})"
    return out


def _redeem_by(c: dict) -> str | None:
    r = c.get("redemption") or {}
    if r.get("type") == "RELATIVE":
        days = r.get("relative_days")
        return f"RELATIVE {days}d" if days is not None else "RELATIVE"
    return r.get("end_time")


def _coupon_row(c: dict) -> dict:
    stats = c.get("usage_stats") or {}
    usage = None
    if stats:
        usage = f"{stats.get('claimed_count', 0)}/{stats.get('redeemed_count', 0)}"
    return {
        "channel_coupon_id": c.get("channel_coupon_id"),
        "title": c.get("title"),
        "status": c.get("status"),
        "claim_end": c.get("claim_end_time"),
        "redeem_by": _redeem_by(c),
        "discount": _coupon_discount(c),
        "usage": usage,
    }


def coupon_list(cfg, opts, args):
    shop = common.shop(cfg, opts)
    status = _csv(opts.get("status"), "--status")
    display_type = _csv(opts.get("display_type"), "--display-type")
    params = {"shop_id": shop, "status": status, "display_type": display_type, "title": opts.get("title")}
    rows, cursor, pages = common.fetch_pages(cfg, "/shop-coupons", params, opts)
    if opts.get("json"):
        common.dump_json({"data": rows, "next_cursor": cursor})
        return 0
    base = common.again("coupon list", *common.flag_pairs(
        shop=shop, status=status, display_type=display_type, title=opts.get("title")))
    if not rows:
        render.emit_empty("coupons", f"shop {shop}", common.page_hints(rows, cursor, pages, base, opts, []))
        return 0
    render.emit_table("coupons", [_coupon_row(c) for c in rows], COUPON_FIELDS)
    hints = [
        f"{len(rows)} coupons · usage = claimed/redeemed (usage_stats, detail only — add --json on get)",
        "Expired? look at status and claim_end_time; a RELATIVE redemption has no absolute end — see relative_days",
        "Coupons are read-only here: creating one is only possible in Seller Center",
    ]
    render.emit_help(common.page_hints(rows, cursor, pages, base, opts, hints))
    return 0


def coupon_get(cfg, opts, args):
    shop = common.shop(cfg, opts)
    if not args:
        raise UsageError("coupon get takes a channel_coupon_id", ["boost coupon get <id> --shop <SHOP_ID>"])
    coupon_id = _object_id(args[0], "coupon id")
    env = api.request(cfg, "GET", f"/shop-coupons/{coupon_id}", params={"shop_id": shop})
    item = env.get("data") or {}
    if opts.get("json"):
        common.dump_json(item)
        return 0
    render.emit_table("coupons", [_coupon_row(item)], COUPON_FIELDS)
    render.emit_help([
        "usage = claimed/redeemed; add --json for usage_limits, threshold, seller_terms, product scope",
        "claim_start_time/claim_end_time and redemption start/end are absolute times unless redemption.type is RELATIVE",
    ])
    return 0


# --- promotion ---------------------------------------------------------------

def _promotion_row(p: dict) -> dict:
    return {
        "channel_promotion_id": p.get("channel_promotion_id"),
        "title": p.get("title"),
        "type": p.get("type"),
        "status": p.get("status"),
        "begin_time": p.get("begin_time"),
        "end_time": p.get("end_time"),
        "products": len(p.get("products") or []),
    }


def promotion_list(cfg, opts, args):
    shop = common.shop(cfg, opts)
    status = _csv(opts.get("status"), "--status", single=True)
    ptype = _csv(opts.get("type"), "--type", single=True)
    params = {"shop_id": shop, "status": status, "type": ptype, "title": opts.get("title")}
    rows, cursor, pages = common.fetch_pages(cfg, "/shop-promotions", params, opts)
    if opts.get("json"):
        common.dump_json({"data": rows, "next_cursor": cursor})
        return 0
    base = common.again("promotion list", *common.flag_pairs(
        shop=shop, status=status, type=ptype, title=opts.get("title")))
    if not rows:
        render.emit_empty("promotions", f"shop {shop}", common.page_hints(rows, cursor, pages, base, opts, []))
        return 0
    render.emit_table("promotions", [_promotion_row(p) for p in rows], PROMOTION_FIELDS)
    hints = [
        f"{len(rows)} promotions · products = products in the activity (detail only — use `boost promotion get`)",
        "UNMAPPED type/status means TikTok added a value this CLI does not know — the raw value is in "
        "channel_type/channel_status (--json)",
    ]
    render.emit_help(common.page_hints(rows, cursor, pages, base, opts, hints))
    return 0


def promotion_get(cfg, opts, args):
    shop = common.shop(cfg, opts)
    if not args:
        raise UsageError("promotion get takes a channel_promotion_id", ["boost promotion get <id> --shop <SHOP_ID>"])
    promotion_id = _object_id(args[0], "promotion id")
    env = api.request(cfg, "GET", f"/shop-promotions/{promotion_id}", params={"shop_id": shop})
    item = env.get("data") or {}
    if opts.get("json"):
        common.dump_json(item)
        return 0
    render.emit_table("promotions", [_promotion_row(item)], PROMOTION_FIELDS)
    render.emit_help([
        "add --json for products with activity prices, target_user_type, discount configuration and "
        "participation_limit (raw TikTok sub-objects)",
        "immutable=true means TikTok forbids editing the activity (activity_commands carries IMMUTABLE)",
    ])
    return 0


# --- product diagnose ----------------------------------------------------------

def _diagnose_row(p: dict) -> dict:
    issues = []
    image_issues = 0
    for d in p.get("diagnoses") or []:
        found = d.get("issues") or []
        issues.extend(found)
        if d.get("field") == "IMAGE":
            image_issues += len(found)
    quality = p.get("listing_quality")
    return {
        "channel_product_id": p.get("channel_product_id"),
        "listing_quality": quality if quality is not None else "-",
        "issues": len(issues),
        "image_issues": image_issues,
    }


def product_diagnose(cfg, opts, args):
    shop = common.shop(cfg, opts)
    raw = opts.get("products") or (args[0] if args else None)
    if not raw:
        raise UsageError("product diagnose takes product ids", ["boost product diagnose --shop <SHOP_ID> --products <id,id,...>"])
    ids = [p.strip() for p in raw.split(",")]
    if any(not p for p in ids):
        raise UsageError(f"--products has an empty item: '{raw}'")
    for pid in ids:
        _object_id(pid, "product id")
    if not PRODUCT_IDS_MIN <= len(ids) <= PRODUCT_IDS_MAX:
        raise UsageError(f"--products takes {PRODUCT_IDS_MIN}-{PRODUCT_IDS_MAX} ids, got {len(ids)}")
    ids = list(dict.fromkeys(ids))
    env = api.request(cfg, "GET", "/product-diagnoses", params={"shop_id": shop, "product_ids": ",".join(ids)})
    rows = env.get("data") or []
    if opts.get("json"):
        common.dump_json({"data": rows})
        return 0
    if not rows:
        render.emit_empty("product_diagnoses", f"shop {shop}, {len(ids)} product ids", [
            "An id missing from the response does not exist or does not belong to this shop",
        ])
        return 0
    render.emit_table("product_diagnoses", [_diagnose_row(p) for p in rows], DIAGNOSE_FIELDS)
    missing = [pid for pid in ids if pid not in {str(p.get("channel_product_id")) for p in rows}]
    hints = [
        f"{len(rows)} of {len(ids)} products answered" + (f" · {len(missing)} missing = do not exist or not in this shop" if missing else ""),
        "listing_quality is only scored in the US; ID/TH/MY products answer null ('-')",
        "add --json for issue codes, how_to_solve text and suggestions (seo_words/smart_texts)",
    ]
    render.emit_help(hints)
    return 0


COMMANDS = [
    Command(
        path="coupon list",
        summary="Seller coupons of a shop: status, claim/redemption window, discount, usage; read-only",
        handler=coupon_list,
        flags=[
            common.shop_flag(),
            Flag("--status", "comma-separated: " + " ".join(COUPON_STATUSES), metavar="STATUS"),
            Flag("--display-type", "comma-separated TikTok display types, upper-case", metavar="TYPE"),
            Flag("--title", "title keyword", metavar="TEXT"),
            *common.page_flags(default_limit=50),
        ],
        examples=[
            "boost coupon list --shop <SHOP_ID> --status ONGOING --all",
            "boost coupon list --shop <SHOP_ID> --title flash --json",
        ],
    ),
    Command(
        path="coupon get",
        summary="One seller coupon: usage stats, limits, threshold, seller terms, product scope",
        handler=coupon_get,
        flags=[common.shop_flag()],
        positional="COUPON_ID", pos_min=1, pos_max=1,
        examples=["boost coupon get <COUPON_ID> --shop <SHOP_ID> --json"],
    ),
    Command(
        path="promotion list",
        summary="Seller promotions (platform activities) of a shop: type, status, window, product count",
        handler=promotion_list,
        flags=[
            common.shop_flag(),
            Flag("--status", "one status: " + " ".join(PROMOTION_STATUSES), metavar="STATUS"),
            Flag("--type", "one type: " + " ".join(PROMOTION_TYPES), metavar="TYPE"),
            Flag("--title", "title keyword", metavar="TEXT"),
            *common.page_flags(default_limit=50),
        ],
        examples=[
            "boost promotion list --shop <SHOP_ID> --status ONGOING --all",
            "boost promotion list --shop <SHOP_ID> --type FLASHSALE --json",
        ],
    ),
    Command(
        path="promotion get",
        summary="One seller promotion: products with activity prices, target user, discount configuration",
        handler=promotion_get,
        flags=[common.shop_flag()],
        positional="PROMOTION_ID", pos_min=1, pos_max=1,
        examples=["boost promotion get <PROMOTION_ID> --shop <SHOP_ID> --json"],
    ),
    Command(
        path="product diagnose",
        summary="TikTok listing diagnoses of 1-200 products: listing quality, issues, suggestions",
        handler=product_diagnose,
        flags=[
            common.shop_flag(),
            Flag("--products", "comma-separated product ids (1-200)", metavar="IDS"),
        ],
        pos_max=1,
        examples=[
            "boost product diagnose --shop <SHOP_ID> --products <id,id>",
        ],
    ),
]
