import json
import logging
import re
from typing import Optional, Dict, Any
from llm_client import call_llm
from base_prompt import PromptBuilder
from variants import VariantDispatcher

logger = logging.getLogger("vera.composition_engine")

class CompositionEngine:
    async def compose_proactive(
        self, 
        category: Dict[str, Any], 
        merchant: Dict[str, Any], 
        trigger: Dict[str, Any], 
        customer: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Assembles contexts, builds prompts, calls LLM, and validates output.
        """
        trigger_kind = trigger.get("kind", "unknown")
        
        # 1. Build Prompts
        system_base = PromptBuilder.build_system_prompt(category, merchant, trigger_kind)
        variant_instr = VariantDispatcher.get_variant_instruction(trigger_kind)
        
        final_system_prompt = f"{system_base}\n\n{variant_instr}"
        user_prompt = PromptBuilder.build_user_prompt(trigger, merchant, customer)
        
        # 2. Call LLM (Resilient)
        raw_response = await call_llm(final_system_prompt, user_prompt)
        if not raw_response:
            logger.error("LLM returned empty response for proactive composition.")
            return None
            
        # 3. Parse and Validate
        parsed = self._parse_and_validate(raw_response, trigger, category)
        if not parsed:
            return None
            
        # 4. Enrich with Meta-data
        parsed["conversation_id"] = f"conv_{trigger['id']}"
        parsed["merchant_id"] = merchant["merchant_id"]
        parsed["customer_id"] = trigger.get("customer_id")
        parsed["trigger_id"] = trigger["id"]
        parsed["suppression_key"] = trigger.get("suppression_key")
        
        # Determine 'send_as'
        # Default: Vera messages merchant. 
        # If scope is 'customer', Vera messages customer on behalf of merchant.
        parsed["send_as"] = "merchant_on_behalf" if trigger.get("scope") == "customer" else "vera"
        
        return parsed

    def _parse_and_validate(self, raw_text: str, trigger: Dict[str, Any], category: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            # Attempt to extract JSON if LLM included conversational filler
            json_match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            clean_json = json_match.group(0) if json_match else raw_text
            
            data = json.loads(clean_json)
            
            # --- Operational Validation ---
            body = data.get("body", "")
            
            # Rule: No URLs
            if "http" in body or ".com" in body or ".in" in body:
                logger.warning("Validation failed: Body contains URL. Stripping...")
                data["body"] = re.sub(r"http\S+|www\.\S+", "", body).strip()
            
            # Rule: No Taboo words (case-insensitive check)
            taboos = category.get("voice", {}).get("vocab_taboo", [])
            for word in taboos:
                if word.lower() in data["body"].lower():
                    logger.warning(f"Validation failed: Taboo word '{word}' detected. Replacing...")
                    data["body"] = data["body"].replace(word, "[redacted]")

            # Rule: Ensure single CTA (simple check for too many question marks or directives)
            # This is primarily handled via prompt, but we can log suspicious outputs.

            return data
            
        except Exception as e:
            logger.error(f"Failed to parse LLM response as JSON: {str(e)}\nRaw: {raw_text}")
            return None

# --- Test ---
if __name__ == "__main__":
    import asyncio
    logging.basicConfig(level=logging.INFO)
    
    async def test():
        engine = CompositionEngine()
        cat = {"slug": "dentists", "voice": {"tone": "clinical", "vocab_allowed": ["scaling"], "vocab_taboo": ["cheap"]}}
        merch = {"merchant_id": "m_001", "identity": {"owner_first_name": "Vikram", "languages": ["en", "hi"]}}
        trg = {"id": "trg_001", "kind": "perf_dip", "scope": "merchant", "payload": {"views": 100}}
        
        print("Testing Composition Engine...")
        result = await engine.compose_proactive(cat, merch, trg)
        print(f"\nFinal Action Object:\n{json.dumps(result, indent=2)}")
        
    asyncio.run(test())
