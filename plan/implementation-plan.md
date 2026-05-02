# Vera — Phase-Wise Implementation Plan

**Based on**: [architecture.md](./architecture.md)
**Date**: 2026-04-30

---

## Phase A — Foundation (Day 1–2)

> **Goal**: Bot passes judge warmup — 5 endpoints live, 255 contexts ingested, healthz reports correct counts.

### [X] Task A.1 — Project Scaffold

**Files**: `requirements.txt`, `config.py`

```
pip dependencies: fastapi, uvicorn, pydantic, httpx, openai (or anthropic)
```

```python
# config.py
TEAM_NAME = "Vera-Rebuild"
TEAM_MEMBERS = ["<your-name>"]
PRIMARY_MODEL = "llama-3.3-70b-versatile" # Groq
FALLBACK_MODEL = "gemini-1.5-flash"       # Gemini
LLM_TIMEOUT = 20  # seconds, leaves 10s buffer for 30s budget
TEMPERATURE = 0   # deterministic per spec
BOT_VERSION = "1.0.0"
```

**Acceptance**: `uvicorn bot:app --port 8080` starts without errors.

---

### [X] Task A.2 — Pydantic Models

**File**: `models/contexts.py`

Define models matching the dataset JSON schemas:

| Model | Source Schema | Key Fields |
|---|---|---|
| `VoiceProfile` | `categories/*.json → voice` | tone, vocab_allowed, vocab_taboo |
| `OfferTemplate` | `categories/*.json → offer_catalog[]` | id, title, value, audience, type |
| `PeerStats` | `categories/*.json → peer_stats` | avg_rating, avg_ctr, avg_reviews |
| `DigestItem` | `categories/*.json → digest[]` | id, kind, title, source, summary |
| `Identity` | `merchants_seed.json → identity` | name, city, locality, languages, owner_first_name |
| `Subscription` | `merchants_seed.json → subscription` | status, plan, days_remaining |
| `Performance` | `merchants_seed.json → performance` | views, calls, ctr, delta_7d |
| `CustomerIdentity` | `customers_seed.json → identity` | name, language_pref, age_band |
| `Relationship` | `customers_seed.json → relationship` | first_visit, last_visit, visits_total, services |

**File**: `models/requests.py`

| Model | Endpoint | Fields |
|---|---|---|
| `ContextPushRequest` | POST /v1/context | scope, context_id, version, payload (dict), delivered_at |
| `TickRequest` | POST /v1/tick | now, available_triggers |
| `ReplyRequest` | POST /v1/reply | conversation_id, merchant_id, customer_id, from_role, message, received_at, turn_number |

**File**: `models/responses.py`

| Model | Endpoint | Fields |
|---|---|---|
| `ContextAccepted` | 200 context | accepted=True, ack_id, stored_at |
| `ContextRejected` | 409 context | accepted=False, reason, current_version |
| `TickAction` | 200 tick → actions[] | conversation_id, merchant_id, customer_id, send_as, trigger_id, template_name, template_params, body, cta, suppression_key, rationale |
| `TickResponse` | 200 tick | actions: list[TickAction] |
| `ReplyResponse` | 200 reply | action ("send"/"wait"/"end"), body?, cta?, wait_seconds?, rationale |

**Acceptance**: All models instantiate with sample data from seed JSONs without validation errors.

---

### [X] Task A.3 — Context Store

**File**: `store/context_store.py`

```python
class ContextEntry:
    version: int
    payload: dict
    stored_at: str

class ContextStore:
    _store: dict[tuple[str, str], ContextEntry]

    def upsert(self, scope, context_id, version, payload) -> tuple[bool, str|int]:
        """Returns (accepted, ack_id_or_current_version)"""
        key = (scope, context_id)
        existing = self._store.get(key)
        if existing and existing.version >= version:
            return (False, existing.version)
        self._store[key] = ContextEntry(version, payload, now_iso())
        return (True, f"ack_{context_id}_v{version}")

    def get(self, scope, context_id) -> ContextEntry | None
    def get_all_by_scope(self, scope) -> list[ContextEntry]
    def counts(self) -> dict[str, int]:
        """Returns {category: N, merchant: N, customer: N, trigger: N}"""
```

**Acceptance**: Unit test — upsert v1, upsert v1 again (rejected), upsert v2 (accepted), get returns v2.

---

### [X] Task A.4 — FastAPI Endpoints

**File**: `bot.py`

| Endpoint | Handler Logic |
|---|---|
| `GET /v1/healthz` | Return status + uptime + `context_store.counts()` |
| `GET /v1/metadata` | Return static team info from `config.py` |
| `POST /v1/context` | Validate scope → `context_store.upsert()` → 200 or 409 |
| `POST /v1/tick` | Return `{"actions": []}` (stub — composer wired in Phase B) |
| `POST /v1/reply` | Return `{"action": "send", "body": "Acknowledged", "cta": "none", "rationale": "stub"}` |

**Acceptance**: Run `python judge_simulator.py` — warmup phase passes (255 contexts loaded, healthz green).

---

### Task A.5 — Dataset Generation

**Action**: Run `python dataset/generate_dataset.py` to expand seeds into full dataset (50 merchants, 200 customers, 100 triggers).

**Acceptance**: Generated files exist and are valid JSON.

---

## Phase B — Composition Engine (Day 3–4)

> **Goal**: Bot composes high-quality proactive messages. Tick handler returns scored actions for available triggers.

### Task B.1 — LLM Client (Resilient Rotation)

**File**: `composer/llm_client.py`

```python
async def call_llm(system_prompt: str, user_prompt: str) -> str:
    """
    1. Select Groq Key (Alternating/Round-Robin from 2 keys)
    2. If 429/Error: Try the OTHER Groq Key
    3. If both fail: Try Gemini Fallback (gemini-1.5-flash)
    4. Return raw text or empty string on total failure.
    """
    # Use httpx with 20s timeout
    # temperature=0 for determinism
```

**Acceptance**: Single call returns valid text within 20s.

---

### [X] Task B.2 — Base Prompt Template

**File**: `composer/prompts/base.py`

The base system prompt injected into every LLM call:

```
You are Vera, a merchant AI assistant for magicpin.

RULES:
- Only use data from the provided contexts. Never invent facts.
- Match the category voice: {voice.tone}, allowed vocab: {voice.vocab_allowed}
- Never use taboo words: {voice.vocab_taboo}
- Use owner's first name: {identity.owner_first_name}
- Honor language preference: {identity.languages}
- No "I hope you're doing well" preambles — start with the hook
- Single CTA per message, placed at the end
- No URLs in body
- Hindi-English code-mix is encouraged when merchant languages include "hi"

OUTPUT FORMAT (JSON):
{
  "body": "...",
  "cta": "open_ended | binary_yes_no | binary_confirm_cancel | none",
  "template_name": "vera_{trigger_kind}_v1",
  "template_params": ["param1", "param2"],
  "suppression_key": "...",
  "rationale": "1-2 sentences explaining why this message, what lever it uses"
}
```

**Acceptance**: Template renders correctly with sample category + merchant data.

---

### [X] Task B.3 — Trigger-Kind Prompt Variants

**Files**: `composer/prompts/` (one file per family), `composer/dispatch.py`

| File | Handles Trigger Kinds | Prompt Focus |
|---|---|---|
| `research_digest.py` | research_digest, cde_opportunity, regulation_change | Source citation, JIDA/DCI reference, "Worth a look" framing |
| `perf_trigger.py` | perf_dip, perf_spike, seasonal_perf_dip, milestone_reached | Data anchoring with peer_stats, "your views are X vs peer Y" |
| `event_trigger.py` | festival_upcoming, ipl_match_today, category_seasonal, competitor_opened | Counter-intuitive insight, existing offer leverage |
| `recall_due.py` | recall_due, chronic_refill_due, trial_followup | Slot offering, language match, send_as=merchant_on_behalf |
| `customer_winback.py` | customer_lapsed_hard, wedding_package_followup | No-shame framing, free trial offer |
| `planning_intent.py` | active_planning_intent, curious_ask_due | Complete drafted artifact OR low-stakes question |
| `operational.py` | renewal_due, gbp_unverified, winback_eligible, dormant_with_vera, review_theme_emerged | Action-oriented nudge with specific data |

```python
# composer/dispatch.py
PROMPT_MAP = {
    "research_digest": research_digest_prompt,
    "regulation_change": research_digest_prompt,
    "cde_opportunity": research_digest_prompt,
    "perf_dip": perf_trigger_prompt,
    "perf_spike": perf_trigger_prompt,
    # ... etc
}

def get_prompt_variant(trigger_kind: str) -> PromptBuilder:
    return PROMPT_MAP.get(trigger_kind, base_prompt)
```

**Acceptance**: Each variant produces valid JSON output for its trigger kind using sample data.

---

### [X] Task B.4 — Composition Engine

**File**: `composer/engine.py`

```python
class CompositionEngine:
    async def compose_proactive(self, category, merchant, trigger, customer=None):
        prompt_builder = dispatch.get_prompt_variant(trigger["kind"])
        system_prompt = prompt_builder.build(category, merchant, trigger, customer)
        raw = await llm_client.call_llm(system_prompt, user_prompt="Compose now.")
        parsed = self._parse_and_validate(raw, trigger, merchant)
        return parsed  # TickAction

    def _parse_and_validate(self, raw, trigger, merchant):
        # Parse JSON from LLM output
        # Validate: no URLs, no taboo words, single CTA, no fabrication
        # Set send_as based on trigger.scope (customer → merchant_on_behalf)
        # Set suppression_key from trigger
```

**Acceptance**: compose_proactive returns valid TickAction for each of the 25 seed triggers.

---

### [X] Task B.5 — Wire Tick Endpoint

**File**: `bot.py` (update POST /v1/tick)

```python
@app.post("/v1/tick")
async def tick(body: TickRequest):
    actions = []
    for trg_id in body.available_triggers:
        trg_entry = context_store.get("trigger", trg_id)
        if not trg_entry: continue
        trg = trg_entry.payload

        # Skip expired/suppressed
        if suppression.is_suppressed(trg.get("suppression_key", "")): continue

        merchant = context_store.get("merchant", trg["merchant_id"])
        if not merchant: continue
        category = context_store.get("category", merchant.payload["category_slug"])
        if not category: continue

        customer = None
        if trg.get("customer_id"):
            customer = context_store.get("customer", trg["customer_id"])

        # Sort by urgency (done after collecting)
        action = await engine.compose_proactive(
            category.payload, merchant.payload, trg, 
            customer.payload if customer else None
        )
        actions.append(action)
        suppression.mark_fired(trg.get("suppression_key", ""))

    # Sort by urgency descending, cap at 20
    actions.sort(key=lambda a: a.get("urgency", 0), reverse=True)
    return {"actions": actions[:20]}
```

**Acceptance**: `judge_simulator.py` Phase 2 — bot sends messages for available triggers with non-zero quality scores.

---

## Phase C — Multi-Turn & Reply Handling (Day 5–6)

> **Goal**: Bot handles merchant replies intelligently — detects auto-replies, intent transitions, hostility. Conversations flow naturally for 3-5 turns.

### [X] Task C.1 — Conversation Manager

**File**: `conversation/manager.py`

```python
class ConversationState:
    conversation_id: str
    merchant_id: str
    customer_id: str | None
    trigger_id: str
    turns: list[dict]          # [{role, message, ts}]
    auto_reply_count: int
    is_ended: bool
    end_reason: str | None
    sent_bodies: set[str]      # for anti-repetition

class ConversationManager:
    _conversations: dict[str, ConversationState]

    def get_or_create(self, conversation_id, merchant_id, customer_id, trigger_id)
    def add_turn(self, conversation_id, role, message)
    def increment_auto_reply(self, conversation_id) -> int  # returns new count
    def mark_ended(self, conversation_id, reason)
    def is_body_repeated(self, conversation_id, body) -> bool
    def record_sent_body(self, conversation_id, body)
```

**Acceptance**: Unit tests for state transitions and anti-repetition tracking.

---

### [X] Task C.2 — Reply Classifier

**File**: `conversation/classifier.py`

```python
class ReplyClassification(Enum):
    AUTO_REPLY = "auto_reply"
    HARD_NO = "hard_no"
    HOSTILE = "hostile"
    INTENT_TRANSITION = "intent_transition"
    OFF_TOPIC = "off_topic"
    ENGAGED = "engaged"

def classify(message: str, conversation_state: ConversationState) -> ReplyClassification:
    msg_lower = message.lower().strip()

    # Auto-reply detection
    auto_reply_phrases = [
        "thank you for contacting", "our team will respond",
        "automated", "auto-reply", "we will get back"
    ]
    if any(phrase in msg_lower for phrase in auto_reply_phrases):
        return AUTO_REPLY
    # Same message repeated from merchant → auto-reply
    if conversation_state.turns and conversation_state.turns[-1].get("role") == "merchant":
        if conversation_state.turns[-1]["message"].strip() == message.strip():
            return AUTO_REPLY

    # Hard no
    no_phrases = ["stop", "not interested", "unsubscribe", "stop messaging", "don't contact"]
    if any(phrase in msg_lower for phrase in no_phrases):
        return HARD_NO

    # Hostile
    hostile_signals = ["useless", "bothering", "waste of time", "spam"]
    if any(s in msg_lower for s in hostile_signals):
        return HOSTILE

    # Intent transition
    intent_phrases = ["let's do it", "yes go ahead", "ok do it", "what's next",
                       "sounds good let's proceed", "yes please", "go ahead"]
    if any(phrase in msg_lower for phrase in intent_phrases):
        return INTENT_TRANSITION

    # Off-topic (simple heuristic — can enhance with LLM)
    off_topic_signals = ["gst", "tax", "invoice", "loan", "insurance"]
    if any(s in msg_lower for s in off_topic_signals):
        return OFF_TOPIC

    return ENGAGED
```

**Acceptance**: Classify correctly for all examples in `api-call-examples.md` (auto-reply, hard no, curveball, engaged).

---

### [X] Task C.3 — Reply Composer

**File**: `composer/prompts/reply_composer.py`

Prompt includes:
- Full conversation history (all turns)
- Original trigger context
- Classification result
- Specific instructions per classification:

| Classification | Prompt Instruction |
|---|---|
| ENGAGED | Continue the thread. Honor what merchant asked. Advance to next step. |
| INTENT_TRANSITION | Switch to ACTION mode. No more questions. Draft/execute the thing. |
| AUTO_REPLY | (Handled by escalation ladder, not LLM) |
| OFF_TOPIC | Politely decline. Redirect to original trigger topic in same message. |
| HARD_NO / HOSTILE | (Handled directly — return end action, no LLM needed) |

---

### [X] Task C.4 — Wire Reply Endpoint

**File**: `bot.py` (update POST /v1/reply)

```python
@app.post("/v1/reply")
async def reply(body: ReplyRequest):
    state = conversation_manager.get_or_create(
        body.conversation_id, body.merchant_id, body.customer_id, trigger_id=None
    )
    conversation_manager.add_turn(body.conversation_id, body.from_role, body.message)

    classification = classifier.classify(body.message, state)

    # Auto-reply escalation ladder
    if classification == AUTO_REPLY:
        count = conversation_manager.increment_auto_reply(body.conversation_id)
        if count == 1:
            return {"action": "send",
                    "body": "Looks like an auto-reply — when the owner sees this, just reply 'Yes' to continue.",
                    "cta": "binary_yes_no",
                    "rationale": "Detected auto-reply; one prompt for owner."}
        elif count == 2:
            return {"action": "wait", "wait_seconds": 86400,
                    "rationale": "Same auto-reply twice. Wait 24h."}
        else:
            conversation_manager.mark_ended(body.conversation_id, "auto_reply_3x")
            return {"action": "end",
                    "rationale": "Auto-reply 3x. No engagement signal. Closing."}

    # Hard no / hostile
    if classification in (HARD_NO, HOSTILE):
        conversation_manager.mark_ended(body.conversation_id, classification.value)
        return {"action": "end",
                "rationale": f"Merchant {classification.value}. Gracefully exiting."}

    # Engaged / intent transition / off-topic → compose via LLM
    merchant = context_store.get("merchant", body.merchant_id)
    category = context_store.get("category", merchant.payload["category_slug"]) if merchant else None
    customer = context_store.get("customer", body.customer_id) if body.customer_id else None

    result = await engine.compose_reply(
        state, body.message, classification,
        category.payload if category else {},
        merchant.payload if merchant else {},
        customer.payload if customer else None
    )

    # Anti-repetition check
    if conversation_manager.is_body_repeated(body.conversation_id, result["body"]):
        result["body"] += " (Let me know if you'd like a different angle.)"

    conversation_manager.record_sent_body(body.conversation_id, result["body"])
    return result
```

**Acceptance**: `judge_simulator.py` Phase 4 replay scenarios pass — auto-reply detected, intent transition honored, hostile exit clean.

---

## Phase D — Optimization & Polish (Day 7)

> **Goal**: Maximize scoring across all 5 dimensions. Handle edge cases. Pass full judge run.

### Task D.1 — Suppression Manager

**File**: `store/suppression.py`

- Track fired suppression_keys globally
- Track ended conversation_ids (don't re-engage)
- Track merchant opt-outs (suppress all future triggers for that merchant)

---

### Task D.2 — Output Validation Layer

**File**: `composer/validator.py`

Post-LLM checks before returning any action:

| Check | Action on Failure |
|---|---|
| Body contains URL | Strip URL, re-compose if body becomes empty |
| Body contains taboo word (from voice.vocab_taboo) | Re-prompt LLM once |
| Multiple CTAs detected | Keep only the last CTA sentence |
| Body is empty | Return `{"actions": []}` for tick, or `{"action": "wait"}` for reply |
| JSON parse failure | Fallback to safe stub response |
| Body exceeds 500 chars | Truncate at last sentence before limit |

---

### Task D.3 — Language Matching

Enhance composer to:
- Check `merchant.identity.languages` — if includes "hi", encourage hi-en code-mix
- Check `customer.identity.language_pref` — match exactly ("hi", "te-en mix", etc.)
- Add language instruction to every prompt variant

---

### Task D.4 — Adaptive Context Verification

Test that mid-test context updates are used:
1. Push category v1 → compose message using digest item A
2. Push category v2 (new digest item B added) → compose message → should reference item B
3. Push merchant v2 (perf numbers changed) → compose → should use new numbers

---

### Task D.5 — Rationale Quality

Ensure every rationale:
- Names the trigger kind ("External research digest...")
- Names the compulsion lever used ("Curiosity + reciprocity")
- References a specific merchant attribute ("high-risk-adult cohort from customer_aggregate")
- Is 1-2 sentences max

---

### Task D.6 — Load & Timeout Testing

```bash
# Simulate 10 concurrent tick requests
for i in {1..10}; do
  curl -X POST -H "Content-Type: application/json" \
    -d '{"now":"2026-04-26T10:35:00Z","available_triggers":["trg_001"]}' \
    http://localhost:8080/v1/tick &
done
```

Verify all respond within 30s. If LLM is slow, return empty actions as fallback.

---

### Task D.7 — End-to-End Judge Simulator Run

```bash
export BOT_URL=http://localhost:8080
python judge_simulator.py
```

Review per-message scores. Iterate on prompt variants for any dimension scoring below 7.

---

## Milestone Summary

| Phase | Duration | Exit Criteria |
|---|---|---|
| **A — Foundation** | Day 1–2 | Warmup passes. 5 endpoints live. 255 contexts stored. healthz green. |
| **B — Composer** | Day 3–4 | Tick returns composed messages. Non-zero scores on all 5 dimensions. |
| **C — Multi-Turn** | Day 5–6 | Reply handles auto-reply/intent/hostile. 3-5 turn conversations flow. |
| **D — Optimization** | Day 7 | All dimensions ≥7/10. No operational penalties. Full simulator pass. |

---

## File Creation Order

```
Day 1:
  1. requirements.txt
  2. config.py
  3. models/contexts.py
  4. models/requests.py
  5. models/responses.py
  6. store/context_store.py
  7. bot.py (5 endpoints, tick/reply stubbed)

Day 2:
  8. Run generate_dataset.py
  9. Test with judge_simulator.py warmup

Day 3:
  10. composer/llm_client.py
  11. composer/prompts/base.py
  12. composer/dispatch.py

Day 4:
  13. composer/prompts/research_digest.py
  14. composer/prompts/perf_trigger.py
  15. composer/prompts/event_trigger.py
  16. composer/prompts/recall_due.py
  17. composer/prompts/customer_winback.py
  18. composer/prompts/planning_intent.py
  19. composer/prompts/operational.py
  20. composer/engine.py
  21. Update bot.py tick handler

Day 5:
  22. conversation/manager.py
  23. conversation/classifier.py

Day 6:
  24. composer/prompts/reply_composer.py
  25. Update bot.py reply handler
  26. store/suppression.py

Day 7:
  27. composer/validator.py
  28. End-to-end testing + prompt iteration
```
