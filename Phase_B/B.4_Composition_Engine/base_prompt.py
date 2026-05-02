from typing import Optional, Dict, Any
import json

BASE_SYSTEM_PROMPT = """
You are Vera, a highly intelligent and proactive merchant AI assistant for magicpin.
Your goal is to engage merchants with data-driven insights and specific, actionable opportunities.

### OPERATIONAL RULES:
1. **Grounded Data**: Use ONLY the numbers, dates, names, and source citations provided in the contexts. Never invent performance data or offers.
2. **Category Voice**: strictly match the {voice_tone} provided. 
3. **Vocabulary**: 
   - Use these allowed words: {vocab_allowed}
   - NEVER use these taboo words: {vocab_taboo}
4. **Personalization**: Address the owner by their first name ({owner_name}) when appropriate.
5. **Language**: Honor the merchant's language preferences ({languages}). If "hi" (Hindi) is included, use natural Hindi-English code-mix (Hinglish).
6. **No Preambles**: Do not start with "I hope you are doing well" or "As an AI...". Start directly with the data-driven hook or insight.
7. **Single CTA**: Provide exactly one clear Call to Action at the end of the message.
8. **No URLs**: Never include website links or URLs in the message body.

### OUTPUT FORMAT:
You MUST respond with a valid JSON object containing:
{
  "body": "The WhatsApp message content",
  "cta": "The type of CTA (open_ended | binary_yes_no | binary_confirm_cancel | none)",
  "template_name": "vera_{trigger_kind}_v1",
  "template_params": ["list", "of", "data", "points", "used"],
  "rationale": "1-2 sentences explaining which compulsion lever you used and why this message fits the merchant state."
}
"""

class PromptBuilder:
    @staticmethod
    def build_system_prompt(category: Dict[str, Any], merchant: Dict[str, Any], trigger_kind: str) -> str:
        voice = category.get("voice", {})
        identity = merchant.get("identity", {})
        
        return BASE_SYSTEM_PROMPT.format(
            voice_tone=voice.get("tone", "professional"),
            vocab_allowed=", ".join(voice.get("vocab_allowed", [])),
            vocab_taboo=", ".join(voice.get("vocab_taboo", [])),
            owner_name=identity.get("owner_first_name", "Merchant"),
            languages=", ".join(identity.get("languages", ["en"])),
            trigger_kind=trigger_kind
        )

    @staticmethod
    def build_user_prompt(trigger: Dict[str, Any], merchant: Dict[str, Any], customer: Optional[Dict[str, Any]] = None) -> str:
        # Construct a detailed context block for the LLM to analyze
        context_block = {
            "trigger": trigger,
            "merchant_performance": merchant.get("performance", {}),
            "merchant_signals": merchant.get("signals", []),
            "active_offers": merchant.get("offers", []),
            "customer_context": customer if customer else "N/A"
        }
        
        return f"CONTEXT DATA:\n{json.dumps(context_block, indent=2)}\n\nCompose the WhatsApp message now."

if __name__ == "__main__":
    # Test rendering
    sample_cat = {"voice": {"tone": "clinical", "vocab_allowed": ["scaling", "CDE"], "vocab_taboo": ["cheap"]}}
    sample_merch = {"identity": {"owner_first_name": "Vikram", "languages": ["en", "hi"]}}
    
    print("--- SYSTEM PROMPT ---")
    print(PromptBuilder.build_system_prompt(sample_cat, sample_merch, "perf_dip"))
