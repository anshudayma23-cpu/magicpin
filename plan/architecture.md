# Vera Merchant AI — System Architecture

**Version**: 1.0 | **Date**: 2026-04-30

---

## 1. System Overview

Vera is a stateful HTTP bot that receives context pushes from a judge harness, decides when to proactively message merchants/customers, and handles multi-turn conversations.

```
┌─────────────────────────┐              ┌──────────────────────────────────┐
│  Judge Harness          │              │  Vera Bot (FastAPI)              │
│  - Pushes contexts      │─── HTTP ───►│                                  │
│  - Sends ticks          │              │  ┌────────────┐ ┌─────────────┐ │
│  - Plays merchant role  │◄── HTTP ────│  │ Context    │ │ Conversation│ │
│  - Scores output        │              │  │ Store      │ │ Manager     │ │
│                         │              │  └─────┬──────┘ └──────┬──────┘ │
└─────────────────────────┘              │        │               │        │
                                         │  ┌─────▼───────────────▼──────┐ │
                                         │  │     Composition Engine     │ │
                                         │  │  (LLM + Prompt Dispatch)   │ │
                                         │  └────────────────────────────┘ │
                                         └──────────────────────────────────┘
```

---

## 2. Five Endpoints (Technical Contract)

| Endpoint | Method | Purpose | Latency |
|---|---|---|---|
| `/v1/healthz` | GET | Liveness + context counts | <2s |
| `/v1/metadata` | GET | Team identity | <2s |
| `/v1/context` | POST | Receive context pushes (idempotent by scope+id+version) | <5s |
| `/v1/tick` | POST | Periodic wake-up; bot returns proactive actions | <10s |
| `/v1/reply` | POST | Receive merchant/customer reply; bot responds | <10s |

### Response Schemas

**`/v1/healthz`** → `{ status, uptime_seconds, contexts_loaded: {category, merchant, customer, trigger} }`

**`/v1/metadata`** → `{ team_name, team_members, model, approach, contact_email, version, submitted_at }`

**`/v1/context`** → `{ accepted: true, ack_id, stored_at }` or `{ accepted: false, reason, current_version }`

**`/v1/tick`** → `{ actions: [{ conversation_id, merchant_id, customer_id, send_as, trigger_id, template_name, template_params, body, cta, suppression_key, rationale }] }`

**`/v1/reply`** → `{ action: "send"|"wait"|"end", body?, cta?, wait_seconds?, rationale }`

---

## 3. Four-Context Data Model

### 3.1 CategoryContext (slow-changing, shared per vertical)

5 categories: `dentists`, `salons`, `restaurants`, `gyms`, `pharmacies`.

| Field | Type | Purpose |
|---|---|---|
| `slug` | str | Category identifier |
| `voice` | VoiceProfile | tone, vocab_allowed, vocab_taboo, salutation_examples |
| `offer_catalog` | list[OfferTemplate] | Service+price patterns (e.g. "Dental Cleaning @ ₹299") |
| `peer_stats` | PeerStats | avg_rating, avg_ctr, avg_reviews — for comparative anchors |
| `digest` | list[DigestItem] | Weekly research/compliance/CDE/trend items with source citations |
| `patient_content_library` | list[ContentItem] | Shareable patient-education content |
| `seasonal_beats` | list[SeasonalBeat] | Month-range patterns (e.g. "Nov-Feb bruxism spike") |
| `trend_signals` | list[TrendSignal] | Search query trends with YoY deltas |

### 3.2 MerchantContext (per-business state, refreshed daily)

50 merchants (10 per category). Key fields:

| Field | Type | Purpose |
|---|---|---|
| `merchant_id` | str | Unique ID |
| `category_slug` | str | Links to CategoryContext |
| `identity` | Identity | name, city, locality, languages, owner_first_name |
| `subscription` | Subscription | status, plan, days_remaining |
| `performance` | PerformanceSnapshot | views, calls, directions, ctr + 7d deltas |
| `offers` | list[MerchantOffer] | Active/expired offers |
| `conversation_history` | list[Turn] | Previous Vera interactions with engagement tags |
| `customer_aggregate` | CustomerAggregate | Roster stats (unique YTD, lapsed count, retention %) |
| `signals` | list[str] | Derived flags: stale_posts, ctr_below_peer, dormant, etc. |
| `review_themes` | list[ReviewTheme] | Sentiment clusters from recent reviews |

### 3.3 TriggerContext (event-driven, per-message)

25 seed triggers expanding to 100. Two families:

**External**: festival, IPL match, regulation change, research digest, competitor opened, seasonal demand shift

**Internal**: perf_dip, perf_spike, milestone, recall_due, customer_lapsed, dormant_with_vera, curious_ask_due, active_planning_intent

| Field | Type | Purpose |
|---|---|---|
| `id` | str | Unique trigger ID |
| `scope` | "merchant" or "customer" | Who this targets |
| `kind` | str | Trigger type for prompt dispatch |
| `source` | "external" or "internal" | Origin classification |
| `merchant_id` | str | Target merchant |
| `customer_id` | str or null | Target customer (if scope=customer) |
| `payload` | dict | Kind-specific data |
| `urgency` | int (1-5) | Priority ranking |
| `suppression_key` | str | Dedup key |
| `expires_at` | datetime | Staleness cutoff |

### 3.4 CustomerContext (optional, for customer-facing messages)

15 seed customers expanding to 200.

| Field | Type | Purpose |
|---|---|---|
| `customer_id` | str | Unique ID |
| `merchant_id` | str | Which merchant they belong to |
| `identity` | CustomerIdentity | name, language_pref, age_band |
| `relationship` | Relationship | first_visit, last_visit, visits_total, services, LTV |
| `state` | enum | new, active, lapsed_soft, lapsed_hard, churned |
| `preferences` | Preferences | preferred_slots, channel, training_focus, etc. |
| `consent` | Consent | opted_in_at, scope array |

---

## 4. Core Components

### 4.1 Context Store

In-memory versioned store keyed by `(scope, context_id)`.

```python
class ContextStore:
    _store: dict[tuple[str, str], ContextEntry]  # (scope, context_id) -> entry

    def upsert(scope, context_id, version, payload) -> UpsertResult:
        # Idempotent: reject if version <= current
        # Atomic replace on higher version

    def get(scope, context_id) -> ContextEntry | None
    def get_all(scope) -> list[ContextEntry]
    def counts() -> dict[str, int]  # for /healthz
```

**Version conflict handling**: Same version → 409 stale_version. Higher version → atomic replace. Lower version → 409.

### 4.2 Conversation Manager

Tracks active conversations and turn history.

```python
class ConversationManager:
    _conversations: dict[str, ConversationState]

    def start(conversation_id, merchant_id, customer_id, trigger_id) -> None
    def add_turn(conversation_id, role, message) -> None
    def get_state(conversation_id) -> ConversationState
    def is_ended(conversation_id) -> bool
    def mark_ended(conversation_id, reason) -> None
```

**ConversationState** includes: turns list, merchant_id, customer_id, trigger_id, auto_reply_count, started_at, is_ended.

### 4.3 Composition Engine

The LLM-prompted composer that produces messages from contexts.

```python
class CompositionEngine:
    def compose_proactive(category, merchant, trigger, customer=None) -> TickAction
    def compose_reply(conversation_state, merchant_reply, category, merchant, customer=None) -> ReplyAction
```

### 4.4 Prompt Dispatch (by trigger.kind)

Different trigger kinds use different prompt variants:

| Trigger Kind | Prompt Focus | Key Lever |
|---|---|---|
| `research_digest` | Source citation, clinical framing, peer tone | Curiosity + Reciprocity |
| `recall_due` | Slot offering, patient name, language match | Specificity + Effort externalization |
| `perf_dip` / `perf_spike` | Data anchoring, comparative peer stats | Loss aversion + Social proof |
| `ipl_match_today` | Counter-intuitive insight, existing offer leverage | Loss aversion + Specificity |
| `supply_alert` | Urgency, batch specificity, workflow offer | Urgency + Effort externalization |
| `customer_lapsed_hard` | No-shame framing, new offering match, free trial | Reciprocity + Binary CTA |
| `curious_ask_due` | Low-stakes question, reciprocity offer | Asking the merchant |
| `active_planning_intent` | Complete drafted artifact, tiered pricing | Effort externalization |
| `competitor_opened` | Voyeur-curiosity framing, differentiation | Curiosity + Loss aversion |
| `milestone_reached` | Celebration, next-goal framing | Social proof + Curiosity |
| `regulation_change` | Compliance deadline, action steps | Urgency + Specificity |
| `winback_eligible` | Value-lost framing, re-engagement offer | Loss aversion |

### 4.5 Reply Classifier

Classifies incoming merchant messages before composing reply:

| Classification | Detection | Response |
|---|---|---|
| **Auto-reply** | Canned phrases ("Thank you for contacting"), repeated verbatim | 1st: acknowledge + re-prompt. 2nd: wait 24h. 3rd: end. |
| **Hard no** | "stop", "not interested", explicit opt-out | End gracefully |
| **Intent transition** | "let's do it", "yes go ahead", "what's next" | Switch from qualifying to action mode |
| **Off-topic** | Unrelated question (GST, etc.) | Politely decline, redirect to trigger |
| **Engaged** | Substantive reply on-topic | Continue conversation |
| **Hostile** | Abuse, anger | One-line apology + end |

### 4.6 Suppression Manager

```python
class SuppressionManager:
    _fired: set[str]         # suppression_keys already used
    _sent_bodies: dict[str, set[str]]  # conversation_id -> set of sent bodies

    def is_suppressed(key: str) -> bool
    def mark_fired(key: str) -> None
    def is_repeated(conversation_id: str, body: str) -> bool
    def record_sent(conversation_id: str, body: str) -> None
```

---

## 5. Request Flow Diagrams

### 5.1 Context Push Flow (`POST /v1/context`)

```
Judge -> /v1/context {scope, context_id, version, payload}
  |
  +-- Validate scope in {category, merchant, customer, trigger}
  +-- Check version > current version for (scope, context_id)
  |   +-- Yes -> Store atomically, return 200 {accepted: true}
  |   +-- No  -> Return 409 {accepted: false, reason: stale_version}
  +-- Invalid -> Return 400
```

### 5.2 Tick Flow (`POST /v1/tick`)

```
Judge -> /v1/tick {now, available_triggers}
  |
  +-- For each trigger_id in available_triggers:
  |   +-- Load trigger from ContextStore
  |   +-- Check not expired (expires_at > now)
  |   +-- Check not suppressed (suppression_key)
  |   +-- Load merchant context via trigger.merchant_id
  |   +-- Load category context via merchant.category_slug
  |   +-- If trigger.customer_id: load customer context
  |   +-- Rank by urgency (higher first)
  |   +-- Compose message via CompositionEngine
  |
  +-- Cap at 20 actions per tick
  +-- Return {actions: [...]}
```

### 5.3 Reply Flow (`POST /v1/reply`)

```
Judge -> /v1/reply {conversation_id, merchant_id, from_role, message, turn_number}
  |
  +-- Load ConversationState
  +-- Add incoming turn to history
  +-- Classify message (auto-reply? intent? hostile? engaged?)
  |
  +-- Auto-reply detected:
  |   +-- count=1: action send (acknowledge auto-reply)
  |   +-- count=2: action wait 86400s
  |   +-- count>=3: action end
  |
  +-- Hard no / hostile -> action: end
  |
  +-- Engaged / intent transition:
  |   +-- Load category + merchant + customer contexts
  |   +-- Compose reply via CompositionEngine
  |   +-- Return {action: send, body, cta, rationale}
  |
  +-- Return response within 30s budget
```

---

## 6. Scoring Dimensions & How Architecture Addresses Them

| Dimension (0-10) | What Judge Looks For | Architectural Answer |
|---|---|---|
| **Specificity** | Concrete numbers, dates, citations | Prompt injects real data from contexts: trial_n, source, page, perf numbers |
| **Category Fit** | Voice/vocabulary match | CategoryContext.voice drives prompt constraints (tone, taboos, vocab) |
| **Merchant Fit** | Personalized to this merchant's state | MerchantContext provides name, perf, offers, signals, history |
| **Trigger Relevance** | Clear "why now" | TriggerContext.kind drives prompt variant; payload provides event details |
| **Engagement Compulsion** | Would merchant reply? | 8 compulsion levers systematically applied per trigger kind |

### Eight Compulsion Levers

1. **Specificity** — numbers, dates, source citations from contexts
2. **Loss aversion** — "you're missing X", "before window closes"
3. **Social proof** — peer_stats comparisons ("3 dentists in your area did Y")
4. **Effort externalization** — "I've drafted X — just say go"
5. **Curiosity** — "want to see who?", "want the full list?"
6. **Reciprocity** — "I noticed Y, thought you'd want to know"
7. **Asking the merchant** — "what's your most-asked service this week?"
8. **Single binary CTA** — Reply YES/STOP, not multi-choice

---

## 7. Adaptive Context Handling

The judge injects new context mid-test:
- **New digest items** — Category version bumps (v1 to v2)
- **Updated perf snapshots** — Merchant version bumps
- **New triggers** — Fresh trigger pushes
- **New customers** — Customer context + recall_due trigger

Architecture response:
- ContextStore always serves latest version (atomic replace on upsert)
- Composer reads from store at composition time (never cached stale)
- New triggers automatically picked up in next `/v1/tick`

---

## 8. Anti-Pattern Guards

| Anti-Pattern | Detection | Prevention |
|---|---|---|
| Generic offers ("Flat 30% off") | Post-LLM validation | Prompt: "Use service+price from offer_catalog, never generic discounts" |
| Multiple CTAs | Output parser | Validate single CTA per message |
| Promotional tone for clinical categories | Voice check | Inject voice.vocab_taboo in prompt |
| Hallucinated data | Context-boundary check | Prompt: "Only cite data present in provided contexts" |
| Long preambles | Output validation | Prompt: "No 'I hope you're doing well' — start with the hook" |
| Repetition | SuppressionManager.is_repeated() | Check before sending |
| Wrong language | Language matcher | Honor merchant.identity.languages / customer.identity.language_pref |

---

## 9. Project Structure

```
vera-bot/
├── bot.py                      # FastAPI app - 5 endpoints
├── models/
│   ├── contexts.py             # Pydantic models for 4 context types
│   ├── requests.py             # Request schemas (CtxBody, TickBody, ReplyBody)
│   └── responses.py            # Response schemas (TickAction, ReplyAction)
├── store/
│   ├── context_store.py        # Versioned in-memory context store
│   └── suppression.py          # Suppression key tracking + anti-repetition
├── conversation/
│   ├── manager.py              # Conversation state tracking
│   └── classifier.py           # Reply classification
├── composer/
│   ├── engine.py               # Main composition engine
│   ├── prompts/
│   │   ├── base.py             # Base system prompt template
│   │   ├── research_digest.py  # Research/compliance trigger prompts
│   │   ├── recall_due.py       # Customer recall prompts
│   │   ├── perf_trigger.py     # Performance spike/dip prompts
│   │   ├── event_trigger.py    # Festival/IPL/weather prompts
│   │   ├── planning_intent.py  # Active planning prompts
│   │   ├── customer_winback.py # Lapsed customer prompts
│   │   └── reply_composer.py   # Multi-turn reply prompts
│   └── dispatch.py             # Route trigger.kind to prompt variant
├── config.py                   # LLM config, team metadata, constants
└── requirements.txt            # fastapi, uvicorn, pydantic, httpx/openai
```

---

## 10. Implementation Phases

### Phase A — Foundation (Day 1-2)
- [ ] Pydantic models for all 4 context types + request/response schemas
- [ ] ContextStore with versioned upsert + conflict detection
- [ ] FastAPI skeleton: 5 endpoints wired to store
- [ ] Pass judge_simulator warmup (255 contexts loaded)

### Phase B — Composer Engine (Day 3-4)
- [ ] Base prompt template with 4-context injection
- [ ] Prompt dispatch by trigger.kind (minimum 5 variants)
- [ ] LLM integration (Claude/GPT, temperature=0)
- [ ] Output validation: CTA shape, language match, no fabrication
- [ ] Tick handler: select triggers, compose, return actions

### Phase C — Multi-Turn & Reply Handling (Day 5-6)
- [ ] ConversationManager with turn tracking
- [ ] Reply classifier (auto-reply, intent transition, hostile, engaged)
- [ ] Reply composer with conversation history in prompt
- [ ] Auto-reply escalation ladder (send → wait → end)
- [ ] Graceful exit on hard-no / hostile

### Phase D — Optimization & Polish (Day 7)
- [ ] Anti-repetition check per conversation
- [ ] Suppression manager for trigger dedup
- [ ] Adaptive context verification
- [ ] Rationale quality alignment
- [ ] Load test: 10 req/s within 30s timeout budget
- [ ] Customer-facing: send_as=merchant_on_behalf, language match

---

## 11. Key Design Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Storage | In-memory dict | No persistence needed; test is single session |
| LLM Resilience | 2x Groq (Alternating/Round-Robin) + 1x Gemini Fallback | Maximize rate limits via alternating keys; stay <2s with Groq speed |
| Prompt strategy | Dispatch by trigger.kind | Different triggers need different framing |
| Context freshness | Read from store at compose-time | Ensures adaptive injection is used |
| Conversation tracking | Per conversation_id dict | Simple, sufficient for 60-min test window |
| Anti-patterns | Post-LLM validation layer | Catches taboo words, multi-CTA, fabrication |

---

## 12. Risk Mitigation

| Risk | Impact | Mitigation |
|---|---|---|
| LLM timeout (>30s) | Tick/reply scored as timeout (-1) | Set LLM timeout to 20s; return empty actions on timeout |
| Hallucinated data | Capped at 5/dimension | Prompt: "Only use data from provided contexts" |
| Wrong voice/tone | Category fit penalty | Inject voice constraints in every prompt |
| Repetition | -2 per repeat | Track sent bodies per conversation |
| Malformed response | -2 per malformed | Pydantic validation on output; fallback to safe default |
| 3x healthz failure | Disqualification | Keep /healthz trivial (dict lookup only) |
| URL in body | -3 per URL | Post-LLM check: strip any URLs before sending |

---

## 13. Dataset Summary (What We Work With)

| Dataset | Seed Count | Expanded | Key Schema |
|---|---|---|---|
| Categories | 5 | 5 | slug, voice, offer_catalog, peer_stats, digest, seasonal_beats, trend_signals |
| Merchants | 10 | 50 | merchant_id, identity, subscription, performance, offers, signals, review_themes |
| Customers | 15 | 200 | customer_id, merchant_id, identity, relationship, state, preferences, consent |
| Triggers | 25 | 100 | id, scope, kind, source, merchant_id, payload, urgency, suppression_key |

### Trigger Kind Distribution (from seeds)

| Kind | Count | Scope |
|---|---|---|
| research_digest | 1 | merchant |
| regulation_change | 1 | merchant |
| recall_due | 1 | customer |
| perf_dip | 1 | merchant |
| renewal_due | 1 | merchant |
| festival_upcoming | 1 | merchant |
| wedding_package_followup | 1 | customer |
| curious_ask_due | 1 | merchant |
| winback_eligible | 1 | merchant |
| ipl_match_today | 1 | merchant |
| review_theme_emerged | 1 | merchant |
| milestone_reached | 1 | merchant |
| active_planning_intent | 2 | merchant |
| seasonal_perf_dip | 1 | merchant |
| customer_lapsed_hard | 1 | customer |
| trial_followup | 1 | customer |
| supply_alert | 1 | merchant |
| chronic_refill_due | 1 | customer |
| category_seasonal | 1 | merchant |
| gbp_unverified | 1 | merchant |
| cde_opportunity | 1 | merchant |
| competitor_opened | 1 | merchant |
| perf_spike | 1 | merchant |
| dormant_with_vera | 1 | merchant |
