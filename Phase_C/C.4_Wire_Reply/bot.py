import time
from typing import Optional
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

app = FastAPI(title="Vera Merchant AI - Phase C")
engine = CompositionEngine()
classifier = ReplyClassifier()
composer = ReplyComposer()

@app.get("/v1/healthz")
async def healthz():
    return {"status": "ok", "contexts_loaded": context_store.counts()}

@app.post("/v1/context")
async def context_push(body: ContextPushRequest):
    accepted, detail = context_store.upsert(body.scope, body.context_id, body.version, body.payload)
    if not accepted:
        return JSONResponse(status_code=409, content={"accepted": False, "reason": "stale_version", "current_version": detail})
    return {"accepted": True, "ack_id": detail}

@app.post("/v1/tick")
async def tick(body: TickRequest) -> TickResponse:
    # (Same as Phase B, but now we also record Vera's outgoing message in history)
    # For brevity in this standalone subphase, logic is simplified
    return TickResponse(actions=[])

@app.post("/v1/reply")
async def reply(body: ReplyRequest) -> ReplyResponse:
    conv_id = body.conversation_id
    message = body.message
    
    # 1. Store the incoming message in history
    conversation_manager.add_message(conv_id, body.from_role, message)
    
    # 2. Classify (Heuristics)
    classification = classifier.classify(message)
    
    if classification["intent"] == "auto_reply":
        return ReplyResponse(action="wait", rationale="Detected auto-reply. No response needed.")
        
    if classification["intent"] == "hostile":
        return ReplyResponse(action="end", body="Understood. I will stop messaging you.", rationale="Merchant requested unsubscribe.")

    if classification["intent"] in ["binary_yes", "binary_no"]:
        # We could handle these via template or LLM. For reliability, we'll let LLM confirm.
        pass

    # 3. Load Contexts for LLM reasoning
    merch_entry = context_store.get("merchant", body.merchant_id)
    if not merch_entry:
        return ReplyResponse(action="wait", rationale="Merchant context missing.")
        
    cat_entry = context_store.get("category", merch_entry.payload.get("category_slug"))
    if not cat_entry:
         return ReplyResponse(action="wait", rationale="Category context missing.")

    # 4. Compose contextual reply (LLM)
    history = conversation_manager.get_history(conv_id)
    result = await composer.compose_reply(cat_entry.payload, merch_entry.payload, history, message)
    
    if not result:
        return ReplyResponse(action="wait", rationale="LLM failed to generate reply.")
        
    # 5. Store Vera's reply in history
    conversation_manager.add_message(conv_id, "vera", result.get("body", ""))
    
    return ReplyResponse(
        action=result.get("action", "send"),
        body=result.get("body"),
        cta=result.get("cta"),
        rationale=result.get("rationale", "LLM reasoning")
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8081)
