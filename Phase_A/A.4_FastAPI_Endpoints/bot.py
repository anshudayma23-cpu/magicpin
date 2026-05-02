import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse

# --- Import from local sub-modules ---
from models import ContextPushRequest, TickRequest, ReplyRequest, TickResponse, ReplyResponse
from context_store import context_store
from config import settings

app = FastAPI(title="Vera Merchant AI")

START_TIME = time.time()

@app.get("/v1/healthz")
async def healthz():
    uptime = int(time.time() - START_TIME)
    return {
        "status": "ok",
        "uptime_seconds": uptime,
        "contexts_loaded": context_store.counts()
    }

@app.get("/v1/metadata")
async def metadata():
    return {
        "team_name": settings.TEAM_NAME,
        "team_members": settings.TEAM_MEMBERS,
        "model": f"{settings.PRIMARY_MODEL} (Groq) with {settings.FALLBACK_MODEL} (Gemini)",
        "approach": "4-context composer with trigger-kind dispatch and multi-key rotation",
        "contact_email": "team@vera.ai",
        "version": settings.BOT_VERSION,
        "submitted_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }

@app.post("/v1/context")
async def context_push(body: ContextPushRequest):
    accepted, detail = context_store.upsert(
        scope=body.scope,
        context_id=body.context_id,
        version=body.version,
        payload=body.payload
    )
    
    if not accepted:
        # Return 409 Conflict for stale versions
        return JSONResponse(
            status_code=409,
            content={
                "accepted": False,
                "reason": "stale_version",
                "current_version": detail
            }
        )
    
    return {
        "accepted": True,
        "ack_id": detail,
        "stored_at": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    }

@app.post("/v1/tick")
async def tick(body: TickRequest) -> TickResponse:
    # Stub: Logic to be implemented in Phase B (Composer)
    return TickResponse(actions=[])

@app.post("/v1/reply")
async def reply(body: ReplyRequest) -> ReplyResponse:
    # Stub: Logic to be implemented in Phase C (Multi-Turn)
    return ReplyResponse(
        action="send",
        body="Acknowledged. We are processing your request.",
        cta="none",
        rationale="Phase A.4 Stub Response"
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.HOST, port=settings.PORT)
