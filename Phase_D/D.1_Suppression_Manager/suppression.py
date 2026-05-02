from typing import Set
from threading import Lock

class SuppressionManager:
    def __init__(self):
        self._fired_keys: Set[str] = set()
        self._opted_out_merchants: Set[str] = set()
        self._lock = Lock()

    def is_suppressed(self, suppression_key: str) -> bool:
        """Checks if a trigger event has already been handled."""
        if not suppression_key:
            return False
        with self._lock:
            return suppression_key in self._fired_keys

    def mark_fired(self, suppression_key: str):
        """Records that a trigger event was successfully processed."""
        if not suppression_key:
            return
        with self._lock:
            self._fired_keys.add(suppression_key)

    def opt_out_merchant(self, merchant_id: str):
        """Blacklists a merchant from future proactive triggers."""
        with self._lock:
            self._opted_out_merchants.add(merchant_id)

    def is_merchant_opted_out(self, merchant_id: str) -> bool:
        """Checks if the merchant has requested to stop messaging."""
        with self._lock:
            return merchant_id in self._opted_out_merchants

    def clear(self):
        """Resets all suppression state."""
        with self._lock:
            self._fired_keys.clear()
            self._opted_out_merchants.clear()

# Global instance
suppression_manager = SuppressionManager()
