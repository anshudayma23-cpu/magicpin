import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger("vera.validator")

class OutputValidator:
    def __init__(self):
        self.url_pattern = re.compile(r"http\S+|www\.\S+|\S+\.(com|in|org|net)\b")

    def validate(self, body: str, category: Dict[str, Any]) -> str:
        """
        Runs a series of safety and quality checks on the message body.
        """
        if not body:
            return ""

        # 1. URL Stripping
        body = self.url_pattern.sub("[link removed]", body)

        # 2. Taboo Word Redaction
        taboos = category.get("voice", {}).get("vocab_taboo", [])
        for word in taboos:
            # Case-insensitive whole-word replacement
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            if pattern.search(body):
                logger.warning(f"Validator: Redacting taboo word '{word}'")
                body = pattern.sub("[redacted]", body)

        # 3. Multi-CTA Pruning (Relaxed)
        # We allow up to 2 questions to support curiosity + action hooks.
        # Prune only if there are 3 or more questions.
        sentences = re.split(r"(?<=[.!?]) +", body)
        questions = [s for s in sentences if "?" in s]
        if len(questions) > 2:
            logger.warning(f"Validator: {len(questions)} CTAs detected. Pruning to final 2.")
            # Keep all non-questions, plus the final two questions
            new_sentences = [s for s in sentences if "?" not in s]
            new_sentences.extend(questions[-2:])
            body = " ".join(new_sentences)


        # 4. Length Guard (Max 1000 chars)
        if len(body) > 1000:
            logger.warning("Validator: Message too long. Truncating.")
            body = body[:997] + "..."

        # 5. Numeric Density Check (Specificity Guard) — Phase I1 hard enforcement
        numbers = re.findall(r'\d+', body)
        if len(numbers) < 2:
            logger.warning(f"Validator: Low specificity ({len(numbers)} numbers). Rejecting message — caller should retry.")
            return ""  # Return empty string so bot.py can retry

        # 6. Source Citation Repair (Phase I1 — active fix, not just warning)
        # If body uses peer comparison language without the citation string, inject it.
        CITATION = "[Ref: MP-Benchmark-2026-Q2]"
        peer_keywords = ['avg', 'peer', 'benchmark', 'vs peer', 'compared to']
        has_peer_language = any(kw in body.lower() for kw in peer_keywords)
        has_citation = CITATION.lower() in body.lower() or 'mp-benchmark-2026-q2' in body.lower()

        if has_peer_language and not has_citation:
            logger.warning("Validator (I1): Peer comparison detected but citation missing — repairing inline.")
            # Find the first sentence containing a peer keyword and append the citation to it
            sentences = re.split(r'(?<=[.!?]) +', body)
            repaired = False
            for i, sent in enumerate(sentences):
                if any(kw in sent.lower() for kw in peer_keywords):
                    sentences[i] = sent.rstrip('.!?') + f' {CITATION}.'
                    repaired = True
                    break
            if repaired:
                body = ' '.join(sentences)

    def _check_engagement_levers(self, body: str) -> tuple[int, list[str]]:
        """Count how many compulsion levers are present in the message."""
        levers = []
        
        # 1. Loss aversion — Rs. amount or "kho rahe ho" / "losing"
        if re.search(r'Rs\.\s*[\d,]+|kho rahe|losing|missed|revenue leak', body, re.I):
            levers.append("LOSS_AVERSION")
        
        # 2. Social proof — "2-3 dentists" / "leading" / "other clinics"
        if re.search(r'\d+\s*(dentist|clinic|salon|gym|restaurant|pharma)|leading|other\s+\w+\s+in', body, re.I):
            levers.append("SOCIAL_PROOF")
        
        # 3. Curiosity — "dekhna chahoge" / "want to see" / "worth a look"
        if re.search(r'dekhna\s+chah|want\s+to\s+see|worth\s+a\s+look|interested|curious', body, re.I):
            levers.append("CURIOSITY")
        
        # 4. Effort externalization — "maine" / "I've" / "ready hai" / "prepared"
        if re.search(r"maine\s+.*?(ready|pull|draft|prepare|identify|nikale|banaya)|I've\s+(already|prepared|pulled|drafted)", body, re.I):
            levers.append("EFFORT_EXTERNALIZATION")
        
        # 5. Reciprocity — "review karte hue" / "I noticed" / "dekha ki"
        if re.search(r'review\s+karte|I\s+noticed|dekha\s+ki|dekhte\s+hue', body, re.I):
            levers.append("RECIPROCITY")
        
        # 6. Binary CTA — "reply" / "boliye" / "karo"
        if re.search(r"reply|boliye|karo|just\s+say|go.*reply", body, re.I):
            levers.append("BINARY_CTA")
        
        return len(levers), levers

    def validate(self, body: str, category: Dict[str, Any]) -> str:
        """
        Runs a series of safety and quality checks on the message body.
        """
        if not body:
            return ""

        # 1. URL Stripping
        body = self.url_pattern.sub("[link removed]", body)

        # 2. Taboo Word Redaction
        taboos = category.get("voice", {}).get("vocab_taboo", [])
        for word in taboos:
            # Case-insensitive whole-word replacement
            pattern = re.compile(re.escape(word), re.IGNORECASE)
            if pattern.search(body):
                logger.warning(f"Validator: Redacting taboo word '{word}'")
                body = pattern.sub("[redacted]", body)

        # 3. Multi-CTA Pruning (Relaxed)
        sentences = re.split(r"(?<=[.!?]) +", body)
        questions = [s for s in sentences if "?" in s]
        if len(questions) > 2:
            logger.warning(f"Validator: {len(questions)} CTAs detected. Pruning to final 2.")
            new_sentences = [s for s in sentences if "?" not in s]
            new_sentences.extend(questions[-2:])
            body = " ".join(new_sentences)

        # 4. Length Guard (Max 1000 chars)
        if len(body) > 1000:
            logger.warning("Validator: Message too long. Truncating.")
            body = body[:997] + "..."

        # 5. Numeric Density Check (Specificity Guard)
        numbers = re.findall(r'\d+', body)
        if len(numbers) < 2:
            logger.warning(f"Validator: Low specificity ({len(numbers)} numbers). Rejecting.")
            return ""

        # 6. Source Citation Repair
        CITATION = "[Ref: MP-Benchmark-2026-Q2]"
        peer_keywords = ['avg', 'peer', 'benchmark', 'vs peer', 'compared to']
        has_peer_language = any(kw in body.lower() for kw in peer_keywords)
        has_citation = CITATION.lower() in body.lower() or 'mp-benchmark-2026-q2' in body.lower()

        if has_peer_language and not has_citation:
            sentences = re.split(r'(?<=[.!?]) +', body)
            repaired = False
            for i, sent in enumerate(sentences):
                if any(kw in sent.lower() for kw in peer_keywords):
                    sentences[i] = sent.rstrip('.!?') + f' {CITATION}.'
                    repaired = True
                    break
            if repaired:
                body = ' '.join(sentences)

        # 7. Phase K6: Engagement Validator — hard rejection on <3 levers
        lever_count, lever_names = self._check_engagement_levers(body)
        if lever_count < 3:
            logger.warning(f"Validator (K6): Engagement guard: only {lever_count} levers ({lever_names}). Need >=3. Rejecting.")
            return ""
        elif lever_count == 3:
            logger.warning(f"Validator (K6): Marginal engagement. Only 3 levers found: {lever_names}.")

        return body.strip()


    def verify_grounding(self, body: str, context_data: Dict[str, Any]) -> bool:
        """
        Heuristic to check if numbers in the body are present in the context.
        Helps prevent 'hallucinated' performance data.
        """
        # Extract all numbers from body
        body_nums = set(re.findall(r"\d+", body))
        if not body_nums:
            return True
            
        # Extract all numbers from context JSON string
        context_str = json.dumps(context_data)
        context_nums = set(re.findall(r"\d+", context_str))
        
        # If a number exists in body but not in context, it might be hallucinated
        # (Excluding small numbers like 1, 2, 7 for dates/days)
        hallucinated = [n for n in body_nums if n not in context_nums and int(n) > 10]
        
        if hallucinated:
            logger.error(f"Validator: Possible hallucination detected! Numbers: {hallucinated}")
            return False
        return True

if __name__ == "__main__":
    import json
    v = OutputValidator()
    cat = {"voice": {"vocab_taboo": ["cheap"]}}
    
    test_body = "This is a cheap offer! Visit www.magicpin.com now. Do you want it? Or do you want that?"
    print(f"Original: {test_body}")
    print(f"Validated: {v.validate(test_body, cat)}")
