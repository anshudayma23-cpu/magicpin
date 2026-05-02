import time
import asyncio
from typing import List
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

# --- Import Components ---
from models import ContextPushRequest, TickRequest, TickResponse, ReplyRequest, ReplyResponse, TickAction
from context_store import context_store
from config import settings
from composition_engine import CompositionEngine

app = FastAPI(title="Vera Merchant AI - Phase B")
engine = CompositionEngine()
fired_suppression_keys = set()

@app.get("/v1/healthz")
async def healthz():
    return {"status": "ok", "contexts_loaded": context_store.counts()}

@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": settings.TEAM_NAME,
        "model": f"{settings.PRIMARY_MODEL} (Groq) + {settings.FALLBACK_MODEL} (Gemini)",
        "version": settings.BOT_VERSION
    }

@app.post("/v1/context")
async def context_push(body: ContextPushRequest):
    accepted, detail = context_store.upsert(body.scope, body.context_id, body.version, body.payload)
    if not accepted:
        return JSONResponse(status_code=409, content={"accepted": False, "reason": "stale_version", "current_version": detail})
    return {"accepted": True, "ack_id": detail}

@app.post("/v1/tick")
async def tick(body: TickRequest) -> TickResponse:
    actions = []
    
    # Process triggers in parallel to save time, but carefully within the 30s budget
    tasks = []
    
    # We only process up to 30 triggers per tick to ensure we stay under the timeout
    target_triggers = body.available_triggers[:30]
    
    for trg_id in target_triggers:
        print(f"Processing trigger: {trg_id}")
        trg_entry = context_store.get("trigger", trg_id)
        if not trg_entry: 
            print(f"Trigger {trg_id} not found in store")
            continue
        trg = trg_entry.payload
        
        # 1. Suppression Check
        s_key = trg.get("suppression_key")
        if s_key and s_key in fired_suppression_keys:
            print(f"Trigger {trg_id} suppressed by key {s_key}")
            continue
            
        # 2. Load Contexts
        merchant_id = trg.get("merchant_id")
        merch_entry = context_store.get("merchant", merchant_id)
        if not merch_entry: 
            print(f"Merchant {merchant_id} not found for trigger {trg_id}")
            continue
        
        cat_slug = merch_entry.payload.get("category_slug")
        cat_entry = context_store.get("category", cat_slug)
        if not cat_entry: 
            print(f"Category {cat_slug} not found for merchant {merchant_id}")
            continue
        
        cust = None
        if trg.get("customer_id"):
            cust_entry = context_store.get("customer", trg["customer_id"])
            if cust_entry:
                cust = cust_entry.payload

        # 3. Queue Composition Task
        tasks.append(
            engine.compose_proactive(cat_entry.payload, merch_entry.payload, trg, cust)
        )

    # Run compositions concurrently
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            print(f"Composition task {i} failed with error: {str(res)}")
            import traceback
            traceback.print_exception(type(res), res, res.__traceback__)
        elif res and isinstance(res, dict):
            actions.append(TickAction(**res))
            # Mark as suppressed if successful
            if res.get("suppression_key"):
                fired_suppression_keys.add(res["suppression_key"])
        else:
            print(f"Composition task {i} returned no result or invalid type: {type(res)}")

    # 4. Rank and Cap
    # Sort by urgency (assumed to be in the action or trigger)
    # Note: Rationale should explain the urgency
    actions.sort(key=lambda x: 5, reverse=True) # Placeholder for ranking logic
    
    return TickResponse(actions=actions[:settings.MAX_ACTIONS_PER_TICK])

@app.post("/v1/reply")
async def reply(body: ReplyRequest) -> ReplyResponse:
    # Still stubbed - to be implemented in Phase C
    return ReplyResponse(action="wait", rationale="Phase B Stub")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
