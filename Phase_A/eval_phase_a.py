import httpx
import time
import subprocess
import os
import signal

BOT_URL = "http://127.0.0.1:8081"
BOT_DIR = r"d:\cursor\magicpin-ai-challenge\Phase_A\A.4_FastAPI_Endpoints"

def run_evaluation():
    print("--- Phase A Evaluation Started ---")
    
    # 1. Startup Check
    print("\n[1/4] Startup Check...")
    process = subprocess.Popen(
        ["python", "bot.py"],
        cwd=BOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server to start
    start_time = time.time()
    started = False
    while time.time() - start_time < 10:
        try:
            with httpx.Client() as client:
                resp = client.get(f"{BOT_URL}/v1/healthz")
                if resp.status_code == 200:
                    started = True
                    break
        except:
            time.sleep(1)
    
    if not started:
        print("FAIL: Server failed to start within 10s")
        process.terminate()
        return

    print("PASS: Server started and /v1/healthz is reachable.")

    # 2. Schema & Metadata Validation
    print("\n[2/4] Metadata Validation...")
    with httpx.Client() as client:
        resp = client.get(f"{BOT_URL}/v1/metadata")
        print(f"Metadata Response: {resp.json()}")
        if resp.status_code == 200 and "team_name" in resp.json():
            print("PASS: /v1/metadata returns valid team info.")
        else:
            print("FAIL: /v1/metadata invalid.")

    # 3. Store Idempotency Check
    print("\n[3/4] Store Idempotency Check...")
    ctx_payload = {
        "scope": "merchant",
        "context_id": "m_test_001",
        "version": 1,
        "payload": {"name": "Test Merchant"},
        "delivered_at": "2026-04-30T20:00:00Z"
    }

    with httpx.Client() as client:
        # First push (v1)
        resp1 = client.post(f"{BOT_URL}/v1/context", json=ctx_payload)
        print(f"Push v1: {resp1.status_code} {resp1.json()}")
        
        # Second push (v1 again)
        resp2 = client.post(f"{BOT_URL}/v1/context", json=ctx_payload)
        print(f"Push v1 again: {resp2.status_code} {resp2.json()}")
        
        # Third push (v2)
        ctx_payload["version"] = 2
        resp3 = client.post(f"{BOT_URL}/v1/context", json=ctx_payload)
        print(f"Push v2: {resp3.status_code} {resp3.json()}")

        if resp1.status_code == 200 and resp2.status_code == 409 and resp3.status_code == 200:
            print("PASS: Versioned idempotency logic is correct.")
        else:
            print("FAIL: Idempotency logic failed.")

    # 4. Final Health Check (Counts)
    print("\n[4/4] Health Check Counts...")
    with httpx.Client() as client:
        resp = client.get(f"{BOT_URL}/v1/healthz")
        counts = resp.json().get("contexts_loaded", {})
        print(f"Context Counts: {counts}")
        if counts.get("merchant") == 1:
            print("PASS: Counts correctly reflect stored contexts.")
        else:
            print("FAIL: Count mismatch.")

    print("\n--- Phase A Evaluation Complete ---")
    
    # Cleanup
    process.terminate()
    try:
        process.wait(timeout=5)
    except:
        process.kill()

if __name__ == "__main__":
    run_evaluation()
