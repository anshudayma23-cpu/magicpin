import time
from typing import Dict, Any, Tuple, Optional, List
from threading import Lock

class ContextEntry:
    def __init__(self, version: int, payload: Dict[str, Any]):
        self.version = version
        self.payload = payload
        self.stored_at = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())

class ContextStore:
    def __init__(self):
        # Key: (scope, context_id) -> ContextEntry
        self._store: Dict[Tuple[str, str], ContextEntry] = {}
        self._lock = Lock()

    def upsert(self, scope: str, context_id: str, version: int, payload: Dict[str, Any]) -> Tuple[bool, Any]:
        """
        Atomically updates the context if the new version is strictly greater.
        Returns (accepted: bool, detail: ack_id or current_version)
        """
        key = (scope, context_id)
        
        with self._lock:
            existing = self._store.get(key)
            
            # Idempotency check: Reject if the incoming version is strictly less than existing
            if existing and existing.version > version:
                return False, existing.version
            
            # Create or update entry
            self._store[key] = ContextEntry(version, payload)
            ack_id = f"ack_{scope}_{context_id}_v{version}"
            return True, ack_id

    def get(self, scope: str, context_id: str) -> Optional[ContextEntry]:
        """Retrieves a single context entry."""
        return self._store.get((scope, context_id))

    def get_all_by_scope(self, scope: str) -> List[ContextEntry]:
        """Retrieves all entries for a specific scope (e.g., all 'merchant' contexts)."""
        return [entry for (s, cid), entry in self._store.items() if s == scope]

    def counts(self) -> Dict[str, int]:
        """Returns a summary of loaded contexts by scope."""
        summary = {"category": 0, "merchant": 0, "customer": 0, "trigger": 0}
        for (scope, cid) in self._store.keys():
            if scope in summary:
                summary[scope] += 1
        return summary

    def clear(self):
        """Resets the store."""
        with self._lock:
            self._store.clear()


# Global instance for the application
context_store = ContextStore()
