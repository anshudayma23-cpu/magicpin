import asyncio
import httpx
import time
import statistics
from typing import List

BOT_URL = "http://localhost:8081"
CONCURRENT_REQUESTS = 10

async def fire_tick(client: httpx.AsyncClient, request_id: int):
    """Sends a single tick request and measures latency."""
    payload = {
        "now": "2026-04-30T10:00:00Z",
        "available_triggers": ["trg_001", "trg_002", "trg_003"]
    }
    
    start_time = time.time()
    try:
        response = await client.post(f"{BOT_URL}/v1/tick", json=payload, timeout=35.0)
        latency = time.time() - start_time
        status = response.status_code
        actions_count = len(response.json().get("actions", []))
        print(f"Request {request_id:02d}: Status {status}, Latency {latency:.2f}s, Actions: {actions_count}")
        return latency
    except Exception as e:
        print(f"Request {request_id:02d}: FAILED with {type(e).__name__}")
        return None

async def run_load_test():
    print(f"Starting Load Test: {CONCURRENT_REQUESTS} concurrent requests to {BOT_URL}/v1/tick")
    print("-" * 60)
    
    async with httpx.AsyncClient() as client:
        tasks = [fire_tick(client, i) for i in range(CONCURRENT_REQUESTS)]
        latencies = await asyncio.gather(*tasks)
        
    valid_latencies = [l for l in latencies if l is not None]
    
    if not valid_latencies:
        print("Error: No requests succeeded.")
        return

    print("-" * 60)
    print(f"Completed: {len(valid_latencies)}/{CONCURRENT_REQUESTS} succeeded.")
    print(f"Min Latency: {min(valid_latencies):.2f}s")
    print(f"Max Latency: {max(valid_latencies):.2f}s")
    print(f"Avg Latency: {statistics.mean(valid_latencies):.2f}s")
    
    if max(valid_latencies) > 30:
        print("\nWARNING: Some requests exceeded the 30s SLA!")
    else:
        print("\nSUCCESS: All requests within 30s budget.")

if __name__ == "__main__":
    asyncio.run(run_load_test())
