import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("vera.language_matching")

class LanguageEngine:
    @staticmethod
    def get_language_instructions(merchant: Dict[str, Any], customer: Optional[Dict[str, Any]] = None) -> str:
        """
        Generates specific language and code-mixing instructions based on identities.
        """
        merch_langs = merchant.get("identity", {}).get("languages", ["en"])
        cust_lang = customer.get("identity", {}).get("language_pref", "") if customer else ""
        
        # Priority 1: Customer preference (if messaging customer)
        if cust_lang:
            return f"The customer prefers {cust_lang}. Please use this language. If it includes a regional Indian language, use natural code-mix with English."
            
        # Priority 2: Merchant languages
        if "hi" in merch_langs:
            return """
            The merchant prefers Hindi-English code-mix (Hinglish). 
            - Use natural, conversational Hinglish (e.g., 'Aapka business growth dekhkar khushi hui'). 
            - Keep the tone professional but warm.
            - Ensure numbers and technical terms stay in English for clarity.
            """
        
        return "The primary language is English. Keep the tone professional and clear."

    @staticmethod
    def format_currency(amount: float) -> str:
        """Ensures local currency formatting."""
        return f"Rs. {amount:,}"

# Update the PromptBuilder to use this engine
# This would be integrated into base_prompt.py or the composition engine.
