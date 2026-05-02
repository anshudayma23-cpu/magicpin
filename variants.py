from typing import Dict

# --- Specialized Instructional Variants ---
# Each variant tells the LLM WHICH payload fields to extract and HOW to use them.

VARIANTS = {
    "perf_dip": """
    STRATEGY: DATA-ANCHORED LOSS AVERSION
    - SENTENCE 1: State the metric and exact drop from `delta_pct`.
    - SENTENCE 2: CONTRARIAN INSIGHT. Recommend a specific action based on their active offers, instead of just running a generic promo.
    - CTA: [CLINICAL: "Retention Audit" | COMMERCIAL: "Free Consultation Offer"] + [Time: "Live in 10 min/2 min review"] + [Objection: "No workflow disruption/No auto-charge"].
    """,

    "perf_spike": """
    STRATEGY: MOMENTUM CAPTURE
    - SENTENCE 1: Celebrate the spike citing `delta_pct`.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Recommend doubling down on the specific active offer or theme driving this to sustain the momentum.
    - CTA: [CLINICAL: "Success Story Protocol" | COMMERCIAL: "Success Story Ad Boost"] + [Time: "5 min setup"] + [Objection: "No extra effort"].
    """,

    "research_digest": """
    STRATEGY: AUTHORITY + CURIOSITY
    - SENTENCE 1: Reference the research/digest from `category`.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Connect the research finding to a specific customer segment or service they offer.
    - CTA: [CLINICAL: "Patient Education Protocol" | COMMERCIAL: "Expert Insight Abstract"] + [Time: "2-min read"] + [Objection: "Just say go"].
    """,

    "regulation_change": """
    STRATEGY: COMPLIANCE URGENCY
    - SENTENCE 1: State the change and EXACT `deadline_iso`.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Provide a highly specific action they must take today to avoid non-compliance.
    - CTA: ["Compliance Audit Checklist"] + ["Ready by tomorrow 5pm"] + ["No workflow disruption"].
    """,

    "recall_due": """
    STRATEGY: REVENUE RECOVERY
    - SENTENCE 1: Name `service_due` and last date.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Suggest booking them into a specific open slot or attaching an active offer.
    - CTA: ["Personalized Slot Reminder"] + ["5-min setup"] + ["Just say YES to send"].
    """,

    "renewal_due": """
    STRATEGY: LOSS AVERSION
    - SENTENCE 1: State `plan` and `days_remaining`.
    - SENTENCE 2: CONTRARIAN INSIGHT. Recommend locking in the exact current plan price now, rather than waiting and risking a price hike or views drop.
    - CTA: ["Renewal Documentation"] + ["Takes 1 min"] + ["Lock in your current price"].
    """,

    "event_trigger": """
    STRATEGY: FOMO + MOMENTUM
    - SENTENCE 1: Name event/match and time.
    - SENTENCE 2: CONTRARIAN INSIGHT. Recommend the counter-intuitive action (e.g. push delivery instead of dine-in on a match night).
    - CTA: ["Swiggy Banner + Insta Story"] + ["Live in 10 min"] + ["No auto-charge"].
    """,

    "review_theme": """
    STRATEGY: CUSTOMER VOICE
    - SENTENCE 1: State `theme` and quote `common_quote`.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Suggest a specific operational tweak based on the review feedback.
    - CTA: ["Response Protocol + Process Audit"] + ["5-min review"] + ["No commitment"].
    """,

    "supply_alert": """
    STRATEGY: PATIENT SAFETY
    - SENTENCE 1: Name `molecule` and batch numbers.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. State exactly how many patients are affected based on context data and what to tell them.
    - CTA: ["Patient Alert Note + Pickup Workflow"] + ["Ready in 5 min"] + ["No workflow disruption"].
    """,

    "winback": """
    STRATEGY: LOSS QUANTIFICATION
    - SENTENCE 1: State days since lapse and `perf_dip_pct`.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Recommend re-engaging them with a specific active offer or new service.
    - CTA: ["Reactivation Campaign"] + ["Live in 10 min"] + ["No commitment required"].
    """,

    "milestone": """
    STRATEGY: POSITIVE MOMENTUM
    - SENTENCE 1: Celebrate `value_now` vs `milestone_value`.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Suggest leveraging this milestone to push a specific high-margin service.
    - CTA: ["Milestone Celebration Post"] + ["5-min setup"] + ["No auto-charge"].
    """,

    "planning_intent": """
    STRATEGY: EXECUTION PARTNER
    - SENTENCE 1: Reference `merchant_last_message`.
    - SENTENCE 2: CONTRARIAN INSIGHT. Suggest a specific, structured way to execute their idea that they might not have thought of.
    - CTA: ["Full Execution Draft"] + ["Ready by tomorrow 5pm"] + ["You can edit it first"].
    """,

    "chronic_refill": """
    STRATEGY: PATIENT CARE
    - SENTENCE 1: List `molecule_list` and `stock_runs_out_iso`.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Suggest setting up a recurring delivery or attaching a relevant active offer.
    - CTA: ["Refill Order + Delivery Schedule"] + ["Takes 1 min"] + ["Reply YES to confirm"].
    """,

    "curious_ask": """
    STRATEGY: ENGAGEMENT
    - SENTENCE 1: Reference market trend.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Suggest a specific action they can take today to capitalize on this trend.
    - CTA: ["Google Post + Reply Template"] + ["Takes 5 min"] + ["No effort needed"].
    """,

    "gbp_unverified": """
    STRATEGY: MISSED OPPORTUNITY
    - SENTENCE 1: State `unverified` and `estimated_uplift_pct`.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Connect the lack of verification to a specific missed opportunity (e.g. losing calls to a competitor).
    - CTA: ["Verification Request Support"] + ["Takes 2 min"] + ["No auto-charge"].
    """,

    "dormant": """
    STRATEGY: RE-ENGAGEMENT
    - SENTENCE 1: Acknowledge days since last chat.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Bring them a highly specific opportunity based on their latest signals or review themes.
    - CTA: ["Catch-up Opportunity Report"] + ["Ready by tomorrow morning"] + ["No commitment"].
    """,

    "competitor": """
    STRATEGY: COMPETITIVE INTELLIGENCE
    - SENTENCE 1: Name `competitor_name` and `their_offer`.
    - SENTENCE 2: CONTRARIAN INSIGHT. Explain why matching their price is a mistake, and suggest competing on a specific quality or service instead.
    - CTA: ["Counter-Offer Strategy"] + ["Done in 10 min"] + ["You can edit it first"].
    """,

    "bridal_followup": """
    STRATEGY: TIMELINE URGENCY
    - SENTENCE 1: Reference `wedding_date`.
    - SENTENCE 2: SPECIFIC RECOMMENDATION. Suggest booking a specific prep service right now before the window closes.
    - CTA: ["Personalized Appointment Reminder"] + ["Ready in 2 min"] + ["Just say go"].
    """

}

# Complete mapping of ALL trigger kinds to variant families
DISPATCH_MAP = {
    # Research & Compliance
    "research_digest": "research_digest",
    "regulation_change": "regulation_change",
    "cde_opportunity": "research_digest",

    # Performance
    "perf_dip": "perf_dip",
    "perf_spike": "perf_spike",
    "seasonal_perf_dip": "perf_dip",
    "milestone_reached": "milestone",

    # Customer Lifecycle
    "recall_due": "recall_due",
    "chronic_refill_due": "chronic_refill",
    "trial_followup": "recall_due",
    "customer_lapsed_hard": "winback",
    "wedding_package_followup": "bridal_followup",

    # Events & Seasonal
    "festival_upcoming": "event_trigger",
    "ipl_match_today": "event_trigger",
    "competitor_opened": "competitor",
    "category_seasonal": "event_trigger",

    # Merchant Engagement
    "curious_ask_due": "curious_ask",
    "active_planning_intent": "planning_intent",
    "dormant_with_vera": "dormant",

    # Operational
    "renewal_due": "renewal_due",
    "supply_alert": "supply_alert",
    "review_theme_emerged": "review_theme",
    "winback_eligible": "winback",
    "gbp_unverified": "gbp_unverified",
}

class VariantDispatcher:
    @staticmethod
    def get_variant_instruction(
        kind: str,
        category_slug: str = "unknown",
        high_risk_count: int = 0,
        peer_calls: int = 0,
        merch_calls: int = 0,
        locality: str = "your area",
    ) -> str:
        variant_key = DISPATCH_MAP.get(kind, "perf_dip")
        base_instr = VARIANTS.get(variant_key, VARIANTS["perf_dip"])

        # ── Phase I3: Category voice reinforcement — 2 example sentences per category ──
        if category_slug == "dentists":
            count_str = f"{high_risk_count} patients" if high_risk_count else "your high-risk patients"
            base_instr += (
                f"\n    - VOCAB: Use terms like 'patient recall', 'clinical conversion', 'fluoride varnish', 'caries risk'."
                f"\n    - VOICE EXAMPLE 1: 'Your high-risk adult cohort ({count_str}) are exactly the segment JIDA flagged for 3-month recall.'"
                f"\n    - VOICE EXAMPLE 2: 'Skipping recall now means 38% higher caries risk for this cohort \u2014 a clinical and revenue loss combined.'"
            )
        elif category_slug == "pharmacies":
            base_instr += (
                "\n    - VOCAB: Use terms like 'chronic Rx', 'sub-potency', 'compliance', 'dispensing audit'."
                "\n    - VOICE EXAMPLE 1: 'Your chronic Rx patients on this molecule are at risk \u2014 sub-potency batches affect 1 in 3 non-compliant refills.'"
                "\n    - VOICE EXAMPLE 2: 'A quick dispensing audit now protects patient safety and keeps your pharmacy from liability.'"
            )
        elif category_slug == "salons":
            base_instr += (
                "\n    - VOCAB: Use terms like 'walk-ins', 'stylist schedule', 'chair utilisation', 'keratin', 'footfall'."
                f"\n    - VOICE EXAMPLE 1: 'Keratin search volume is up 28% in {locality} \u2014 perfect time to fill your stylist's open Tuesday slots.'"
                f"\n    - VOICE EXAMPLE 2: 'Your {peer_calls} peer-avg footfall benchmark shows {merch_calls} walk-ins is below what top salons in {locality} pull.'"
            )
        elif category_slug == "gyms":
            base_instr += (
                "\n    - VOCAB: Use terms like 'active members', 'trial conversion', 'retention window', 'batch utilisation'."
                f"\n    - VOICE EXAMPLE 1: 'Apr\u2013Jun is the post-resolution lull \u2014 every metro gym sees \u221225% to \u221235% in this window; your {merch_calls} check-ins confirm it.'"
                "\n    - VOICE EXAMPLE 2: 'Converting even 15% of trial members this month locks in annualised revenue before the summer slump hits.'"
            )
        elif category_slug == "restaurants":
            _aov_str = f"Rs.{merch_calls * 12}" if merch_calls else "Rs.X"
            base_instr += (
                "\n    - VOCAB: Use terms like 'covers', 'AOV', 'dine-in traffic', 'delivery mix', 'table turn'."
                f"\n    - VOICE EXAMPLE 1: 'Saturday night covers drop 12% on IPL match nights (magicpin Metro Benchmark 2026) \u2014 push delivery, not dine-in.'"
                f"\n    - VOICE EXAMPLE 2: 'Your current AOV of {_aov_str} trails the {locality} leader by 18% \u2014 a single upsell item closes that gap.'"
            )

        elif category_slug == "spas":
            base_instr += (
                "\n    - VOCAB: Use terms like 'appointment utilisation', 'lapsed guests', 'treatment package', 'retention'."
                "\n    - VOICE EXAMPLE 1: 'Your lapsed guests are 3x more likely to rebook when contacted within 90 days of their last visit.'"
                "\n    - VOICE EXAMPLE 2: 'A targeted re-engagement offer on your most popular treatment converts at 25% \u2014 no discount needed.'"
            )

        return base_instr


if __name__ == "__main__":
    # Verify all 25 trigger kinds are mapped
    from dataset_triggers import TRIGGER_KINDS  # optional test
    missing = [k for k in TRIGGER_KINDS if k not in DISPATCH_MAP]
    print(f"Missing mappings: {missing}" if missing else "All trigger kinds covered!")
