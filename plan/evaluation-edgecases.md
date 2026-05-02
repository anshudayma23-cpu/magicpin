# Vera — Evaluation & Edge Cases per Phase

**Based on**: [implementation-plan.md](./implementation-plan.md)
**Date**: 2026-04-30

This document outlines the evaluation criteria, expected outcomes, and potential edge cases to test for each implementation phase of the Vera Merchant AI.

---

## Phase A — Foundation

> **Goal**: Establish the base FastAPI application, Pydantic models, and versioned context store to pass the Judge Simulator Warmup.

### Evaluation Criteria
1. **Startup Check**: The server (`uvicorn bot:app`) starts smoothly and exposes the 5 required endpoints on the designated port.
2. **Schema Validation**: Seed data (merchants, categories, customers, triggers) loads successfully into Pydantic models without raising `ValidationError`.
3. **Store Idempotency**: 
   - Pushing `version: 1` succeeds (HTTP 200).
   - Re-pushing `version: 1` is rejected gracefully with `stale_version` (HTTP 409).
   - Pushing `version: 2` replaces the payload atomically (HTTP 200).
4. **Warmup Benchmark**: Running `judge_simulator.py` correctly reports all 255 contexts loaded via `/v1/healthz`.

### Edge Cases to Handle
- **Missing Payload Fields**: A context push is missing expected fields (e.g., a merchant with no `performance` object). Pydantic models must use `Optional` types or defaults to avoid crashing.
- **Malformed JSON**: The judge sends an invalid JSON string. FastAPI handles this natively with a 422, but we should ensure we return a 400 format per the challenge brief if required.
- **Invalid Scope**: `/v1/context` receives a scope outside of `[category, merchant, customer, trigger]`. Must return `{"accepted": False, "reason": "invalid_scope"}`.
- **High Concurrency**: The judge pushes 255 contexts very quickly. The in-memory dictionary `_store` must not encounter race conditions (standard Python async/await handling should suffice since there's no cross-thread blocking I/O).

---

## Phase B — Composition Engine

> **Goal**: Integrate the LLM, dispatch logic, and prompt variants to successfully compose high-quality proactive messages in the `/v1/tick` handler.

### Evaluation Criteria
1. **LLM Integration**: The LLM client successfully connects, handles API keys, and returns a raw string.
2. **Prompt Dispatch**: The dispatcher correctly identifies the trigger kind (e.g., `research_digest`) and applies the appropriate prompt variant.
3. **JSON Output**: The LLM consistently returns a strictly valid JSON block conforming to the expected keys (`body`, `cta`, `template_name`, etc.).
4. **Action Ranking**: If 30 triggers are available, the tick handler composes messages and returns exactly 20 actions ranked by `urgency`.

### Edge Cases to Handle
- **LLM Timeout/Rate Limit**: The LLM provider takes > 20s or throws a 429 Too Many Requests. 
  *Mitigation*: The wrapper must catch exceptions/timeouts and return an empty `actions: []` for that tick rather than failing the entire request and violating the 30s budget.
- **Invalid LLM JSON**: The LLM output includes unescaped quotes, trailing commas, or markdown blocks (e.g., ` ```json `).
  *Mitigation*: The `_parse_and_validate` method must strip markdown backticks and attempt to use a forgiving JSON parser or regex before failing.
- **Missing Trigger Dependencies**: A trigger specifies a `customer_id`, but the context store has no record of that customer.
  *Mitigation*: Skip the trigger and drop it from the current tick queue.
- **LLM Ignores Instructions**: The LLM outputs multiple CTAs or ignores the voice taboos.
  *Mitigation*: Add post-LLM validation to enforce single CTA and strip taboo words.

---

## Phase C — Multi-Turn & Reply Handling

> **Goal**: Accurately classify incoming merchant messages and manage stateful 3-5 turn conversations.

### Evaluation Criteria
1. **Classifier Accuracy**: The classifier correctly maps strings like "Stop bothering me" to `HOSTILE`, "let's do it" to `INTENT_TRANSITION`, and "we will get back to you" to `AUTO_REPLY`.
2. **Escalation Ladder**: An `AUTO_REPLY` results in an action of `send` on the 1st occurrence, `wait` on the 2nd, and `end` on the 3rd.
3. **Turn Logging**: The `ConversationManager` successfully tracks all previous turns, including their timestamps and roles.
4. **Context Injection**: Multi-turn replies successfully append the conversation history into the LLM system prompt so Vera "remembers" what was just said.

### Edge Cases to Handle
- **Mutated Auto-Replies**: An auto-reply contains dynamic text like `"Thank you... Received at 10:42 AM"`.
  *Mitigation*: The `classify` function should use substring matching or regex (`"thank you for contacting"`) rather than strict equality, or fall back to checking if the merchant sends the exact same string twice in a row.
- **Context Window Exhaustion**: A conversation runs for 15 turns and the text history exceeds the LLM context window.
  *Mitigation*: The `ConversationManager` should truncate or summarize turns older than the last 5 when injecting into the prompt.
- **Unrecognized Conversation ID**: `/v1/reply` receives a `conversation_id` that the bot didn't start.
  *Mitigation*: `get_or_create` handles this, but we must ensure we gracefully recover context from the provided `merchant_id`.
- **Ambiguous Replies**: The merchant replies "ok" or an emoji.
  *Mitigation*: Classify as `ENGAGED` and let the LLM prompt handle the ambiguous continuation.

---

## Phase D — Optimization & Polish

> **Goal**: Ensure the bot meets all constraint rules to prevent score penalties, applies the 8 compulsion levers, and survives the full 60-minute load test.

### Evaluation Criteria
1. **Anti-Repetition**: The bot never sends the exact same body text twice within the same `conversation_id`.
2. **Dedup/Suppression**: Once a trigger is processed, its `suppression_key` is marked, and subsequent ticks with the same key are ignored.
3. **Adaptive Context Use**: If a Category context is bumped to version 2 with a new digest item mid-test, the next message composed uses the new digest item.
4. **Language Compliance**: Output text strictly reflects the code-mixed language preferences of the customer/merchant identity.

### Edge Cases to Handle
- **Over-zealous Validation Loop**: The validator detects a URL, strips it, detects a taboo word, and calls the LLM again, consuming 25 seconds.
  *Mitigation*: The validator should only retry the LLM *once*. If it fails again, fall back to a safe, hardcoded response.
- **Concurrent Context Mutability**: The judge pushes a new Context version exactly while the `CompositionEngine` is reading the old version to craft a prompt.
  *Mitigation*: Since FastAPI handles requests in an event loop, the references pulled at the start of the `/v1/tick` execution should remain consistent for that turn.
- **Excessive Tick Volume**: The judge sends 50 `available_triggers` in a single tick. Composing 50 messages takes 100 seconds (failing the 30s budget).
  *Mitigation*: The tick handler MUST slice the available triggers down to a manageable batch (e.g., top 5 by urgency) *before* invoking the LLM, leaving the rest for the next tick.
- **Rationale Mismatch**: The LLM outputs a rationale that doesn't match the body (e.g., claims it used specific numbers but didn't).
  *Mitigation*: In the few-shot prompt examples, strongly enforce that the rationale must refer to exact data present in the output.
