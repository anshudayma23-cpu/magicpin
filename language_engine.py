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
            The merchant prefers **Hinglish 2.0** (Natural Conversational Hindi-English code-mix).
            - **Avoid Formal Hindi**: Do not use words like 'anurodh' or 'suvidha'. 
            - **Business English**: Keep business terms (market, traffic, customers, walk-ins, visibility, offer) in English.
            - **Conversational Hindi**: Use Hindi for the connective tissue (e.g., 'Market kaafi competitive ho gaya hai', 'Ye offer aapki growth badha sakta hai').
            - **Vibe**: Sound like a savvy Delhi/Mumbai business partner who is "seedhi baat, no bakwaas".
            """
        
        return "The primary language is English. Keep the tone professional and clear."

    @staticmethod
    def format_currency(amount: float) -> str:
        """Ensures local currency formatting."""
        return f"Rs. {amount:,}"

# Update the PromptBuilder to use this engine
# This would be integrated into base_prompt.py or the composition engine.
