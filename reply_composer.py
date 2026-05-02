import json
import logging
from typing import List, Dict, Any, Optional
from llm_client import call_llm

logger = logging.getLogger("vera.reply_composer")

REPLY_SYSTEM_PROMPT = """
You are Vera, the merchant AI assistant. You are in a multi-turn conversation with a merchant ({owner_name}).

### CONTEXT:
Category: {category_slug}
Voice Tone: {voice_tone}
Merchant Performance: {performance}

### RULES:
1. **Consistency**: Maintain the same voice and data-driven approach as the opening message.
2. **Conciseness**: Keep replies under 50 words.
3. **Intent Detection**: 
   - If they say "Yes/Ok/Go ahead" or the intent is 'binary_yes' or 'intent_transition', use ACTION words like 'Done', 'Proceeding', 'Drafted', or 'Scheduled'. Be decisive.
   - If they ask a question, answer it using ONLY the provided data.
   - If they are hostile or say "Stop", set action to "end".
4. **No URLs**: Never include links.

### OUTPUT FORMAT:
{{
  "action": "send | wait | end",
  "body": "Your response message",
  "cta": "binary_yes_no | none",
  "rationale": "Why you chose this response based on the latest reply."
}}
"""

class ReplyComposer:
    async def compose_reply(
        self,
        category: Dict[str, Any],
        merchant: Dict[str, Any],
        history: List[Dict[str, str]],
        latest_message: str
    ) -> Optional[Dict[str, Any]]:
        """
        Generates a contextual reply based on the full conversation history.
        """
        # 1. Build System Prompt
        voice = category.get("voice", {})
        identity = merchant.get("identity", {})
        
        system_prompt = REPLY_SYSTEM_PROMPT.format(
            owner_name=identity.get("owner_first_name", "Merchant"),
            category_slug=category.get("slug", "merchant"),
            voice_tone=voice.get("tone", "professional"),
            performance=json.dumps(merchant.get("performance", {}))
        )
        
        # 2. Build User Prompt (History + Latest Message)
        # We pass the history as part of the messages in the LLM client usually,
        # but here we'll prepare a structured string or just let the client handle it.
        # For our client, we'll append history to the user prompt for simplicity.
        history_str = "\n".join([f"{m['role']}: {m['content']}" for m in history])
        user_prompt = f"CONVERSATION HISTORY:\n{history_str}\n\nLATEST REPLY: {latest_message}\n\nRespond now."
        
        # 3. Call LLM
        raw_response = await call_llm(system_prompt, user_prompt)
        if not raw_response:
            return None
            
        try:
            # Simple JSON extraction
            import re
            json_match = re.search(r"\{.*\}", raw_response, re.DOTALL)
            clean_json = json_match.group(0) if json_match else raw_response
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Reply parsing failed: {str(e)}")
            return None
