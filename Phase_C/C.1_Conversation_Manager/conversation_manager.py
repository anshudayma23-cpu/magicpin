from typing import List, Dict, Any, Optional
from threading import Lock
import time

class Message:
    def __init__(self, role: str, content: str):
        self.role = role # "vera" or "merchant" or "customer"
        self.content = content
        self.timestamp = time.time()

class Conversation:
    def __init__(self, conversation_id: str):
        self.conversation_id = conversation_id
        self.history: List[Message] = []
        self.last_updated = time.time()
        self.metadata: Dict[str, Any] = {}

class ConversationManager:
    def __init__(self, max_history: int = 10):
        self._conversations: Dict[str, Conversation] = {}
        self._lock = Lock()
        self.max_history = max_history

    def add_message(self, conversation_id: str, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        """
        Adds a message to the history and prunes old messages if limit exceeded.
        """
        with self._lock:
            if conversation_id not in self._conversations:
                self._conversations[conversation_id] = Conversation(conversation_id)
            
            conv = self._conversations[conversation_id]
            conv.history.append(Message(role, content))
            conv.last_updated = time.time()
            
            if metadata:
                conv.metadata.update(metadata)
            
            # Prune to last N turns
            if len(conv.history) > self.max_history:
                conv.history = conv.history[-self.max_history:]

    def get_history(self, conversation_id: str) -> List[Dict[str, str]]:
        """
        Returns history in OpenAI-style message list format.
        """
        with self._lock:
            conv = self._conversations.get(conversation_id)
            if not conv:
                return []
            
            return [
                {"role": "assistant" if msg.role == "vera" else "user", "content": msg.content}
                for msg in conv.history
            ]

    def get_turn_count(self, conversation_id: str) -> int:
        with self._lock:
            conv = self._conversations.get(conversation_id)
            return len(conv.history) if conv else 0

    def clear(self, conversation_id: str):
        with self._lock:
            if conversation_id in self._conversations:
                del self._conversations[conversation_id]

# Global instance
conversation_manager = ConversationManager()
