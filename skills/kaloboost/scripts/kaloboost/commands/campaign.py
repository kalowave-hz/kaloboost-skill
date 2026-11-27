"""`boost campaign` / `boost open-collab` — TikTok platform campaigns of a shop and its open
collaboration settings / free-sample rules / products in open collaboration, read live from TikTok (nothing is stored in Kaloboost).

Everything here is read-only: registering for or leaving a campaign, and changing open
collaboration, are only possible in Seller Center. TikTok's rule for these routes is "missing =
unknown": a `null` boolean or count means TikTok gave no answer — never read it as false / 0 /
"may register".
"""

from __future__ import annotations

import re

from .. import api, render
from ..core import Command, Flag
from ..errors import UsageError
from . import common

CAMPAIGN_TYPES = ("PRODUCT", "SHOP", "LIVESTREAM", "SHORT_VIDEO")
REGISTRATION_SCOPES = ("REGISTERED", "UNREGISTERED")
ELIGIBILITY_FILTERS = ("ALL", "ELIGIBLE")
REGISTERED_STATUSES = ("INEFFECTIVE", "UPCOMING", "ACTIVE", "EXPIRED")
GROUP_FIELDS = ("channel_campaign_group_id", "title", "type", "status", "region", "is_invited", "campaign_count",
                "start_at", "end_at")
CAMPAIGN_FIELDS = ("channel_campaign_id", "title", "type", "status", "is_invited", "has_joined", "eligible",
                   "can_register", "block_reason", "registration_end_at")
DETAIL_FIELDS = ("channel_campaign_id", "title", "type", "status", "region", "is_invited", "registration_status",
                 "registration_end_at")
REGISTERED_FIELDS = ("channel_campaign_id", "title", "type", "status", "region", "registered", "approved",
                     "under_review", "rejected", "end_at")
SAMPLE_RULE_FIELDS = ("channel_product_id", "status", "sample_quota", "available_quantity", "start_time", "end_time",
                      "min_followers", "min_gmv")
# Detail sub-objects that say whether the shop may register (PRODUCT / SHOP vs LIVESTREAM / SHORT_VIDEO)
ELIGIBILITY_OBJECTS = ("registration_availability", "shop_eligibility", "registration_summary")
PASS_THROUGH_OBJECTS = (
    "campaign_group", "benefits", "fees", "participation_rules", "registration_availability", "registration_limit",
    "shop_eligibility", "shop_participation", "linked_campaigns", "agreement", "participation_requirements",
    "registration_summary", "session_statistics", "super_livestream", "registration_statistics",
)
PRODUCT_IDS_MIN, PRODUCT_IDS_MAX = 1, 200
NAME_MAX_BYTES = 100
LOCALE_MAX = 64
INT64_MAX = 9223372036854775807

_POSITIVE_INT64 = re.compile(r"[1-9][0-9]{0,18}")
_LOCALE = re.compile(r"[A-Za-z]{2,8}(-[A-Za-z0-9]{1,8})*")
_REGION = re.compile(r"[A-Z]{2}")
_OBJECT_ID = re.compile(r"[A-Za-z0-9_-]{1,64}")

NULL_HINT = "null = TikTok gave no answer (unknown) — never read it as false / 0 / may register"


# --- argument helpers ----------------------------------------------------------

def _enum_csv(value: str | None, flag: str, allowed: tuple, *, single: bool = False) -> str | None:
    """Comma list -> upper-cased, de-duplicated, comma-joined; each item must be one of `allowed`."""
    if value is None:
        return None
    items = [p.strip().upper() for p in value.split(",")]
    if any(not p for p in items):
        raise UsageError(f"{flag} has an empty item: '{value}'")
    if single and len(items) > 1:
        raise UsageError(f"{flag} takes one value, got {len(items)}", [f"valid values: {' '.join(allowed)}"])
    bad = [p for p in items if p not in allowed]
    if bad:
        hints = [f"valid values: {' '.join(allowed)}"]
        if flag == "--statuses" and "DEACTIVATED" in bad:
            hints.insert(0, "DEACTIVATED can't be filtered on — deactivated campaigns are counted under EXPIRED")
        raise UsageError(f"unsupported {flag} value(s): {', '.join(bad)}", hints)
    return ",".join(dict.fromkeys(items))


def _int64_id(value: str | None, what: str) -> str:
    v = (value or "").strip()
    if not _POSITIVE_INT64.fullmatch(v) or int(v) > INT64_MAX:
        raise UsageError(f"{what} must be a positive 64-bit decimal integer, got '{value}'")
    return v


def _name(value: str | None, flag: str = "--name") -> str | None:
    if value is None or not value.strip():
        return None
    v = value.strip()
    if len(v.encode("utf-8")) > NAME_MAX_BYTES:
        raise UsageError(f"{flag} is at most {NAME_MAX_BYTES} bytes in UTF-8")
    return v


def _locale(value: str | None) -> str | None:
    if value is None:
        return None
    v = value.strip()
    if len(v) > LOCALE_MAX or not _LOCALE.fullmatch(v):
        raise UsageError(f"--locale must be a BCP-47 language tag (e.g. en-US, id-ID), got '{value}'")
    return v


def _regions(value: str | None) -> str | None:
    if value is None:
        return None
    items = [p.strip().upper() for p in value.split(",")]
    if any(not _REGION.fullmatch(p) for p in items):
        raise UsageError(f"--regions takes ISO 3166-1 alpha-2 codes or EU, comma-separated, got '{value}'")
    return ",".join(dict.fromkeys(items))


def _true(opts, key: str) -> str | None:
    """Boolean filters: only `true` filters; false / absent means "don't filter", so send nothing."""
    return "true" if opts.get(key) else None


def _period(obj: dict | None, key: str) -> str | None:
    return (obj or {}).get(key)


def _empty_page_hint(rows: list, cursor: str | None) -> list[str]:
    if not rows and cursor:
        return ["This page is empty but TikTok says there is more — an empty page is not the end; only a null "
                "next_cursor is"]
    return []


# --- campaign groups -------------------------------------------------------------

def _group_row(g: dict) -> dict:
    period = g.get("campaign_period")
    return {
        "channel_campaign_group_id": g.get("channel_campaign_group_id"),
        "title": render.clip(g.get("title")),
        "type": g.get("type"),
        "status": g.get("status"),
        "region": g.get("region"),
        "is_invited": g.get("is_invited"),
        "campaign_count": g.get("campaign_count"),
        "start_at": _period(period, "start_at"),
        "end_at": _period(period, "end_at"),
    }


def campaign_groups(cfg, opts, args):
    shop = common.shop(cfg, opts)
    name = _name(opts.get("name"))
    invited = _true(opts, "invited_only")
    pending = _true(opts, "pending_only")
    if invited and pending:
        raise UsageError("--invited-only and --pending-only can't be combined (TikTok treats them as exclusive)",
                         ["Run once with each"])
    registration = _enum_csv(opts.get("registration"), "--registration", REGISTRATION_SCOPES, single=True)
    locale = _locale(opts.get("locale"))
    params = {"shop_id": shop, "name": name, "invited_only": invited, "pending_registration_only": pending,
              "registration": registration, "locale": locale}
    rows, cursor, pages = common.fetch_pages(cfg, "/campaign-groups", params, opts)
    if opts.get("json"):
        common.dump_json({"data": rows, "next_cursor": cursor})
        return 0
    base = common.again("campaign groups", *common.flag_pairs(shop=shop, name=name),
                        "--invited-only" if invited else None, "--pending-only" if pending else None,
                        *common.flag_pairs(registration=registration, locale=locale))
    if not rows:
        render.emit_empty("campaign_groups", f"shop {shop}",
                          common.page_hints(rows, cursor, pages, base, opts, _empty_page_hint(rows, cursor)))
        return 0
    render.emit_table("campaign_groups", [_group_row(g) for g in rows], GROUP_FIELDS)
    hints = [
        f"{len(rows)} campaign groups (TikTok platform campaigns, not seller promotions) · this list takes a few "
        "seconds per page",
        "Campaigns of a group: `boost campaign list --shop " + shop + " --group <channel_campaign_group_id>` "
        "(NORMAL groups also carry them inline in --json; LONG_TERM groups carry linked_campaign_groups)",
        NULL_HINT + "; start_at/end_at are campaign_period, ISO 8601 UTC",
    ]
    render.emit_help(common.page_hints(rows, cursor, pages, base, opts, hints))
    return 0


# --- campaigns ---------------------------------------------------------------------

def _campaign_row(c: dict) -> dict:
    summary = c.get("registration_summary") or {}
    reason = summary.get("registration_block_reason") or {}
    return {
        "channel_campaign_id": c.get("channel_campaign_id"),
        "title": render.clip(c.get("title")),
        "type": c.get("type"),
        "status": c.get("status"),
        "is_invited": c.get("is_invited"),
        "has_joined": c.get("has_joined"),
        "eligible": summary.get("is_eligible"),
        "can_register": summary.get("is_registration_available"),
        "block_reason": reason.get("code"),
        "registration_end_at": _period(c.get("registration_period"), "end_at"),
    }


def _undetailed(rows: list[dict]) -> int:
    return sum(1 for r in rows if r.get("type") not in CAMPAIGN_TYPES)


def campaign_list(cfg, opts, args):
    shop = common.shop(cfg, opts)
    if not opts.get("group"):
        raise UsageError("campaign list needs --group <channel_campaign_group_id>",
                         [f"Group ids come from `boost campaign groups --shop {shop}`"])
    group = _int64_id(opts.get("group"), "--group")
    pending = _true(opts, "pending_only")
    eligibility = _enum_csv(opts.get("eligibility"), "--eligibility", ELIGIBILITY_FILTERS, single=True)
    types = _enum_csv(opts.get("types"), "--types", CAMPAIGN_TYPES)
    locale = _locale(opts.get("locale"))
    params = {"shop_id": shop, "campaign_group_id": group, "pending_registration_only": pending,
              "eligibility": eligibility, "types": types, "locale": locale}
    rows, cursor, pages = common.fetch_pages(cfg, "/campaigns", params, opts)
    if opts.get("json"):
        common.dump_json({"data": rows, "next_cursor": cursor})
        return 0
    base = common.again("campaign list", *common.flag_pairs(shop=shop, group=group),
                        "--pending-only" if pending else None,
                        *common.flag_pairs(eligibility=eligibility, types=types, locale=locale))
    if not rows:
        render.emit_empty("campaigns", f"shop {shop}, group {group}",
                          common.page_hints(rows, cursor, pages, base, opts, _empty_page_hint(rows, cursor)))
        return 0
    render.emit_table("campaigns", [_campaign_row(c) for c in rows], CAMPAIGN_FIELDS)
    hints = [
        f"{len(rows)} campaigns · eligible / can_register / block_reason come from registration_summary — "
        "the only list-level answer to \"may this shop register?\"",
        NULL_HINT,
        "Detail: `boost campaign get <channel_campaign_id> --shop " + shop + " --type <type>`",
    ]
    skipped = _undetailed(rows)
    if skipped:
        hints.append(f"{skipped} campaigns have type UNMAPPED or null — their detail can't be fetched yet "
                     "(raw type in channel_type, --json)")
    render.emit_help(common.page_hints(rows, cursor, pages, base, opts, hints))
    return 0


def _detail_row(c: dict) -> dict:
    period = c.get("registration_period") or {}
    return {
        "channel_campaign_id": c.get("channel_campaign_id"),
        "title": render.clip(c.get("title")),
        "type": c.get("type"),
        "status": c.get("status"),
        "region": c.get("region"),
        "is_invited": c.get("is_invited"),
        # LIVESTREAM / SHORT_VIDEO answer it top-level; PRODUCT / SHOP inside registration_period
        "registration_status": c.get("registration_status") or period.get("status"),
        "registration_end_at": period.get("end_at"),
    }


def campaign_get(cfg, opts, args):
    shop = common.shop(cfg, opts)
    if not args:
        raise UsageError("campaign get takes a channel_campaign_id",
                         ["boost campaign get <id> --shop <SHOP_ID> --type PRODUCT|SHOP|LIVESTREAM|SHORT_VIDEO"])
    campaign_id = _int64_id(args[0], "campaign id")
    if not opts.get("type"):
        raise UsageError("campaign get needs --type (the type the campaign list returned)",
                         [f"valid values: {' '.join(CAMPAIGN_TYPES)}",
                          "A campaign listed with type UNMAPPED or null can't be fetched yet"])
    ctype = (opts.get("type") or "").strip().upper()
    if ctype not in CAMPAIGN_TYPES:
        raise UsageError(f"unsupported --type '{opts.get('type')}'",
                         [f"valid values: {' '.join(CAMPAIGN_TYPES)}",
                          "A campaign listed with type UNMAPPED or null can't be fetched yet"])
    locale = _locale(opts.get("locale"))
    env = api.request(cfg, "GET", f"/campaigns/{campaign_id}",
                      params={"shop_id": shop, "type": ctype, "locale": locale})
    item = env.get("data") or {}
    if opts.get("json"):
        common.dump_json(item)
        return 0
    render.emit_table("campaigns", [_detail_row(item)], DETAIL_FIELDS)
    eligibility = {k: item[k] for k in ELIGIBILITY_OBJECTS if item.get(k) is not None}
    if eligibility:
        render.emit_detail("eligibility", eligibility)
    present = [k for k in PASS_THROUGH_OBJECTS if item.get(k) is not None and k not in eligibility]
    hints = [
        "May the shop register? Read the eligibility objects above (registration_availability / shop_eligibility "
        "for PRODUCT·SHOP, registration_summary for LIVESTREAM·SHORT_VIDEO); missing = no answer, not \"allowed\"",
        NULL_HINT + "; registration_status is the registration phase, not whether this shop registered",
    ]
    if present:
        hints.append("add --json for " + ", ".join(present) + " (raw TikTok sub-objects, shape may change)")
    hints.append("Registering or leaving a campaign is only possible in Seller Center")
    render.emit_help(hints)
    return 0


# --- registered campaigns -------------------------------------------------------------

def _registered_row(c: dict) -> dict:
    stats = c.get("registration_statistics") or {}
    return {
        "channel_campaign_id": c.get("channel_campaign_id"),
        "title": render.clip(c.get("title")),
        "type": c.get("type"),
        "status": c.get("status"),
        "region": c.get("region"),
        "registered": stats.get("registered_count"),
        "approved": stats.get("approved_count"),
        "under_review": stats.get("under_review_count"),
        "rejected": stats.get("rejected_count"),
        "end_at": _period(c.get("campaign_period"), "end_at"),
    }


def campaign_registered(cfg, opts, args):
    shop = common.shop(cfg, opts)
    name = _name(opts.get("name"))
    types = _enum_csv(opts.get("types"), "--types", CAMPAIGN_TYPES)
    statuses = _enum_csv(opts.get("statuses"), "--statuses", REGISTERED_STATUSES)
    regions = _regions(opts.get("regions"))
    locale = _locale(opts.get("locale"))
    params = {"shop_id": shop, "name": name, "types": types, "statuses": statuses, "regions": regions,
              "locale": locale}
    rows, cursor, pages = common.fetch_pages(cfg, "/registered-campaigns", params, opts)
    if opts.get("json"):
        common.dump_json({"data": rows, "next_cursor": cursor})
        return 0
    base = common.again("campaign registered", *common.flag_pairs(
        shop=shop, name=name, types=types, statuses=statuses, regions=regions, locale=locale))
    if not rows:
        render.emit_empty("registered_campaigns", f"shop {shop}",
                          common.page_hints(rows, cursor, pages, base, opts, _empty_page_hint(rows, cursor)))
        return 0
    render.emit_table("registered_campaigns", [_registered_row(c) for c in rows], REGISTERED_FIELDS)
    hints = [
        f"{len(rows)} registered campaigns · counts are registration_statistics (registered includes rejected "
        "and expired; approved is not \"benefit live\")",
        NULL_HINT + "; status is the campaign's status, not the review status",
        "add --json for bargain_statistics, scheduled / suspended / withdrawal counts and periods",
    ]
    render.emit_help(common.page_hints(rows, cursor, pages, base, opts, hints))
    return 0


def campaign_counts(cfg, opts, args):
    shop = common.shop(cfg, opts)
    env = api.request(cfg, "GET", "/registered-campaigns/counts", params={"shop_id": shop})
    item = env.get("data") or {}
    if opts.get("json"):
        common.dump_json(item)
        return 0
    render.emit_detail("registered_campaign_counts", {
        k: item.get(k) for k in ("all_count", "upcoming_count", "active_count", "ended_count")})
    render.emit_help([
        "The four counts are independent — they need not add up to all_count",
        "active spans registration opening to campaign end (not only running); ended includes deactivated",
        "null = not available from TikTok, not 0",
    ])
    return 0


# --- open collaboration -----------------------------------------------------------------

def _rate_percent(rate) -> str | None:
    try:
        return f"{float(rate) * 100:g}%"
    except (TypeError, ValueError):
        return None


def open_collab_settings(cfg, opts, args):
    shop = common.shop(cfg, opts)
    env = api.request(cfg, "GET", "/open-collaboration-settings", params={"shop_id": shop})
    item = env.get("data") or {}
    if opts.get("json"):
        common.dump_json(item)
        return 0
    auto = item.get("auto_add_product")
    render.emit_detail("open_collaboration_settings", {
        "auto_add_product_enabled": (auto or {}).get("enabled"),
        "commission_rate": (auto or {}).get("commission_rate"),
    })
    rate = _rate_percent((auto or {}).get("commission_rate"))
    hints = [
        "commission_rate is a ratio string" + (f": {auto['commission_rate']} = {rate}" if rate else " (\"0.1000\" = 10%)"),
        "enabled=true: existing non-affiliate products were added once and new products join automatically; "
        "false: new products don't (already added ones stay) · null = TikTok gave no answer",
        "Read-only: open collaboration is changed in Seller Center",
    ]
    render.emit_help(hints)
    return 0


def _sample_rule_row(r: dict) -> dict:
    th = r.get("thresholds") or {}
    unlimited = r.get("is_sample_time_unlimited") is True
    return {
        "channel_product_id": r.get("channel_product_id"),
        "status": r.get("status"),
        "sample_quota": r.get("sample_quota"),
        "available_quantity": r.get("available_quantity"),
        "start_time": "unlimited" if unlimited else r.get("start_time"),
        "end_time": "unlimited" if unlimited else r.get("end_time"),
        "min_followers": th.get("minimum_follower_count"),
        "min_gmv": th.get("minimum_gmv"),
    }


def open_collab_sample_rules(cfg, opts, args):
    shop = common.shop(cfg, opts)
    raw = opts.get("products") or (args[0] if args else None)
    if not raw:
        raise UsageError("open-collab sample-rules takes product ids",
                         ["boost open-collab sample-rules --shop <SHOP_ID> --products <id,id,...>"])
    ids = [p.strip() for p in raw.split(",")]
    if any(not p for p in ids):
        raise UsageError(f"--products has an empty item: '{raw}'")
    for pid in ids:
        if not _OBJECT_ID.fullmatch(pid):
            raise UsageError(f"product id must match [A-Za-z0-9_-]{{1,64}}, got '{pid}'")
    ids = list(dict.fromkeys(ids))
    if not PRODUCT_IDS_MIN <= len(ids) <= PRODUCT_IDS_MAX:
        raise UsageError(f"--products takes {PRODUCT_IDS_MIN}-{PRODUCT_IDS_MAX} ids, got {len(ids)}")
    env = api.request(cfg, "GET", "/open-collaboration-sample-rules",
                      params={"shop_id": shop, "product_ids": ",".join(ids)})
    data = env.get("data") or {}
    rules = data.get("rules") or []
    not_returned = data.get("products_not_returned") or []
    if opts.get("json"):
        common.dump_json({"rules": rules, "products_not_returned": not_returned})
        return 0
    missing_hint = ("not returned = no free-sample rule, does not exist, or not in this shop (the three can't be "
                    "told apart)")
    if not rules:
        render.emit_empty("sample_rules", f"shop {shop}, {len(ids)} product ids", [
            f"None of the {len(ids)} products returned a rule — {missing_hint}",
        ])
        return 0
    render.emit_table("sample_rules", [_sample_rule_row(r) for r in rules], SAMPLE_RULE_FIELDS)
    hints = [f"{len(rules)} of {len(ids)} products have a free-sample rule"
             + (f" · {len(not_returned)} {missing_hint}: {','.join(not_returned)}" if not_returned else ""),
             "start_time/end_time are the sample application window (ISO 8601 UTC); 'unlimited' = any time",
             "min_gmv is TikTok's raw integer (30-day GMV must exceed it); add --json for avg_ec_video_views, "
             "category_ids and predicted_fulfillment_rank thresholds",
             "Read-only: sample rules are changed in Seller Center"]
    render.emit_help(hints)
    return 0


OPEN_COLLAB_FIELDS = ("channel_open_collaboration_id", "status", "commission", "commission_end_at",
                      "channel_product_id", "title", "product_status", "price", "inventory", "showcase_creators",
                      "content_creators")
OPEN_COLLAB_SORTS = ("product_original_price",)
SORT_ORDERS = ("DESC", "ASC")


def _price_range(price: dict | None) -> str | None:
    if not isinstance(price, dict):
        return None
    lo, hi, cur = price.get("minimum_amount"), price.get("maximum_amount"), price.get("currency") or ""
    if lo is None and hi is None:
        return None
    text = str(lo if hi is None or lo == hi else f"{lo}-{hi}") if lo is not None else str(hi)
    return f"{text} {cur}".strip()


def _open_collab_row(c: dict) -> dict:
    commission = c.get("current_commission") or {}
    product = c.get("product") or {}
    rate = commission.get("rate")
    pct = _rate_percent(rate)
    return {
        "channel_open_collaboration_id": c.get("channel_open_collaboration_id"),
        "status": c.get("status") if c.get("status") != "UNMAPPED" else f"UNMAPPED:{c.get('channel_status')}",
        "commission": f"{rate} ({pct})" if rate is not None and pct else rate,
        "commission_end_at": commission.get("end_at"),
        "channel_product_id": product.get("channel_product_id"),
        "title": render.clip(product.get("title")),
        "product_status": (product.get("status") if product.get("status") != "UNMAPPED"
                           else f"UNMAPPED:{product.get('channel_status')}"),
        "price": _price_range(product.get("original_price")),
        "inventory": product.get("inventory"),
        "showcase_creators": c.get("showcase_creator_count"),
        "content_creators": c.get("content_creator_count"),
    }


def _single_enum(value: str | None, flag: str, allowed: tuple, *, lower: bool = False) -> str | None:
    if value is None or not value.strip():
        return None
    v = value.strip().lower() if lower else value.strip().upper()
    if v not in allowed:
        raise UsageError(f"unsupported {flag} '{value}'", [f"valid values: {' '.join(allowed)}"])
    return v


def open_collab_list(cfg, opts, args):
    shop = common.shop(cfg, opts)
    product = (opts.get("product") or "").strip() or None
    product_name = _name(opts.get("product_name"), "--product-name")
    if product and product_name:
        raise UsageError("--product and --product-name can't be combined", ["Search by id or by name, not both"])
    if product and not _OBJECT_ID.fullmatch(product):
        raise UsageError(f"--product must match [A-Za-z0-9_-]{{1,64}}, got '{product}'")
    category = (opts.get("category") or "").strip() or None
    if category is not None:
        category = _int64_id(category, "--category")
    sort = _single_enum(opts.get("sort"), "--sort", OPEN_COLLAB_SORTS, lower=True)
    order = _single_enum(opts.get("order"), "--order", SORT_ORDERS)
    params = {"shop_id": shop, "product_id": product, "product_name": product_name, "category_id": category,
              "sort": sort, "order": order}
    rows, cursor, pages = common.fetch_pages(cfg, "/open-collaborations", params, opts)
    if opts.get("json"):
        common.dump_json({"data": rows, "next_cursor": cursor})
        return 0
    base = common.again("open-collab list", *common.flag_pairs(
        shop=shop, product=product, product_name=product_name, category=category, sort=sort, order=order))
    if not rows:
        render.emit_empty("open_collaborations", f"shop {shop}", common.page_hints(
            rows, cursor, pages, base, opts, _empty_page_hint(rows, cursor) + [
                "No product of this shop is in open collaboration with these filters (ended ones are not listed)"]))
        return 0
    render.emit_table("open_collaborations", [_open_collab_row(c) for c in rows], OPEN_COLLAB_FIELDS)
    hints = [
        f"{len(rows)} products in open collaboration · commission is a ratio string (\"0.1000\" = 10%), "
        "commission_end_at ISO 8601 UTC",
        "TERMINATING = the seller removed it; it ends at commission_end_at · price is the original price range "
        "of all SKUs",
        "showcase_creators = creators who added it to their showcase; content_creators = creators who posted a "
        "live or video with it · null = TikTok gave no answer",
        "Read-only: open collaboration is changed in Seller Center",
    ]
    render.emit_help(common.page_hints(rows, cursor, pages, base, opts, hints))
    return 0


def _locale_flag() -> Flag:
    return Flag("--locale", "BCP-47 language for campaign texts (default en-US), e.g. id-ID", metavar="LOCALE")


COMMANDS = [
    Command(
        path="campaign groups",
        summary="TikTok platform campaign groups a shop can see: type, status, invited, period; read-only, a few seconds",
        handler=campaign_groups,
        flags=[
            common.shop_flag(),
            Flag("--name", "group or campaign name contains (UTF-8 ≤100 bytes)", metavar="TEXT"),
            Flag("--invited-only", "only campaigns the shop is invited to (not with --pending-only)",
                 kind="flag", default=False),
            Flag("--pending-only", "only campaigns with registrations waiting for the seller to confirm",
                 kind="flag", default=False),
            Flag("--registration", "one of: " + " ".join(REGISTRATION_SCOPES), metavar="SCOPE"),
            _locale_flag(),
            *common.page_flags(),
        ],
        examples=[
            "boost campaign groups --shop <SHOP_ID>",
            "boost campaign groups --shop <SHOP_ID> --invited-only --registration UNREGISTERED",
        ],
    ),
    Command(
        path="campaign list",
        summary="Campaigns of one campaign group: type, status, invited, joined, may register (registration_summary)",
        handler=campaign_list,
        flags=[
            common.shop_flag(),
            Flag("--group", "channel_campaign_group_id from `boost campaign groups` (required)", metavar="GROUP_ID"),
            Flag("--pending-only", "only campaigns with registrations waiting for the seller to confirm",
                 kind="flag", default=False),
            Flag("--eligibility", "one of: " + " ".join(ELIGIBILITY_FILTERS), metavar="FILTER"),
            Flag("--types", "comma-separated: " + " ".join(CAMPAIGN_TYPES), metavar="TYPES"),
            _locale_flag(),
            *common.page_flags(),
        ],
        examples=[
            "boost campaign list --shop <SHOP_ID> --group <GROUP_ID>",
            "boost campaign list --shop <SHOP_ID> --group <GROUP_ID> --eligibility ELIGIBLE --types PRODUCT,SHOP",
        ],
    ),
    Command(
        path="campaign get",
        summary="One platform campaign: eligibility, benefits, fees, participation rules (raw TikTok sub-objects)",
        handler=campaign_get,
        flags=[
            common.shop_flag(),
            Flag("--type", "the campaign's type from the list: " + " ".join(CAMPAIGN_TYPES) + " (required)",
                 metavar="TYPE"),
            _locale_flag(),
        ],
        positional="CAMPAIGN_ID", pos_min=1, pos_max=1,
        examples=["boost campaign get <CAMPAIGN_ID> --shop <SHOP_ID> --type PRODUCT --json"],
    ),
    Command(
        path="campaign registered",
        summary="Platform campaigns the shop registered for: status, region, registration / review counts",
        handler=campaign_registered,
        flags=[
            common.shop_flag(),
            Flag("--name", "campaign name contains (UTF-8 ≤100 bytes)", metavar="TEXT"),
            Flag("--types", "comma-separated: " + " ".join(CAMPAIGN_TYPES), metavar="TYPES"),
            Flag("--statuses", "comma-separated campaign statuses: " + " ".join(REGISTERED_STATUSES), metavar="STATUSES"),
            Flag("--regions", "comma-separated campaign regions: ISO 3166-1 alpha-2 or EU", metavar="REGIONS"),
            _locale_flag(),
            *common.page_flags(),
        ],
        examples=[
            "boost campaign registered --shop <SHOP_ID> --statuses ACTIVE,UPCOMING",
            "boost campaign registered --shop <SHOP_ID> --types PRODUCT --json",
        ],
    ),
    Command(
        path="campaign counts",
        summary="How many platform campaigns the shop registered for: all / upcoming / active / ended",
        handler=campaign_counts,
        flags=[common.shop_flag()],
        examples=["boost campaign counts --shop <SHOP_ID>"],
    ),
    Command(
        path="open-collab settings",
        summary="Open collaboration settings of a shop: auto-add new products, default commission rate; read-only",
        handler=open_collab_settings,
        flags=[common.shop_flag()],
        examples=["boost open-collab settings --shop <SHOP_ID>"],
    ),
    Command(
        path="open-collab list",
        summary="Products of a shop in open collaboration: current commission rate, product status, price, "
                "creators; read-only",
        handler=open_collab_list,
        flags=[
            common.shop_flag(),
            Flag("--product", "one TikTok product id (not with --product-name)", metavar="PRODUCT_ID"),
            Flag("--product-name", "product name keyword, UTF-8 ≤100 bytes (not with --product)", metavar="TEXT"),
            Flag("--category", "top-level TikTok category id", metavar="CATEGORY_ID"),
            Flag("--sort", "product_original_price (default: creation time)", metavar="FIELD"),
            Flag("--order", "DESC (default) or ASC", metavar="ORDER"),
            *common.page_flags(),
        ],
        examples=[
            "boost open-collab list --shop <SHOP_ID>",
            "boost open-collab list --shop <SHOP_ID> --product-name serum --sort product_original_price --order ASC",
        ],
    ),
    Command(
        path="open-collab sample-rules",
        summary="Free-sample rules of 1-200 products in open collaboration: quota, window, creator thresholds",
        handler=open_collab_sample_rules,
        flags=[
            common.shop_flag(),
            Flag("--products", "comma-separated product ids (1-200)", metavar="IDS"),
        ],
        pos_max=1,
        examples=["boost open-collab sample-rules --shop <SHOP_ID> --products <id,id>"],
    ),
]
