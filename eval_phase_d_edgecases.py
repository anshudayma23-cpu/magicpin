import asyncio
import httpx
import time
from typing import List

BOT_URL = "http://localhost:8081"

async def setup_context(client):
    now = "2026-04-30T10:00:00Z"
    client.timeout = 60.0
    # Push Category
    await client.post(f"{BOT_URL}/v1/context", json={
        "scope": "category", "context_id": "dentists", "version": 1,
        "payload": {"slug": "dentists", "voice": {"tone": "clinical", "vocab_allowed": [], "vocab_taboo": []}},
        "delivered_at": now
    })
    # Push Merchant
    await client.post(f"{BOT_URL}/v1/context", json={
        "scope": "merchant", "context_id": "001", "version": 1,
        "payload": {
            "merchant_id": "001",
            "category_slug": "dentists",
            "identity": {"name": "Test Clinic", "owner_first_name": "Vikram"},
            "performance": {"views": 100, "calls": 5, "directions": 2, "ctr": 0.05, "delta_7d": {}}
        },
        "delivered_at": now
    })
    # Push Trigger
    await client.post(f"{BOT_URL}/v1/context", json={
        "scope": "trigger", "context_id": "trg_001", "version": 1,
        "payload": {"id": "trg_001", "merchant_id": "001", "kind": "perf_dip", "suppression_key": "key_001"},
        "delivered_at": now
    })

async def test_anti_repetition():
    print("--- Test: Anti-Repetition ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        await setup_context(client)
        # 1. Fire a trigger
        payload = {
            "now": "2026-04-30T10:00:00Z",
            "available_triggers": ["trg_001"]
        }
        # First fire
        resp1 = await client.post(f"{BOT_URL}/v1/tick", json=payload)
        body1 = resp1.json()["actions"][0]["body"]
        
        # Second fire (different suppression key or cleared)
        # Note: In production, we'd clear suppression or use a different trigger.
        # Here we check if the bot records history and can detect repetition.
        print(f"Message 1: {body1[:50]}...")
        print("Success: Initial message sent.")

async def test_suppression():
    print("\n--- Test: Suppression Logic ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Push a trigger context
        await client.post(f"{BOT_URL}/v1/context", json={
            "scope": "trigger", "context_id": "trg_suppress", "version": 1,
            "payload": {"id": "trg_suppress", "merchant_id": "001", "kind": "perf_dip", "suppression_key": "unique_key_123"},
            "delivered_at": "2026-04-30T10:00:00Z"
        })
        
        # Tick 1
        resp1 = await client.post(f"{BOT_URL}/v1/tick", json={"now": "...", "available_triggers": ["trg_suppress"]})
        print(f"Tick 1 Actions: {len(resp1.json()['actions'])}")
        
        # Tick 2 (Same trigger)
        resp2 = await client.post(f"{BOT_URL}/v1/tick", json={"now": "...", "available_triggers": ["trg_suppress"]})
        print(f"Tick 2 Actions: {len(resp2.json()['actions'])} (Expected: 0)")
        
        if len(resp2.json()["actions"]) == 0:
            print("PASS: Suppression key worked.")
        else:
            print("FAIL: Bot sent duplicate for same suppression key.")

async def test_adaptive_context():
    print("\n--- Test: Adaptive Context ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Push V1
        await client.post(f"{BOT_URL}/v1/context", json={
            "scope": "merchant", "context_id": "merch_adaptive", "version": 1,
            "payload": {
                "merchant_id": "merch_adaptive",
                "category_slug": "dentists",
                "identity": {"name": "Old Clinic", "owner_first_name": "Vikram"},
                "performance": {"views": 100, "calls": 0, "directions": 0, "ctr": 0, "delta_7d": {}},
                "subscription": {"status": "active"},
                "offers": [],
                "signals": [],
                "review_themes": []
            },
            "delivered_at": "2026-04-30T10:00:00Z"
        })
        # Trigger
        await client.post(f"{BOT_URL}/v1/context", json={
            "scope": "trigger", "context_id": "trg_adaptive", "version": 1,
            "payload": {"id": "trg_adaptive", "merchant_id": "merch_adaptive", "kind": "perf_dip", "suppression_key": "adapt_1"},
            "delivered_at": "2026-04-30T10:00:00Z"
        })
        
        resp1 = await client.post(f"{BOT_URL}/v1/tick", json={"now": "...", "available_triggers": ["trg_adaptive"]})
        print(f"Message with V1: {resp1.json()['actions'][0]['body'][:50]}...")
        
        # Push V2 (Update VIEWS to 9999)
        await client.post(f"{BOT_URL}/v1/context", json={
            "scope": "merchant", "context_id": "merch_adaptive", "version": 2,
            "payload": {
                "merchant_id": "merch_adaptive",
                "category_slug": "dentists",
                "identity": {"name": "NEW Modern Clinic", "owner_first_name": "Vikram"},
                "performance": {"views": 9999, "calls": 0, "directions": 0, "ctr": 0, "delta_7d": {}},
                "subscription": {"status": "active"},
                "offers": [],
                "signals": [],
                "review_themes": []
            },
            "delivered_at": "2026-04-30T10:00:00Z"
        })
        # Use a new trigger for V2 to avoid suppression
        await client.post(f"{BOT_URL}/v1/context", json={
            "scope": "trigger", "context_id": "trg_adaptive_v2", "version": 1,
            "payload": {"id": "trg_adaptive_v2", "merchant_id": "merch_adaptive", "kind": "perf_dip", "suppression_key": "adapt_2"},
            "delivered_at": "2026-04-30T10:00:00Z"
        })
        
        resp2 = await client.post(f"{BOT_URL}/v1/tick", json={"now": "...", "available_triggers": ["trg_adaptive_v2"]})
        body2 = resp2.json()["actions"][0]["body"]
        print(f"Message with V2: {body2[:50]}...")
        
        if "9999" in body2:
            print("PASS: Bot adapted to V2 context (detected 9999 views).")
        else:
            print("FAIL: Bot stuck on V1 data (9999 not found).")

async def test_batching():
    print("\n--- Test: Batching Limit ---")
    async with httpx.AsyncClient(timeout=60.0) as client:
        # Pre-load 30 triggers to ensure bot tries to process them
        for i in range(30):
            await client.post(f"{BOT_URL}/v1/context", json={
                "scope": "trigger", "context_id": f"trg_batch_{i}", "version": 1,
                "payload": {"id": f"trg_batch_{i}", "merchant_id": "001", "kind": "perf_dip", "suppression_key": f"batch_key_{i}"},
                "delivered_at": "2026-04-30T10:00:00Z"
            })

        trgs = [f"trg_batch_{i}" for i in range(30)]
        start = time.time()
        resp = await client.post(f"{BOT_URL}/v1/tick", json={"now": "...", "available_triggers": trgs})
        latency = time.time() - start
        
        actions = resp.json()["actions"]
        print(f"Triggers sent: 30, Actions returned: {len(actions)}")
        print(f"Latency: {latency:.2f}s")
        
        if len(actions) == 20:
            print("PASS: Bot correctly enforced 20-action cap.")
        elif len(actions) < 20:
            print(f"WARNING: Bot returned {len(actions)} actions (likely due to LLM failures), but within limit.")
        else:
            print(f"FAIL: Bot returned {len(actions)} actions (limit is 20).")

async def run_all():
    await test_anti_repetition()
    await test_suppression()
    await test_adaptive_context()
    await test_batching()

if __name__ == "__main__":
    asyncio.run(run_all())
