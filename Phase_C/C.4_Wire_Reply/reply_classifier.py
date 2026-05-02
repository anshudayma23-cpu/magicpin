import re
from typing import Dict, Any

class ReplyClassifier:
    # Patterns for common auto-replies
    AUTO_REPLY_KEYWORDS = [
        "thank you for contacting",
        "currently away",
        "busy at the moment",
        "get back to you",
        "automated message",
        "thanks for reaching out"
    ]
    
    # Patterns for simple intents
    YES_PATTERNS = [r"^yes$", r"^y$", r"^ha$", r"^ok$", r"^thik hai$", r"^done$", r"^han$", r"^agree$"]
    NO_PATTERNS = [r"^no$", r"^n$", r"^nahi$", r"^don't$", r"^stop$", r"^cancel$"]
    
    # Patterns for hostility or hard refusal
    HOSTILE_KEYWORDS = [
        "fuck", "bastard", "idiot", "fraud", "scam", 
        "don't message", "stop spamming", "unsubscribe", "remove me"
    ]

    def classify(self, message: str) -> Dict[str, Any]:
        """
        Classifies the incoming message into intent categories.
        """
        msg_clean = message.lower().strip()
        
        # 1. Check for Auto-Reply (Skip LLM)
        for kw in self.AUTO_REPLY_KEYWORDS:
            if kw in msg_clean:
                return {"intent": "auto_reply", "confidence": 1.0, "should_respond": False}
        
        # 2. Check for Hostility/Hard Refusal (End convo)
        for kw in self.HOSTILE_KEYWORDS:
            if kw in msg_clean:
                return {"intent": "hostile", "confidence": 1.0, "should_respond": True, "action": "end"}
        
        # 3. Check for Binary Yes
        for pattern in self.YES_PATTERNS:
            if re.match(pattern, msg_clean):
                return {"intent": "binary_yes", "confidence": 0.9, "should_respond": True}
                
        # 4. Check for Binary No
        for pattern in self.NO_PATTERNS:
            if re.match(pattern, msg_clean):
                return {"intent": "binary_no", "confidence": 0.9, "should_respond": True}

        # 5. Default to Complex (Requires LLM)
        return {"intent": "complex", "confidence": 0.5, "should_respond": True}

if __name__ == "__main__":
    classifier = ReplyClassifier()
    tests = [
        "Thank you for contacting Smile Dental. We are busy.",
        "Yes",
        "Thik hai",
        "No way",
        "Stop spamming me",
        "What is the exact cost of the scaling offer?"
    ]
    
    for t in tests:
        print(f"Msg: '{t}' -> {classifier.classify(t)}")
