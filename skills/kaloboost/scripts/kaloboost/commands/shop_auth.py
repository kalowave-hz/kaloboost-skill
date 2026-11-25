"""`boost shop-auth` — a TikTok authorization link that binds (or re-authorizes) a shop for the shop owner.

Named `shop-auth`, not `shop authorize`: `shop` is already an alias of `shops`.
"""

from __future__ import annotations

from .. import api, render
from ..core import Command, Flag
from ..errors import UsageError
from . import common


def create(cfg, opts, args):
    # Only an explicit --shop means re-authorization: the config default shop must not turn a
    # new-shop link into one for an already bound shop.
    shop = (opts.get("shop") or "").strip() or None
    region = (opts.get("region") or "").strip().upper() or None
    if not shop and not region:
        raise UsageError(
            "give --region <CC> for a new shop, or --shop <SHOP_ID> to re-authorize a bound shop",
            ["example: boost shop-auth create --region ID", "example: boost shop-auth create --shop <SHOP_ID>"],
        )
    if region is not None and region not in common.REGIONS:
        raise UsageError(f"unknown region '{region}'", [f"valid regions: {' '.join(common.REGIONS)}"])
    body = {k: v for k, v in (("shop_region", region), ("shop_id", shop)) if v}
    # No Idempotency-Key: the endpoint doesn't read one; a repeated call only yields another expiring link.
    env = api.request(cfg, "POST", "/shop-authorization-links", body=body)
    data = env.get("data") or {}
    if opts.get("json"):
        common.dump_json(data)
        return 0
    render.emit_detail("shop_authorization_link", {
        "authorization_url": data.get("authorization_url"),
        "shop_region": data.get("shop_region"),
        "expires_at": data.get("expires_at"),
    })
    if shop:
        confirm = (f"After the owner authorizes, rerun the command that failed (e.g. `boost shop-order list --shop {shop} "
                   "--from 1d`) — success there is the proof; `boost shops` capabilities are not")
    else:
        confirm = "After the owner authorizes, the new shop shows up in `boost shops`"
    render.emit_help([
        "Send this link only to the shop owner, one link per shop; it works once (a failed authorization uses it "
        "up too; cancelling on the TikTok page does not)",
        "The owner must finish authorizing before expires_at; an expired or used link binds nothing and shows no "
        "error — just create a new one",
        confirm + "; check every 30s and stop 10 minutes after expires_at, then ask the owner what the TikTok page said",
        "Only the first shop TikTok returns is bound; other shops of the same seller account go through the "
        "Kaloboost web console",
        "Don't post the link in group chats or logs: whoever completes it binds a shop into this company",
    ])
    return 0


COMMANDS = [
    Command(
        path="shop-auth create",
        summary="TikTok authorization link for the shop owner: bind a new shop, or re-authorize a bound one (--shop)",
        handler=create,
        flags=[
            Flag("--region", "market of a new shop: " + " ".join(common.REGIONS), metavar="REGION"),
            Flag("--shop", "re-authorize this bound shop_id (SCOPE_MISSING / SHOP_NOT_API_AUTHORIZED); --region "
                 "not needed", metavar="SHOP_ID"),
        ],
        examples=[
            "boost shop-auth create --region ID",
            "boost shop-auth create --shop <SHOP_ID>",
        ],
    ),
]
