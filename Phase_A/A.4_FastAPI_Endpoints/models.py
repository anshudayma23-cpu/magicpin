from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

# --- Sub-Models ---

class VoiceProfile(BaseModel):
    tone: str
    vocab_allowed: List[str]
    vocab_taboo: List[str]
    salutation_examples: List[str]

class OfferTemplate(BaseModel):
    id: str
    title: str
    value: str
    audience: str
    type: str

class PeerStats(BaseModel):
    avg_rating: float
    avg_ctr: float
    avg_reviews: int

class DigestItem(BaseModel):
    id: str
    kind: str
    title: str
    source: str
    summary: str

class Performance(BaseModel):
    views: int
    calls: int
    directions: int
    ctr: float
    delta_7d: Dict[str, float]

class MerchantOffer(BaseModel):
    id: str
    title: str
    status: str
    expires_at: Optional[str] = None

class CustomerIdentity(BaseModel):
    name: str
    language_pref: str
    age_band: str

class Relationship(BaseModel):
    first_visit: str
    last_visit: str
    visits_total: int
    services: List[str]
    ltv_estimate: Optional[float] = None

# --- Main Context Models ---

class CategoryContext(BaseModel):
    slug: str
    voice: VoiceProfile
    offer_catalog: List[OfferTemplate]
    peer_stats: PeerStats
    digest: List[DigestItem]
    seasonal_beats: Optional[List[Dict[str, Any]]] = None
    trend_signals: Optional[List[Dict[str, Any]]] = None

class MerchantContext(BaseModel):
    merchant_id: str
    category_slug: str
    identity: Dict[str, Any] # name, city, owner_first_name, etc.
    subscription: Dict[str, Any]
    performance: Performance
    offers: List[MerchantOffer]
    signals: List[str]
    review_themes: List[Dict[str, Any]]
    conversation_history: List[Dict[str, Any]] = []

class TriggerContext(BaseModel):
    id: str
    scope: str # "merchant" or "customer"
    kind: str
    source: str
    merchant_id: str
    customer_id: Optional[str] = None
    payload: Dict[str, Any]
    urgency: int
    suppression_key: str
    expires_at: str

class CustomerContext(BaseModel):
    customer_id: str
    merchant_id: str
    identity: CustomerIdentity
    relationship: Relationship
    state: str
    preferences: Dict[str, Any]
    consent: Dict[str, Any]

# --- API Request/Response Models ---

class ContextPushRequest(BaseModel):
    scope: str
    context_id: str
    version: int
    payload: Dict[str, Any]
    delivered_at: str

class TickRequest(BaseModel):
    now: str
    available_triggers: List[str]

class ReplyRequest(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    from_role: str
    message: str
    received_at: str
    turn_number: int

class TickAction(BaseModel):
    conversation_id: str
    merchant_id: str
    customer_id: Optional[str] = None
    send_as: str # "vera" or "merchant_on_behalf"
    trigger_id: str
    template_name: str
    template_params: List[str]
    body: str
    cta: str
    suppression_key: str
    rationale: str

class TickResponse(BaseModel):
    actions: List[TickAction]

class ReplyResponse(BaseModel):
    action: str # "send", "wait", "end"
    body: Optional[str] = None
    cta: Optional[str] = None
    wait_seconds: Optional[int] = None
    rationale: str
