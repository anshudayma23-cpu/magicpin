import logging

logger = logging.getLogger("vera.rationale_quality")

RATIONALE_INSTRUCTION = """
### RATIONALE RULES (Strictly 1-2 sentences):
1. Start by naming the Trigger Kind (e.g., 'For this research_digest...').
2. Explicitly name the compulsion lever used (e.g., 'using Loss Aversion and Social Proof').
3. Reference the specific merchant data point that drove this message (e.g., 'anchored on their 12% CTR dip').

Example: "For this perf_dip trigger, I used Loss Aversion by highlighting the 15% view drop compared to peers in {locality}."
"""

class RationaleOptimizer:
    @staticmethod
    def get_instruction() -> str:
        return RATIONALE_INSTRUCTION

# This will be integrated into the system prompts for all variants.
