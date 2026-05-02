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

        # 3. Single CTA Enforcement
        # If there are multiple question marks or imperative sentences, 
        # we try to keep only the last one.
        sentences = re.split(r"(?<=[.!?]) +", body)
        if len(sentences) > 1:
            questions = [s for s in sentences if "?" in s]
            if len(questions) > 1:
                logger.warning("Validator: Multiple CTAs detected. Pruning to final question.")
                # Keep all non-questions, plus the final question
                new_sentences = [s for s in sentences if "?" not in s]
                new_sentences.append(questions[-1])
                body = " ".join(new_sentences)

        # 4. Length Guard (Max 500 chars)
        if len(body) > 500:
            logger.warning("Validator: Message too long. Truncating.")
            body = body[:497] + "..."

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
