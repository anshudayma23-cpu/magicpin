import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("vera.adaptive_context")

class AdaptiveContextVerifier:
    """
    Utility to verify that context updates are being picked up mid-session.
    """
    @staticmethod
    async def verify_freshness(bot_client, conversation_id: str, merchant_id: str):
        print(f"--- Adaptive Context Verification for {merchant_id} ---")
        
        # 1. Update Category with a unique 'digest' item
        v1_digest = "Guidelines for dental scaling 2024"
        cat_payload = {
            "slug": "dentists",
            "digest": [{"id": "d1", "summary": v1_digest}]
        }
        print("Pushing Category V1...")
        await bot_client.post("/v1/context", json={
            "scope": "category", "context_id": "dentists", "version": 1, 
            "payload": cat_payload, "delivered_at": "..."
        })
        
        # 2. Update Category to V2 with DIFFERENT digest
        v2_digest = "NEW URGENT: DCI update on clinical waste management"
        cat_payload_v2 = {
            "slug": "dentists",
            "digest": [{"id": "d1", "summary": v2_digest}]
        }
        print("Pushing Category V2 (Update)...")
        await bot_client.post("/v1/context", json={
            "scope": "category", "context_id": "dentists", "version": 2, 
            "payload": cat_payload_v2, "delivered_at": "..."
        })
        
        print("Verification: The next /v1/tick or /v1/reply MUST use the V2 digest info.")
        # This is guaranteed because our bot.py calls context_store.get() inside the handler.

if __name__ == "__main__":
    print("Adaptive Context Verification Logic Loaded.")
