---
name: kaloboost
description: >
  Use for TikTok Shop creator outreach and affiliate operations, or any question about the
  user's Kaloboost account: DM or invite creators (content, shop products, images inline) and
  cancel outreach, look up creators by handle (email, followers, GMV), save templates, track
  outreach progress and per-creator results, read and reply to creator chats (TikTok Shop
  站内信), collaboration status, free samples and approving / rejecting sample applications,
  creator videos and metrics, affiliate orders and commission, full shop orders and SLA deadlines,
  shop returns / refunds / replacements, coupons and promotions, TikTok platform campaigns and
  open collaboration (settings, free-sample rules, products and commission — including changing open collaboration settings / sample rules and adding / removing products), TikTok Shop Analytics
  (shop GMV / orders / traffic, product and SKU sales rankings), generating TikTok Shop authorization
  links, change events and webhooks — 达人建联、发私信/定向邀约、建联进度、取消建联、达人聊天/站内信收发、
  合作状态、寄样/申样、审核申样、达人视频、联盟订单、佣金归因、店铺全量订单与超时预警、退货/退款/换货、
  平台活动（Campaign）报名资格与已报名活动、公开合作设置/免费样品规则/公开合作商品与佣金（含修改公开合作设置/样品规则、添加/移除商品）、
  店铺经营数据（GMV、订单、流量）与商品/SKU 销售排行、生成绑店授权链接、事件推送.
  Runs via the bundled `boost` CLI (Python, zero install); use it even if the user never
  says "kaloboost".
---

# Kaloboost creator outreach (`boost`)

Kaloboost is the seller-side creator-outreach and shop operations tool for TikTok Shop. This skill
works on the Kaloboost data of the company that owns the API key: its bound shops, outreach,
collaborations, chats with creators, samples, content, affiliate orders, full shop orders and
returns, shop authorization links, and events. Most commands read. The `[write]` commands send
messages to real creators, approve / reject their sample applications, or change webhook settings —
see "Writes" below before using them.

## Run

The CLI ships inside this skill (`scripts/boost.py`, Python 3.11+ stdlib only — nothing to install):

```sh
python3 <this-skill-dir>/scripts/boost.py shops
```

All examples below write `boost` as shorthand for `python3 <this-skill-dir>/scripts/boost.py`.

Output is TOON (token-oriented) on stdout; add `--json` to any command for raw JSON.
Errors are structured on stdout with actionable `help:` lines. Exit codes: 0 ok, 1 error, 2 usage.

## Setup — check this before the first query

Every command needs a KaloData OpenAPI key (sent as the `secret-key` header). It is the same key
the `kalo` CLI of the kalodata skill uses, stored in the same place. Before the first query of a
session run `boost config` and look at `api_key`. If it says `missing`, stop — don't guess a key
and don't retry the query. Walk the user through these steps and wait:

1. **Get a key** — sign in at https://www.kalodata.com/open-center/account and click
   *generate key*. No account yet? Register at https://www.kalodata.com/open-center/home first.
2. **Save it** — `boost config set --key <API_KEY>` (stored in `~/.config/kalodata/config.toml`,
   mode 0600, shared with `kalo`), or set `KALODATA_API_KEY` in the environment.
3. **Access** — data is scoped to the key's company, which needs a Kaloboost account with shops
   bound in Kaloboost. `boost shops` lists what the key can see; an empty list or a
   `COMPANY_NOT_BOUND` error means this company has no Kaloboost data.

**The API key is the only credential.** Never ask the user for a browser login, password,
cookie, `localStorage` / `ssoAccessToken` or any other token, and don't try to sign in to the
Kaloboost website or call its internal APIs: those credentials don't work with this API, and
going around it is not allowed. On `401` / `403` follow the `help:` lines (`ACCOUNT_NOT_ELIGIBLE`
names what the account still needs) — another credential won't fix them.

## First steps in a session

1. `boost shops` — shop ids for `--shop`, and per-shop capabilities. If the user has one shop, or
   names one, save it: `boost config set --shop <SHOP_ID>` so later commands can omit `--shop`.
2. `boost capabilities` if a command answers `CAPABILITY_UNAVAILABLE` — features marked
   `PLANNED`/`UNAVAILABLE` are not open for this key; tell the user instead of retrying.

## Commands

| command | what |
|---|---|
| `boost capabilities` | which features are open for this key; creator regions; rate limits |
| `boost shops` | bound shops → shop_id for --shop; per-shop capabilities |
| `boost creator resolve <@handle\|user_id...>` | TikTok creator → creator_oecuid (≤100); --region |
| `boost creator get <creator_oecuid...>` | profile, contact email/phone, creator level, followers, GMV band; --region |
| `boost creator changes` | creators of a region whose profile or metrics changed; --since |
| `boost resolve-job create\|get\|results` | async resolve of up to 10,000 handles / user ids |
| `boost outreach list` | outreach tasks + send progress; --since |
| `boost outreach get <task_id>` | schedule, invitation products, commission |
| `boost outreach recipients <task_id>` | per-creator send result and failure reason |
| `boost outreach templates` | DM / invitation templates; --method |
| `boost outreach products` | shop products usable in a DM card / invitation, selectable or why not; --method |
| `boost outreach upload-image <path>` | JPG/PNG (≤5 MB) → `image_id` for DM image segments (can take ~75s) |
| `boost outreach create <creator_oecuid...>` | `[write]` send a DM / target invitation, content inline or from a template |
| `boost outreach create-template` | `[write]` save a DM / invitation template in Kaloboost for reuse |
| `boost outreach cancel <task_id>` | `[write]` stop what is not sent yet |
| `boost chat list` | chat conversations with creators, unread counts; --status UNREAD\|UNREPLIED\|STARRED\|ARCHIVED |
| `boost chat counts` | how many conversations are unread / unreplied / archived |
| `boost chat open <creator_oecuid>` | get or start the conversation with a creator → `conversation_id` (sends nothing) |
| `boost chat messages <conversation_id>` | a conversation's messages, sender role (CREATOR / MERCHANT / UNKNOWN) |
| `boost chat upload-image <path>` | JPG/PNG/GIF/WebP (≤10 MB) → url, width, height for chat images |
| `boost chat send <conversation_id>` | `[write]` reply: text, image, product card, text + image/products card, invitation or sample card |
| `boost chat read <conversation_id...>` | mark conversations read (only when the user asks) |
| `boost chat status <conversation_id>` | star / unstar / archive a conversation (only when the user asks) |
| `boost collab list` | collaboration records: cooperate_status, outreach_result; --since |
| `boost collab get <id>` | one collaboration record |
| `boost sample list` | sample requests: status, product, commission, content counts; --since --status |
| `boost sample get <id>` | SKUs, fulfillment, status timeline |
| `boost sample contents <id>` | videos/lives posted for a sample: views, likes, orders |
| `boost sample review <id> --decision APPROVE\|REJECT` | `[write]` approve / reject a `PENDING` sample application on TikTok |
| `boost content list` / `get <id>` | creator videos/lives of a shop with metrics; --creator --published-from |
| `boost order list` | affiliate orders only (`orders` too), by order time; --from --to (≤90 days) |
| `boost shop-order list` | all orders of a shop (not only affiliate): status, ship-by deadline, buyer paid; --from\|--updated-from --status (≤90 days) |
| `boost shop-return list` | returns / refunds / replacements of a shop, seller to-dos and deadlines; --status --type --order (--limit 10-50) |
| `boost shop-auth create` | authorization link for the shop owner: bind a new shop (--region) or re-authorize a bound one (--shop) |
| `boost coupon list` / `get <id>` | seller coupons of a shop: status, claim/redemption window, discount, usage; read-only (create in Seller Center) |
| `boost promotion list` / `get <id>` | seller promotions of a shop: type, status, window, activity prices |
| `boost product diagnose` | TikTok listing diagnoses of 1-200 products: quality, issues, suggestions |
| `boost campaign groups` / `list --group <id>` / `get <id> --type` | TikTok platform campaigns a shop can see: invited, eligibility, benefits, fees; read-only (register in Seller Center) |
| `boost campaign registered` / `counts` | platform campaigns the shop registered for: status, registration / review counts |
| `boost open-collab settings` / `sample-rules` / `list` | open collaboration auto-add + commission, free-sample rules, products in open collaboration |
| `boost open-collab settings set` / `sample-rule set` / `add` / `remove` | `[write]` change open collaboration settings, sample rules, add / remove products (UNKNOWN = read back before retrying) |
| `boost shop-performance` | TikTok Shop Analytics of a shop: GMV, orders, buyers, AOV, refunds, traffic; --from --to (≤90 days) --granularity DAY |
| `boost product-performance` / `sku-performance` | product / SKU sales ranking (TikTok official numbers); --sort --status --categories (--products for SKUs) |
| `boost attribution list` / `get <id>` | affiliate attribution per order line; --creator --order --since |
| `boost event list` | change events (outreach, collab, sample, new chat message); --types --since |
| `boost webhook list` | push endpoints for change events |
| `boost webhook create\|update\|rotate-secret\|test\|replay` | `[write]` manage push endpoints |
| `boost config` | show/set key (shared with kalo), default shop, endpoint |

`content` and `sample_review` are open as `PILOT`. `attribution` and `creator changes` follow the
published API but may still answer `CAPABILITY_UNAVAILABLE` (`PLANNED` / `NOT_IMPLEMENTED`) — tell the
user the feature isn't live yet; `boost capabilities` shows what this key has.

## Writes

`[write]` commands never act on the first run: without `--yes` they print the exact request
(`dry_run:`) and send nothing. Show it to the user, get an explicit yes, then rerun with the flags
the hint gives (`--yes`, plus `--external-id` for `outreach create`). Never add `--yes` on your own.

- **Send outreach** — write the content inline; no template or Kaloboost console needed:
  1. `boost creator resolve @handle --region <shop region>` → `creator_oecuid` (only `MATCHED`;
     tell the user about `NOT_FOUND` / `AMBIGUOUS`, don't guess). This API can't search creators
     by category / followers / region — the user supplies the handles.
  2. Products (invitations need them; DMs only for a product card):
     `boost outreach products --shop S --method <METHOD>` → use only `selectable=true` ids.
  3. Optional DM image: `boost outreach upload-image ./pic.png --shop S` → `image_id`.
  4. Dry run, then the user confirms, then the same command + `--external-id <id from the hint> --yes`:
     - DM: `boost outreach create <oecuid...> --shop S --text 'Hi ${handle}! ...' [--image <image_id>] [--card <product_id>]`
     - Target invitation: `boost outreach create <oecuid...> --shop S --method TIKTOK_TARGET_COLLABORATION
       --invite-name '<≤26 chars>' --invite-message 'Hi ${handle}! ...' --contact WHATSAPP:<number>
       --products <id>[,<id>:0.2] --commission 0.15 [--sync-dm 'Hi ${handle}, just sent you an invite!']`
  5. `boost outreach recipients <task_id> --shop S` for per-creator results (`Accepted` ≠ sent).
     Failures such as `TARGET_INVITATION_UNAVAILABLE_CREATOR` are about the creator, not the
     request: report them and ask the user for other creators instead of resending.
- **Content rules** (checked before sending):
  - The creator placeholder is `${handle}` — it becomes the creator's TikTok username, without
    `@`; don't put `@` in front. Any other form (`{creator}`, `{{name}}`, `$name`) is rejected.
    **Single-quote** text with `${handle}` in a shell, or the shell replaces it with nothing.
  - `--contact` is the merchant's real WhatsApp / email / LINE / … that creators reply to. Ask the
    user for it; never invent one, reuse an example, or take a member's login phone / email for it. Numbers without country prefix or `+`
    (`WHATSAPP:812345678:TH`; the country code defaults to the shop's market).
  - Commission is a ratio 0.01–0.80: 15% is `0.15`. Invite name ≤26 characters, no placeholder;
    invite message ≤500 characters, no emoji. DMs: ≤5 segments, ≤3 images, ≤1950 chars per text.
  - Inline content is all-or-nothing: an unavailable product or bad contact rejects the request
    (nothing is created) — fix what the error names and send again.
- **Templates** are only for content the merchant wants to reuse. `boost outreach templates` lists
  them; `boost outreach create-template --name ... <same content flags>` saves one (an invitation
  needs two: content, and products). Send with `--template <id>` (invitations add
  `--product-template <id>`); template content can't be overridden per request.
- `--operator` is optional: without it everything runs as the key's own Kaloboost account, which
  is what the user normally wants. Only pass a member (login email or `'+86 13800000000'`) when
  the user asks to act as that member or `SHOP_NOT_AUTHORIZED [operator_account/...]` says the own
  account can't manage the shop — then ask the user which member to use; never pick one yourself.
- Up to 10,000 creators per task — no need to split (`--file` for long lists). Big tasks take 1–3
  minutes to create; the CLI waits for them, so let it run. Invitations expire 7 days after the
  start by default (`--expire`); `--at` schedules up to 90 days ahead.
- Outreach calls (create, create-template, upload-image, products) share a limit of 1 call per
  second: run them one at a time. A `503` asking to wait minutes (TikTok verification for the
  shop) means stop and tell the user — don't retry right away.
- **Retrying**: if a write ends with "outcome is unknown" (timeout / 503), rerun the identical
  command with the `--external-id` / `--idempotency-key` the hint shows — it then runs at most
  once. Never retry an outreach with a new external id: that sends a second task.
  `create-template` has no such key: check `boost outreach templates` for it before retrying.
- `CAPABILITY_UNAVAILABLE ... NOT_IMPLEMENTED` on inline content, products, images or template
  creation means this environment (the test env) doesn't have them yet: tell the user; don't
  work around it.
- Sent messages and invitations can't be recalled; `outreach cancel` only stops unsent ones.

## Outreach playbook

Defaults to propose, not rules: say what you plan, and follow the user whenever they choose otherwise.
Ask for the business inputs (commission, sample policy, contact, which products) instead of picking numbers.

- **Who**: this API can't search creators. Take handles from the user, or — when the user agrees —
  from a creator-discovery tool such as the kalodata skill; then `creator resolve` them here.
- **Exclude before sending**, and tell the user who was dropped and why:
  creators with a sample in `UNFULFILLED`, or long in `CONTENT_PENDING` (`boost sample list --all`).
  Invitations skip already-invited creators on their own; `--sync-dedup DAYS_30` does the same for
  the DM. Past partners (`COOPERATED` in `boost collab list`) are worth inviting again, not excluding.
- **Shape**: a target invitation (products, commission, free sample) with a short `--sync-dm`
  converts better than a DM alone. Creators who fail with `TARGET_INVITATION_UNAVAILABLE_CREATOR`
  can get a plain DM instead (`--card <product_id>` puts the product and its image in it) — offer
  that rather than dropping them. Invitation text and the sync DM can't carry images.
- **Copy**: one shared message for a batch. Write per-creator copy (one task each, after looking at
  their content) only for a few high-value creators the user picks — it's slow at scale.
- **Follow up**, where most replies come from — propose, never send unasked:
  `boost chat list --status UNREPLIED` for creators waiting on an answer; invitations with no
  response after a few days (`boost collab list`); samples shipped but no post (`CONTENT_PENDING`).
- Don't resend the same text to the same creators in a short time; TikTok rate-limits and
  flags repetitive outreach.

## Chat with creators

One-to-one TikTok Shop chat between the shop and a creator — replying to what a creator wrote,
following up after an invitation or sample. (Bulk first contact is `outreach create`.)

1. Find the conversation: `boost chat list --shop S --status UNREPLIED` (or `UNREAD`), or for a
   given creator `boost chat open <creator_oecuid> --shop S` (resolve `@handle` first; opening
   sends nothing). `creator_im_id` in the output is TikTok's chat id, not a `creator_oecuid`.
2. Read before replying: `boost chat messages <conversation_id> --shop S`. `sender_role` is often
   `UNKNOWN`; then a `sender_id` equal to the conversation's `creator_im_id` is the creator, any
   other sender is the shop. Old messages don't have the same shape as what you send — build a
   reply from the send flags, don't copy their content.
3. Draft the reply, dry-run `boost chat send <conversation_id> --shop S ...`, show it, and only after
   the user confirms rerun it with `--idempotency-key <key from the dry run> --yes`. The flags pick
   the message type:
   - `--text '...'` (≤2000 chars) — plain text
   - `--image <url> --width W --height H` — url and size from `boost chat upload-image ./pic.png --shop S`
   - `--product <id>` — one product card; `--text '...' --product <id>,<id>` — text with 1–5 products
   - `--text '...' --image <url> [--title '...']` — text-with-image card (text ≤500, title ≤50)
   - `--collab <channel_invite_id>` (from `boost collab get`) — the invitation card;
     `--sample <channel_apply_id>` (from `boost sample get`) — the free-sample card. Not the local
     `invite_id` / `sample_request_id`.
4. `accepted=true` only means TikTok took it, not delivered or read.

- New messages: `boost event list --shop S --types chat.message.created --since 1h` (or a webhook
  with that type). Events hold no text — read it with `chat messages`. Events can be late or
  missing: poll `chat list --status UNREAD` too.
- Nothing marks a conversation read except `boost chat read`; reading or listing doesn't. Leave
  conversations unread, and don't star / archive, unless the user asks — the merchant's team uses
  those states in the Kaloboost inbox.
- **Retrying a send**: if it fails with "may already have been sent" (`OUTCOME_UNKNOWN`) or a
  network error, run `chat messages` first; if the message isn't there, rerun the identical command
  with the same `--idempotency-key`. Only `NOT_SUBMITTED` is safe to rerun straight away. Never
  resend with a new key — the creator would get it twice. Keys are kept 24h.
- Chat writes (open, send, upload-image, read, status) share 1 call per second: one at a time.
  `PLATFORM_REJECTED` is TikTok refusing (quota, risk control, content) — tell the user, don't resend.
- `--operator` works as for outreach: leave it out unless the user asks to act as another member.

## Review sample applications

Creators apply for free samples; the shop approves or rejects each one on TikTok. `boost sample review`
submits that decision to TikTok in real time — it is a `[write]` and **can't be undone**.

1. Find what waits: `boost sample list --shop S --all --status APPLY_TO_REVIEW`; look at the creator
   (`boost creator get <creator_oecuid> --region <shop region>`) and the product before deciding.
   Only applications still `PENDING` on TikTok can be reviewed — the local status may lag.
2. Dry run, show it, and only after the user decides per application rerun with
   `--idempotency-key <key from the dry run> --yes`:
   - approve: `boost sample review <id> --shop S --decision APPROVE`
   - reject: `boost sample review <id> --shop S --decision REJECT --reject-reason NOT_MATCH|OFFLINE|OUT_OF_STOCK|OTHER`
     (TikTok's codes; no free text — ask the user which applies, don't pick one)
   Never approve or reject in bulk on your own judgment: the user decides each one (or gives an explicit rule).
3. Read the answer: `platform` is TikTok's state read back once right after the review;
   `observed=false` only means it wasn't read back, not that the review failed — check `boost sample get`
   later. An approval's `channel_main_order_id` often is still null (TikTok creates it within about a
   minute); when present, keep it — `/samples` gets it only hours to a day later. `replayed=true` means
   TikTok wasn't called again because the decision was already in effect.

- Only shops whose market is US/ID/TH/MY/VN/PH/SG/JP and that authorized TikTok Shop Open API in Kaloboost
  (`SAMPLE_REVIEW` in `boost shops`); others answer `CHANNEL_NOT_AVAILABLE`. Applications an agency
  submitted for a creator (`AGENCY_APPLICATION`) can only be handled in TikTok Seller Center.
- `SAMPLE_NOT_REVIEWABLE` = no longer pending on TikTok (someone handled it, it expired, or the creator
  withdrew): report the state it names; don't retry.
- **Retrying**: after a timeout / 503 rerun the identical command with the same `--idempotency-key` — it
  then runs at most once. Never retry with a new key. If the answer is `SAMPLE_NOT_REVIEWABLE` without a
  state, or `PLATFORM_REJECTED`, after such a timeout, the first try may have worked: check
  `boost sample get <id>` before anything else.
- Limit: 5 reviews per second per key.

## Shop orders, returns, and authorization links

Three separate order-related commands — pick the right one:

- `boost order list` (alias `orders`) — **affiliate orders only** (creator-attributed orders and commission).
- `boost shop-order list` (alias `shop-orders`) — **all orders of a shop** (not only affiliate), with SLA deadlines, fulfillment, cancellation, and payment totals.
- `boost shop-return list` (alias `shop-returns`) — **returns, refunds, replacements, and exchanges** of a shop, with seller to-dos (`seller_actions`) and deadlines.

### Shop orders & returns

- **Availability & scopes**: unlike most capabilities (which do not depend on TikTok scopes), `SHOP_ORDERS` requires both a supported market (`US`, `ID`, `TH`, `MY`, `VN`, `JP`; `PH` is not yet supported) and the TikTok order/return scopes. `SCOPE_MISSING` or `SHOP_NOT_API_AUTHORIZED` means ask the shop owner to re-authorize using `boost shop-auth create --shop <shop_id>`.
- **Serial calls & scheduling**: page one shop serially (don't issue concurrent pages for the same shop). For multi-shop daily reports, query shops one by one and avoid scheduling right on the top of the hour (`:00`) to reduce `429` (`CHANNEL_RATE_LIMITED` / `server_capacity`).
- **Daily report day boundaries**: convert the shop's local calendar day using `time_zone` from `boost shops` (e.g. Indonesia = `Asia/Jakarta` UTC+7; US = `America/Los_Angeles`).
- **GMV & unit counts**: report both `payment.sub_total` (product GMV; US excludes tax, cross-border includes VAT) and `payment.total_amount` (buyer paid) directly from TikTok — do not recompute from formulas. Exclude `UNPAID` / `CANCELLED` and `is_sample_order`, `is_refundable_sample`, `is_replacement_order`, `is_exchange_order`. Unit count is the number of `line_items` (one item per line), which differs from affiliate `order list`'s `items[].quantity`.
- **SLA / overdue warnings**: only check `fulfillment_type = FULFILLMENT_BY_SELLER`, exclude `shipping_type` in `{TIKTOK_DIGITAL, IN-STORE PICKUP}`, and skip orders with `null` deadlines:
  - At risk / overdue to ship: `status` in `{AWAITING_SHIPMENT, PARTIALLY_SHIPPING}` against `deadlines.ship_sla_at` (for partial shipments, `TO_FULFILL` lines use `ship_sla_at` and `PROCESSING` lines use `collect_sla_at`).
  - At risk / overdue for carrier pickup: `status = AWAITING_COLLECTION` against `min(collect_sla_at, pick_up_cut_off_at)` when present.
  - Auto-cancel risk: check `auto_cancel_if_unshipped_at` / `auto_cancel_if_uncollected_at`.
  - Pending buyer cancellation requests: query with `--buyer-cancel-requested true` (response deadline is not in the order payload; estimate ~24h conservatively).
- **Returns grouping & counting**: count only the latest record per chain (`channel_next_return_id` is `null`). Group statuses as:
  - *Seller action needed*: `RETURN_OR_REFUND_REQUEST_PENDING`, `REPLACEMENT_REQUEST_PENDING`, `EXCHANGE_REQUEST_PENDING`, `BUYER_SHIPPED_ITEM` (alert when `seller_actions` has a `deadline` approaching).
  - *Waiting on buyer*: `AWAITING_BUYER_SHIP`, `AWAITING_BUYER_RESPONSE`.
  - *Refund approved / completed*: `RETURN_OR_REFUND_REQUEST_SUCCESS` → `…_COMPLETE`; `REPLACEMENT_REQUEST_REFUND_SUCCESS` and `EXCHANGE_REQUEST_REFUND_SUCCESS` are terminal.
  - *Replacement / exchange approved (new order to ship)*: `REPLACEMENT_REQUEST_COMPLETE`, `EXCHANGE_REQUEST_COMPLETE` (the new `is_replacement_order` / `is_exchange_order` order appears in SLA checks).
  - *Rejected* (not terminal — buyer may open arbitration, check `arbitration_status`): `REFUND_OR_RETURN_REQUEST_REJECT`, `REJECT_RECEIVE_PACKAGE`, `REPLACEMENT_REQUEST_REJECT`.
  - *Canceled*: `RETURN_OR_REFUND_REQUEST_CANCEL`, `REPLACEMENT_REQUEST_CANCEL`, `EXCHANGE_REQUEST_CANCEL`.
- `boost shop-return list` accepts `--limit 10-50` (default 20), and can omit the time window when `--order <channel_order_id>` is passed. Use `return_shipping.tracking_number` only for tracking return arrival.

### Shop authorization links (`boost shop-auth create`)

Generates a TikTok Shop authorization URL (`--region <CC>` to bind a new shop; `--shop <shop_id>` to re-authorize a bound shop, no `--region` needed). Limit: 10 links per 60 seconds; not idempotent.

- **Single-use, 2-hour expiry**: send only to the shop owner, one link per shop. The owner must **complete** authorization before `expires_at` (not just open the page). Any callback with an auth code — even if binding fails — consumes the link; canceling on TikTok's page does not. If a link expires or fails, generate a new one rather than reusing it.
- **Multi-shop accounts**: one authorization binds only the **first** shop TikTok returns. To bind additional shops under the same TikTok seller account, use the Kaloboost web console (or contact Kaloboost). Re-authorizing an already-bound shop with `--shop` matches that specific shop.
- **Owner redirect & error codes**: after authorizing, the browser redirects to Kaloboost's bind-shop page (`?error=<code>`). That page requires a Kaloboost login, so the owner may not see the result. Possible error codes: `SHOP_COUNT_LIMIT` (quota full at bind time), `SHOP_AUTH_OTHER_COMPANY` (already bound to another company), `SHOP_AUTH_COOKIE_DIFF` (wrong shop authorized for `--shop`), `OPENAPI_LINK_ALREADY_USED` (replayed/concurrent click), `OPENAPI_LINK_DISABLED` (feature paused), `SHOP_BIND_REGION_NOT_OPEN`, `BIND_FAILED`. An **expired** link fails silently without an explicit error.
- **How to confirm completion**: for a new shop, check `boost shops`. For re-authorization, rerun the previously failing call (e.g. `boost shop-order list` over a short window) — `SHOP_ORDERS` in `boost shops` can already appear when scopes are unknown or a token expired, so it is not proof of re-authorization. Poll roughly every 30s and stop 10 minutes after `expires_at`.
- **Risk & side effects**: TikTok's authorization page shows only the app name, not the company — confirm the owner before sending, as once bound the shop's orders and returns are immediately visible to this company's key holders and enabled agents. Binding or re-authorizing switches the caller's active shop in the Kaloboost web console and assigns the shop to the caller. Opening the link does **not** sign the owner into Kaloboost.

## Coupons, promotions, and product diagnoses

Three read-only views of a shop's seller marketing tools, live from TikTok (nothing stored in Kaloboost):

- `boost coupon list` (alias `coupons`) — seller coupons: status, claim window, redemption window, discount, usage.
- `boost promotion list` (alias `promotions`) — seller-created promotions (discounts, flash sales, shipping discounts, bundles, gifts — not TikTok platform campaigns): type, status, time window, products.
- `boost product diagnose --products <id,id,...>` — TikTok's own listing diagnoses for 1-200 products of a shop.

### Coupons & promotions

- **Availability & scopes**: `SHOP_PROMOTIONS` / `PRODUCT_DIAGNOSIS` need the TikTok scopes `seller.promotion.info` and `serller.product.optimize` (TikTok's own spelling). There is no market list — it is purely per-shop scopes; US/JP/PH apps currently do not carry these scopes, so those shops answer 422 `SCOPE_MISSING`. `SCOPE_MISSING` or `SHOP_NOT_API_AUTHORIZED` means ask the shop owner to re-authorize with `boost shop-auth create --shop <shop_id>`.
- **Coupons are read-only**: creating or editing a coupon is only possible in Seller Center — never promise to create one.
- **Expiry checks**: look at `status` together with `claim_end_time` (end of the claim window). A coupon whose `redemption.type` is `RELATIVE` has **no absolute expiry** — buyers redeem within `relative_days` of claiming; only `ABSOLUTE` redemptions have a `redemption.end_time`.
- **Money**: coupon amounts carry ISO currency (`IDR`/`MYR`/`THB`/`VND`/`PHP`/…); promotion activity prices carry whatever currency TikTok returns, as-is.
- **Pass-through objects**: a promotion's `discount` configuration and `participation_limit` are raw TikTok sub-objects, forwarded unchanged — do not assume a fixed shape inside them; `UNMAPPED` type/status means TikTok added a value, the raw one is in `channel_type`/`channel_status`.

### Product diagnoses

- **Missing ids**: a requested id that is absent from the response does not exist or does not belong to this shop — it is not an error. Products in `DELETED`/`FREEZE`/`DRAFT`/`SELLER_DEACTIVATED` still answer their diagnoses.
- **`listing_quality` is US-only**: products in Indonesia, Thailand, Malaysia (and other non-US markets) answer `null` — report it as "not scored", not as a zero/bad score.
- **Reading issues**: each entry under `diagnoses[]` is one field (`IMAGE`, `TITLE`, …) with `issues[]` (machine `code` + human `how_to_solve`, often in the shop's local language) and `suggestion` (`seo_words` / `smart_texts`).

## Platform campaigns and open collaboration

Live from TikTok (nothing stored in Kaloboost). **You can't register for or leave a campaign here**
— that is done in Seller Center; never promise it. Open collaboration, on the other hand, **can be
changed here** with the `[write]` commands below — read "Changing open collaboration" before using them.

- `boost campaign groups` (alias `campaigns`) — TikTok **platform** campaign groups (not the seller's own promotions — those are `boost promotion`). Takes a few seconds per page; don't loop it.
- `boost campaign list --group <channel_campaign_group_id>` — campaigns of one group, with the list-level eligibility answer.
- `boost campaign get <channel_campaign_id> --type <type>` — one campaign; `--type` is the `type` the list returned.
- `boost campaign registered` / `boost campaign counts` — campaigns the shop registered for, and their counts.
- `boost open-collab settings` (alias `open-collaboration`) — auto-add products to open collaboration, default commission.
- `boost open-collab sample-rules --products <id,id,...>` — free-sample rules of 1-200 products.
- `boost open-collab list` — the shop's products in open collaboration with their current commission; `--product <id>` or `--product-name <keyword>` (not both), `--category <top-level id>`, `--sort product_original_price --order ASC|DESC` (default: creation time).
- `boost open-collab settings set` — `[write]` change auto-add and the default commission; `--enable` or `--disable`, `--commission` required either way.
- `boost open-collab sample-rule set <product_id>` — `[write]` activate (`--status ACTIVE --quota N --unlimited` or `--start/--end`, optional thresholds) or deactivate (`--status INACTIVE`) a product's free-sample rule.
- `boost open-collab add <product_id> --commission <rate>` — `[write]` put one product into open collaboration.
- `boost open-collab remove <product_id>` — `[write]` remove one product; effective midnight shop time, can't be undone.

### Reading campaigns right

- **`null` = TikTok gave no answer.** TikTok omits booleans and counts it has no conclusion on; a `null` `is_invited`, `has_joined`, `is_eligible`, `is_registration_available` or count is **unknown — never report it as false, 0 or "may register"**. Explicit `false` / `0` / `[]` are real answers.
- **Can the shop register?** Only `registration_summary` (list: `is_eligible`, `is_registration_available`, `registration_block_reason.code`/`message`) or the detail's eligibility objects (`registration_availability` / `shop_eligibility` for PRODUCT / SHOP, `registration_summary` for LIVESTREAM / SHORT_VIDEO) answer it. Being invited (`is_invited`), the campaign `status`, or the registration phase (`registration_status` / `registration_period.status`) are **not** eligibility; a missing eligibility object is not "allowed".
- **Detail needs a known type**: a campaign listed with `type` `UNMAPPED` or `null` can't be fetched with `campaign get` yet (raw value in `channel_type`). An id that doesn't exist, isn't visible to the shop, or is passed with the wrong `--type` answers 404 `RESOURCE_NOT_FOUND`.
- **Raw sub-objects**: detail objects such as `benefits`, `fees`, `participation_rules`, `registration_availability`, `shop_participation`, `agreement`, `participation_requirements` are TikTok's own sub-objects forwarded unchanged (TikTok key names, RFC 3339 times) — their shape may change; read them, don't assume fields.
- **Times** (`*_period.start_at`/`end_at`, `query_time`) are ISO 8601 UTC. A `null` period edge is unknown, not unbounded.
- **Paging**: only a null `next_cursor` ends a list — an empty page can still carry a cursor; follow the `More:` hint or `--all`.
- **`campaign counts`**: `all_count`, `upcoming_count`, `active_count`, `ended_count` are independent and need not add up; `active` spans registration opening to campaign end; `null` = not available, not 0.
- **Registered stats**: `registered_count` includes rejected and expired; `approved_count` is not "benefit live"; `scheduled_count` must not be added to `approved_count`; `under_review_count` is TikTok review, not "waiting for the seller".

### Reading open collaboration right

- **Open collaboration products** (`open-collab list`): `current_commission.rate` is a ratio string — `"0.1000"` = 10%; `start_at`/`end_at` are ISO 8601 UTC. `status` `NORMAL` = active, `TERMINATING` = the seller removed it and it ends at `end_at` (ended ones aren't listed); `UNMAPPED` carries TikTok's raw value in `channel_status`. `product.status` is `LIVE` / `OUT_OF_STOCK` / `SELLER_DEACTIVATE` / `PLATFORM_DEACTIVATE` / `GNE_REJECT` / `DELETE` / `OTHER`; `original_price` is the min-max original price over all SKUs. `showcase_creator_count` = creators who added it to their showcase, `content_creator_count` = creators who posted a live or video with it.
- **`commission_rate`** is a ratio string: `"0.1000"` = 10%. `enabled=true` means existing non-affiliate products were added once and new products join automatically; `false` means new products don't (already added ones stay).
- **Sample rules**: a product absent from `rules` is listed in `products_not_returned` — it has **no free-sample rule, does not exist, or is not in this shop** (TikTok doesn't say which); it is not an error, and an all-missing request still answers 200 with empty `rules`. `is_sample_time_unlimited=true` means any time (no `start_time`/`end_time`); thresholds (`minimum_follower_count`, `minimum_gmv` — TikTok's raw integer, `avg_ec_video_views`, `category_ids`, `predicted_fulfillment_rank`) are minimums a creator must meet.

### Changing open collaboration

The four `[write]` commands submit to TikTok in real time. Like every write they print the exact
request (method, path, body, Idempotency-Key) without `--yes` and send nothing: show it, and only
rerun with `--idempotency-key <key from the dry run> --yes` after the user confirms. They answer a
uniform `data.outcome` instead of a plain success:

- **`SUBMITTED`** — TikTok took it. `observed=READ_BACK` means the new state was also read back;
  anything less is not a failure, but verify with the read command when it matters.
- **`PLATFORM_REJECTED`** — TikTok refused (`reason` / `channel_code` say why). Don't resend the
  same thing; tell the user.
- **`NOT_SUBMITTED`** — nothing reached TikTok; once the cause is fixed, rerun the identical
  command with the same `--idempotency-key`.
- **`UNKNOWN`** — **the change may already be in effect. Do not retry — not even with the same
  key.** Read back first: `boost open-collab settings` / `open-collab sample-rules --products <id>`
  / `open-collab list --product <id>`. Only if the read-back shows the change did *not* happen,
  rerun the identical command with the same key. Never retry with a new key — it could apply twice.
  The same applies when the call itself dies (timeout / 503): retry with the same key, and if the
  answer comes back `UNKNOWN`, switch to read-back.

Rules of the operations themselves:

- **Commission is a ratio string 0.01–0.80** (1%–80%, at most 4 decimals): 15% is `0.15`, `"0.1000"` = 10%.
- **`settings set` always takes both** `--enable`/`--disable` *and* `--commission` — TikTok has no
  "keep the current rate" form. Read the current settings first and reuse the rate unless the user
  wants it changed.
- **`sample-rule set`** needs `--quota` (total free samples) and either `--unlimited` (creators can
  apply at any time) or **both** `--start` and `--end` (the application window, ISO 8601 UTC or
  relative `24h`/`7d` from now; end after start). Thresholds (`--min-followers`, `--min-gmv`,
  `--min-avg-video-views`, `--category-ids`, `--fulfillment-rank`) are minimums a creator must meet
  to apply. `--status INACTIVE` takes no other field — it just turns the rule off.
- **`add` is idempotent on TikTok**: adding a product that already is in open collaboration returns
  the existing collaboration, not an error. But a success can still mean **nothing was created**
  when the product doesn't exist — always verify with `open-collab list --product <id>`.
- **`remove` can't be undone** and normally takes effect at **midnight in the shop's timezone**
  (`terminated_effective_at`); until then the product shows as `TERMINATING`. Confirm the user means
  it before `--yes`.

### Availability & scopes

- Campaigns are part of `SHOP_PROMOTIONS` and need the TikTok scope `seller.promotion.info`. US / JP / PH apps don't carry it, so shops there answer 422 `SCOPE_MISSING` — tell the user campaigns aren't available for that shop's market (re-authorizing won't add a scope the app doesn't have).
- Open collaboration is `OPEN_COLLABORATION` and needs `seller.affiliate_collaboration.read`, which nearly every market's app carries — **US shops included**. A 422 `SCOPE_MISSING` there means ask the shop owner to re-authorize: `boost shop-auth create --shop <shop_id>`.
- `boost shops` lists both keys per shop.

## Shop, product and SKU performance (TikTok Shop Analytics)

Read-only, live from TikTok Shop Analytics — **TikTok's official numbers for the shop's own sales**,
not KaloData's estimates (KaloData is T+1 market-wide data with its own method; the two won't match,
don't mix them in one comparison).

- `boost shop-performance` — one shop's GMV, orders, SKU orders, items sold, buyers, AOV, refunds, product impressions / clicks, conversion; `--granularity DAY` = one row per day (default `ALL` = one total row). `--json` has the full `sales` / `traffic` / `breakdowns` objects (live / video / product-card GMV, creator vs seller, shipping, tax, cancellations and returns).
- `boost product-performance` — product ranking; `--sort gmv|items_sold|orders --order DESC|ASC`, `--status LIVE|INACTIVE|ALL`, `--categories <id,id>`.
- `boost sku-performance` — SKU ranking; `--sort gmv|sku_orders|units_sold`, same filters, plus `--products <id,id>` (≤100) for the SKUs of some products.
- All three take `--from` / `--to`. **Money is always the shop's local currency** — there is no USD option (TikTok's USD conversion didn't fully take effect in testing, so it isn't offered); convert yourself before comparing shops in different currencies.

### Reading performance right

- **Dates are calendar days in the shop's timezone** (`yyyy-MM-dd`, not ISO times), `--from` inclusive, **`--to` exclusive**: one day D is `--from D --to D+1`; "the last 7 days" is `--from <today − 7> --to <today>` — the default when both are omitted (the CLI uses your local date, which approximates the shop's timezone). `--from 30d` = 30 days before `--to`. `--to` must be after `--from`; **at most 90 days per call** — split longer ranges.
- **Data lags a day (T-1)**: `latest_available_date` is the last day whose offline data is ready; days after it (usually today, and future dates) come back empty or incomplete — say so instead of reporting a drop.
- **Rates are decimal strings**: `"0.0843"` = 8.43% (`ctr`, `add_cart_rate`, `click_order_rate`, `unique_ctr`, `avg_conversation_rate`, …). Money is `{amount, currency}` in the shop's local currency; `currency` is its ISO 4217 code (`IDR`, `MYR`, `THB`, …).
- **Product performance**: `total_performance` (all channels) has fixed fields (`gmv`, `orders`, `items_sold`, `sku_orders`, `estimated_customers`, `aov`, impressions / clicks / `ctr`, add-to-cart, `click_order_rate`, refunds); the 7 channel objects (`seller_live_performance`, `seller_video_performance`, `seller_product_card_performance`, `affiliate_total_performance`, `affiliate_live_performance`, `affiliate_video_performance`, `shop_tab_performance`) are TikTok's raw sub-objects forwarded unchanged — read them, don't assume fields.
- **Ids**: `channel_sku_id` / `channel_product_id` are decimal strings that can exceed 2^53 — keep them as text.
- **Paging**: a page can be shorter than `--limit` or even empty; only a null `next_cursor` ends the list. The cursor is bound to the shop, dates, sort and filters — follow the `More:` hint as printed.

### Availability & scopes

- The three performance commands are `SHOP_ANALYTICS` and need the TikTok scope `data.shop_analytics.public.read`. **The JP app doesn't carry it** — JP shops answer 422 `SCOPE_MISSING` and re-authorizing won't help; tell the user it isn't available for Japan. Some earlier-authorized **Indonesia** shops (and the odd shop elsewhere) lack it too: there a 422 `SCOPE_MISSING` means ask the shop owner to re-authorize — `boost shop-auth create --shop <shop_id>`.
- `open-collab list` is `OPEN_COLLABORATION` and needs `seller.affiliate_collaboration.read`, available in every market; a `SCOPE_MISSING` there is also fixed by re-authorizing.
- `boost shops` lists `SHOP_ANALYTICS` per shop.

## Conventions

- Shop-level commands need `--shop <shop_id>` from `boost shops` (or a saved default)
- Lists take `--limit` (1-100; exception: `shop-return list` takes 10-50, default 20) `--cursor` `--all`. To page, run the exact command in the `More:`
  hint — a cursor only works with the same `--shop`/`--since`/`--from`/`--to` it was issued with,
  and expires after 24h. `--all` follows cursors for up to 20 pages
- `--since` / `--from` / `--to` take `30m`, `24h`, `7d`, `yyyy-MM-dd` or ISO 8601 UTC — except the
  performance commands (`shop-performance`, `product-performance`, `sku-performance`): shop-timezone
  `yyyy-MM-dd` only (`--from` also takes `Nd`), `--to` exclusive
- Creator commands are per market: `--region US` (default), GB ID TH VN PH MY SG JP MX BR DE ES FR IT NL IE PL
- Run `boost <command> --help` for per-command flags and examples

## Typical flows

- Outreach progress: `boost outreach list --shop S --since 7d` → `boost outreach recipients <task_id> --shop S`
- Who agreed to work with us: `boost collab list --shop S --since 30d --all` → filter `cooperate_status`
- Sample follow-up: `boost sample list --shop S --all --status CONTENT_PENDING` (shipped, no post yet)
  → `boost creator get <creator_oecuid> --region <shop region>` for the contact email
- Did the samples pay off: `boost sample contents <id> --shop S` (views, orders per video) and
  `boost order list --shop S --from 30d --all` (affiliate GMV and commission by creator)
- Look up a creator: `boost creator resolve @handle --region US` → `boost creator get <creator_oecuid>`
- Many creators (>100): `boost resolve-job create --file handles.txt --region US` → `boost resolve-job get <job_id>`
  until it finishes → `boost resolve-job results <job_id> --all`
- Reply to creators: `boost chat list --shop S --status UNREPLIED` → `boost chat messages <id> --shop S`
  → `boost chat send <id> --shop S --text '...'` (dry run → user confirms → `--idempotency-key <key> --yes`)
- Get pushed instead of polling: `boost webhook create --url https://... --shop S` (dry run → `--yes`);
  store the one-time `secret`. Missed events: `boost webhook replay <endpoint_id> --from 24h`

## Reading the data right

- **Creator GMV**: `gmv` is exact for only ~2–5% of creators; `"0"` or null means *unknown*, not
  zero. Quote `gmv_range` to the user, and never rank or drop creators by `gmv`.
- **Outreach counts**: `total − sent_ok − sent_fail` is not-yet-sent or canceled, not failed.
  `AUTOMATION` tasks may never finish; their counts keep growing.
- **Collaboration**: `cooperate_status` is the shop↔creator relationship (COOPERATED >
  SAMPLE_COOPERATED > NOT_COOPERATED); `outreach_result` is this one invitation (null for DMs).
  Times before 2026-09-11 can be ~8h late.
- **Samples**: no status is final (COMPLETED/CANCELED/EXPIRED can still change) — `curr_status`
  is the truth. `EXPIRED`, `REJECTED`, and `CANCELED` mean the application never shipped
  (`fulfillment.channel_main_order_id` is `0` and `shipped_time` is null) — they are not shipped
  samples. `delivered_time` is always null today. `--since` can miss some changes; for a
  complete picture list without `--since`. `sample get` on an old id may return a new merged id.
- **Sample content metrics** are snapshots, often stale for older posts; don't sum across calls.
- **Affiliate orders** are read live from TikTok (only US/ID/TH/MY/VN/PH/SG/JP shops that authorized
  TikTok Shop Open API in Kaloboost; others answer `CHANNEL_NOT_AVAILABLE`). Settlement and
  refunds change after the fact — re-pull the window rather than adding up earlier runs. Use
  `--all` for complete orders: one order can span two pages.
- **Events** reflect the object at detection time and are kept 30 days; several changes can merge
  into one event, so they are not a step-by-step history. Webhooks push the same events.
- **Outreach create** answers `Accepted` before anything is sent; target invitations skip creators
  already invited, so `total_count` can be below the number you sent.
- **Stay inside this CLI.** For Kaloboost questions answer from what `boost` returns, scoped to the
  key's own company. Don't go looking for Kaloboost databases, tables or web-console APIs. Data
  from other tools (e.g. kalodata for finding creators) only comes in when the user agrees to it,
  and say which numbers came from where.
