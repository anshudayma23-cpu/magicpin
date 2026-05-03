import time
import json
import logging
import asyncio
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# --- Components ---
from models import ContextPushRequest, TickRequest, TickResponse, ReplyRequest, ReplyResponse, TickAction
from context_store import context_store
from config import settings
from composition_engine import CompositionEngine
from conversation_manager import conversation_manager
from reply_classifier import ReplyClassifier
from reply_composer import ReplyComposer
from suppression import suppression_manager

logger = logging.getLogger("vera.bot")

app = FastAPI(title="Vera Merchant AI - Production")
engine = CompositionEngine()
classifier = ReplyClassifier()
composer = ReplyComposer()

@app.get("/")
async def root():
    return {
        "status": "online",
        "bot": "Vera Merchant AI",
        "version": settings.BOT_VERSION,
        "endpoints": ["/v1/healthz", "/v1/metadata", "/v1/context", "/v1/tick", "/v1/reply"]
    }

@app.get("/v1/healthz")
async def healthz():
    return {"status": "ok", "contexts_loaded": context_store.counts()}

@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": settings.TEAM_NAME,
        "model": f"{settings.PRIMARY_MODEL} (Groq)",
        "version": settings.BOT_VERSION
    }

@app.post("/v1/context")
async def context_push(body: ContextPushRequest):
    accepted, detail = context_store.upsert(body.scope, body.context_id, body.version, body.payload)
    if not accepted:
        return JSONResponse(status_code=409, content={"accepted": False, "reason": "stale_version", "current_version": detail})
    return {"accepted": True, "ack_id": detail}

@app.post("/v1/reset")
async def reset():
    """Resets all in-memory stores (suppression and context)."""
    suppression_manager.clear()
    context_store.clear()
    conversation_manager.clear_all()
    logger.info("Bot state fully reset via /v1/reset")
    return {"status": "ok", "message": "All stores cleared."}


@app.post("/v1/tick")
async def tick(body: TickRequest) -> TickResponse:
    actions = []
    # Phase 2: Signal Sifting Logic - Prioritize by financial impact
    # Phase J: Complete
    # Order: perf_dip (1), recall_due (2), event_trigger (3), research_digest (4)
    priority_map = {"perf_dip": 1, "recall_due": 2, "event_trigger": 3, "research_digest": 4}
    
    def get_priority(tid):
        t = context_store.get("trigger", tid)
        kind = t.payload.get("kind", "other") if t else "other"
        return priority_map.get(kind, 10)
    
    sorted_trigger_ids = sorted(body.available_triggers, key=get_priority)
    target_triggers = sorted_trigger_ids[:3]
    
    tasks = []
    target_trigger_payloads = []  # Track for indexing
    for trg_id in target_triggers:
        trg_entry = context_store.get("trigger", trg_id)
        if not trg_entry:
            print(f"[DEBUG] trigger {trg_id} NOT FOUND in context store")
            continue
        trg = trg_entry.payload

        # 2. Suppression Check
        suppkey = trg.get("suppression_key")
        if suppression_manager.is_suppressed(suppkey):
            print(f"[DEBUG] trigger {trg_id} SUPPRESSED (key={suppkey})")
            continue

        merch_id = trg.get("merchant_id")
        if suppression_manager.is_merchant_opted_out(merch_id):
            print(f"[DEBUG] merchant {merch_id} OPTED OUT")
            continue

        merchant = context_store.get("merchant", merch_id)
        if not merchant:
            print(f"[DEBUG] merchant {merch_id} NOT FOUND in context store")
            continue

        cat_slug = merchant.payload.get("category_slug")
        category = context_store.get("category", cat_slug)
        if not category:
            print(f"[DEBUG] category {cat_slug} NOT FOUND in context store")
            continue

        customer = None
        if trg.get("customer_id"):
            cust_entry = context_store.get("customer", trg["customer_id"])
            if cust_entry: customer = cust_entry.payload

        # 3. Queue Composition Task
        tasks.append(engine.compose_proactive(category.payload, merchant.payload, trg, customer))
        target_trigger_payloads.append(trg_id)



    # 4. Sequential Composition (to avoid TPM rate limits)
    results = []
    # Limit to 3 triggers per tick to ensure we stay under the 150s timeout
    max_triggers = 3
    for i, t in enumerate(tasks[:max_triggers]):
        try:
            res = await t
            results.append(res)
            # Only sleep if there's another task coming
            if i < len(tasks[:max_triggers]) - 1:
                await asyncio.sleep(4.1) 

        except Exception as e:
            logger.error(f"Composition exception: {type(e).__name__}: {e}")
            results.append(e)


    
    for i, res in enumerate(results):
        if isinstance(res, dict) and res:
            try:
                # Phase 4.1: Data Enrichment
                # The LLM only returns body/cta/rationale. We must add the metadata.
                trg_id = target_triggers[i]
                trg_entry = context_store.get("trigger", trg_id)
                trg = trg_entry.payload if trg_entry else {}
                
                enriched_res = {
                    "conversation_id": f"conv_{trg.get('merchant_id')}_{trg_id}",
                    "merchant_id": trg.get("merchant_id"),
                    "customer_id": trg.get("customer_id"),
                    "trigger_id": trg_id,
                    "template_name": "proactive_standard",
                    "send_as": "vera",
                    "suppression_key": trg.get("suppression_key", f"key_{trg_id}"),
                    **res # Body, cta, rationale from LLM
                }
                
                actions.append(TickAction(**enriched_res))
                print(f"\n[BOT] SENDING MESSAGE: {enriched_res['body']}\n")
                
                # Mark as fired
                suppression_manager.mark_fired(enriched_res.get("suppression_key"))
                # Record in history
                conversation_manager.add_message(enriched_res["conversation_id"], "vera", enriched_res["body"])
            except Exception as e:
                logger.error(f"TickAction validation failed for trigger {target_triggers[i]}: {str(e)}")
                print(f"Validation Error Detail: {str(e)}")

    return TickResponse(actions=actions)

@app.post("/v1/reply")
async def reply(body: ReplyRequest) -> ReplyResponse:
    conv_id = body.conversation_id
    message = body.message
    
    # 1. Record Turn
    conversation_manager.add_message(conv_id, body.from_role, message)
    
    # 2. Classify Intent
    classification = classifier.classify(message)
    intent = classification["intent"]
    
    # 3. Special Handlers (Auto-Reply & Hostility)
    if intent == "auto_reply":
        return ReplyResponse(action="end", rationale="Detected automated response. Closing thread.")
        
    if intent == "hostile":
        suppression_manager.opt_out_merchant(body.merchant_id)
        return ReplyResponse(action="end", body="I've noted that. I will stop messaging you.", rationale="Merchant opted out.")

    # 4. LLM Contextual Reply
    merch_entry = context_store.get("merchant", body.merchant_id)
    if not merch_entry: return ReplyResponse(action="wait", rationale="No merchant context.")
    cat_entry = context_store.get("category", merch_entry.payload.get("category_slug"))
    if not cat_entry: return ReplyResponse(action="wait", rationale="No category context.")

    history = conversation_manager.get_history(conv_id)
    
    # Enrich prompt with intent
    enriched_msg = f"[Intent: {intent}] {message}"
    result = await composer.compose_reply(cat_entry.payload, merch_entry.payload, history, enriched_msg)
    
    if not result:
        return ReplyResponse(action="wait", rationale="LLM failed to compose reply.")
        
    # 5. Record and Return
    conversation_manager.add_message(conv_id, "vera", result.get("body", ""))
    return ReplyResponse(
        action=result.get("action", "send"),
        body=result.get("body"),
        cta=result.get("cta"),
        wait_seconds=300 if result.get("action") == "wait" else None,
        rationale=result.get("rationale")
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
