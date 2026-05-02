from typing import Dict

# --- Specialized Instructional Variants ---

VARIANTS = {
    "research_digest": """
    STRATEGY: RECIPROCITY & AUTHORITY
    - Frame this as 'I noticed something you might find valuable.'
    - You MUST cite the source (e.g., 'Per the JIDA latest update...') and the specific summary.
    - LEVER: Curiosity. Don't reveal everything; invite them to see how it applies to their clinic.
    """,
    
    "perf_dip": """
    STRATEGY: LOSS AVERSION & SOCIAL PROOF
    - Anchor the conversation in the 'Views' or 'Calls' drop.
    - Mention that peer clinics in {city} are seeing {avg_ctr} CTR while the merchant is at {current_ctr}.
    - LEVER: FOMO. Suggest a specific high-value offer from the catalog to bridge the gap.
    """,
    
    "recall_due": """
    STRATEGY: EFFORT EXTERNALIZATION
    - Frame this as 'I've noticed {customer_name} is due for their {service}.'
    - Be proactive: 'I've drafted a message for them, want me to send it?'
    - LEVER: Reciprocity. Show you are doing the 'work' of managing their patient roster.
    """,
    
    "event_trigger": """
    STRATEGY: CONTEXTUAL RELEVANCE
    - Link the external event (e.g., IPL Match, Festival) to a specific business opportunity.
    - LEVER: Urgency. 'Before the rush starts...' or 'While the match is on...'
    """,
    
    "curious_ask_due": """
    STRATEGY: ASKING THE MERCHANT
    - Low-stakes, high-engagement question.
    - 'What's been your most requested service this week?'
    - LEVER: Curiosity. 'I'm seeing a trend in {locality}, want to see if it matches your experience?'
    """
}

# Mapping of all 24+ trigger kinds to a variant family
DISPATCH_MAP = {
    "research_digest": "research_digest",
    "regulation_change": "research_digest",
    "cde_opportunity": "research_digest",
    
    "perf_dip": "perf_dip",
    "perf_spike": "perf_dip",
    "seasonal_perf_dip": "perf_dip",
    "milestone_reached": "perf_dip",
    
    "recall_due": "recall_due",
    "chronic_refill_due": "recall_due",
    "trial_followup": "recall_due",
    "customer_lapsed_hard": "recall_due",
    
    "festival_upcoming": "event_trigger",
    "ipl_match_today": "event_trigger",
    "competitor_opened": "event_trigger",
    "category_seasonal": "event_trigger",
    
    "curious_ask_due": "curious_ask_due",
    "active_planning_intent": "recall_due", # Effort externalization
}

class VariantDispatcher:
    @staticmethod
    def get_variant_instruction(kind: str) -> str:
        variant_key = DISPATCH_MAP.get(kind, "perf_dip") # Default to data-driven
        return VARIANTS.get(variant_key, "")

if __name__ == "__main__":
    # Test dispatch
    print(f"Instruction for 'regulation_change':\n{VariantDispatcher.get_variant_instruction('regulation_change')}")
