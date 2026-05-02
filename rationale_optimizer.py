
RATIONALE_INSTRUCTION = """
### RATIONALE RULES (Strictly 1-2 sentences):
1. **Name the Lever**: State which engagement lever you used: Loss Aversion, Curiosity Gap, Social Proof, Effort Externalization, or FOMO.
2. **Cite the Data**: Reference the exact number from the context that anchors the message (e.g., "50% call drop", "4 reviews mentioning delays").
3. **Peer Comparison**: If you used peer benchmarks, state the merchant-vs-peer delta (e.g., "67% below peer avg in calls").

Example: "Loss Aversion + Social Proof: Highlighted the 50% call drop (vs_baseline 12) and the fact that merchant is 67% below peer avg in calls, creating urgency to activate a free consultation offer."
"""

class RationaleOptimizer:
    @staticmethod
    def get_instruction() -> str:
        return RATIONALE_INSTRUCTION
