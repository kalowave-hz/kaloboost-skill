"""Command registry: every noun module contributes Command objects."""

from __future__ import annotations

from ..core import Command
from . import (
    account, attribution, chat, collab, content, creator, event, meta, order, outreach, resolve_job, sample,
    shop_auth, shop_order, webhook,
)

COMMANDS: list[Command] = []
for _mod in (
    account, creator, resolve_job, outreach, chat, collab, sample, content, order, shop_order, shop_auth, attribution,
    event, webhook, meta,
):
    COMMANDS.extend(_mod.COMMANDS)

# noun -> default subcommand when invoked bare (content first: `boost sample` == list)
DEFAULT_SUB = {
    "outreach": "list",
    "chat": "list",
    "collab": "list",
    "sample": "list",
    "content": "list",
    "order": "list",
    "shop-order": "list",
    "shop-return": "list",
    "shop-auth": "create",
    "attribution": "list",
    "event": "list",
    "webhook": "list",
    "config": "show",
}

ALIASES = {
    "caps": "capabilities",
    "shop": "shops",
    "creators": "creator",
    "chats": "chat",
    "collaboration": "collab",
    "collaborations": "collab",
    "samples": "sample",
    "contents": "content",
    "orders": "order",
    "shop-orders": "shop-order",
    "shop-returns": "shop-return",
    "attributions": "attribution",
    "events": "event",
    "webhooks": "webhook",
}
