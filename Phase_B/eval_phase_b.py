import httpx
import time
import subprocess
import os
import json

BOT_URL = "http://127.0.0.1:8081"
BOT_DIR = r"d:\cursor\magicpin-ai-challenge\Phase_B\B.5_Wire_Tick"

def run_evaluation():
    print("--- Phase B Evaluation Started ---")
    
    # Start bot
    process = subprocess.Popen(
        ["python", "bot.py"],
        cwd=BOT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for server
    time.sleep(5)
    
    try:
        with httpx.Client() as client:
            # 1. Setup Contexts
            print("\n[1/4] Ingesting Contexts...")
            
            # Category
            cat_payload = {
                "scope": "category", "context_id": "dentists", "version": 1,
                "payload": {
                    "slug": "dentists",
                    "voice": {"tone": "clinical", "vocab_allowed": ["scaling"], "vocab_taboo": ["cheap", "discount"]},
                    "digest": [{"id": "d1", "kind": "research", "title": "JIDA Update", "source": "JIDA", "summary": "New guidelines for scaling."}]
                },
                "delivered_at": "2026-04-30T20:00:00Z"
            }
            client.post(f"{BOT_URL}/v1/context", json=cat_payload)
            
            # Merchant
            merch_payload = {
                "scope": "merchant", "context_id": "m_001", "version": 1,
                "payload": {
                    "merchant_id": "m_001", "category_slug": "dentists",
                    "identity": {"name": "Smile Care", "owner_first_name": "Vikram", "languages": ["en", "hi"]},
                    "performance": {"views": 1000, "calls": 10, "ctr": 0.01, "delta_7d": {"views_pct": -0.2}}
                },
                "delivered_at": "2026-04-30T20:00:00Z"
            }
            client.post(f"{BOT_URL}/v1/context", json=merch_payload)
            
            # Trigger
            trg_payload = {
                "scope": "trigger", "context_id": "trg_001", "version": 1,
                "payload": {
                    "id": "trg_001", "kind": "perf_dip", "merchant_id": "m_001",
                    "payload": {"metric": "views", "delta": -20},
                    "urgency": 5, "suppression_key": "perf_dip:m_001:test1"
                },
                "delivered_at": "2026-04-30T20:00:00Z"
            }
            client.post(f"{BOT_URL}/v1/context", json=trg_payload)
            
            # Debug: Check counts
            h_resp = client.get(f"{BOT_URL}/v1/healthz")
            print(f"Healthz Counts: {h_resp.json().get('contexts_loaded')}")

            # 2. Test Tick Composition
            print("\n[2/4] Testing Proactive Composition (/v1/tick)...")
            tick_payload = {
                "now": "2026-04-30T21:00:00Z",
                "available_triggers": ["trg_001"]
            }
            
            start_time = time.time()
            resp = client.post(f"{BOT_URL}/v1/tick", json=tick_payload, timeout=30)
            latency = time.time() - start_time
            
            print(f"Tick Latency: {latency:.2f}s")
            
            if resp.status_code == 200:
                actions = resp.json().get("actions", [])
                if actions:
                    action = actions[0]
                    print(f"Action Body: {action['body']}")
                    print(f"Action Rationale: {action['rationale']}")
                    print(f"Action CTA: {action['cta']}")
                    
                    # 3. Validation Checks
                    print("\n[3/4] Running Guardrail Validations...")
                    body = action['body'].lower()
                    
                    # Taboo Check
                    if "cheap" in body or "discount" in body:
                        print("FAIL: Taboo word detected in body!")
                    else:
                        print("PASS: No taboo words detected.")
                        
                    # URL Check
                    if "http" in body:
                        print("FAIL: URL detected in body!")
                    else:
                        print("PASS: No URLs detected.")
                        
                    print("PASS: LLM returned valid JSON structure.")
                    
                else:
                    print("FAIL: No actions returned in tick response.")
            else:
                print(f"FAIL: Tick endpoint returned {resp.status_code}")
                print(resp.text)

            # 4. Suppression Test
            print("\n[4/4] Testing Suppression Logic...")
            resp_dup = client.post(f"{BOT_URL}/v1/tick", json=tick_payload)
            if len(resp_dup.json().get("actions", [])) == 0:
                print("PASS: Duplicate trigger suppressed correctly.")
            else:
                print("FAIL: Duplicate trigger was NOT suppressed.")

    except Exception as e:
        print(f"ERROR during evaluation: {str(e)}")
    finally:
        process.terminate()
        print("\n--- Phase B Evaluation Complete ---")

if __name__ == "__main__":
    run_evaluation()
