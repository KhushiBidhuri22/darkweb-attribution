from typing import Any, List, Optional
from pydantic import BaseModel, Field


# -------------------------------------------------------------
# AUTH & USER
# -------------------------------------------------------------

class User(BaseModel):
    id: str
    name: Optional[str] = None
    role: Optional[str] = "Analyst"


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    user: Optional[User] = None


class LoginResponse(BaseModel):
    user: User


# -------------------------------------------------------------
# SUGGESTIONS & SEARCH
# -------------------------------------------------------------

class SuggestionItem(BaseModel):
    label: str
    value: str
    type: str = "all"  # 'all' | 'handle' | 'wallet' | 'key'


class SuggestionsResponse(BaseModel):
    items: List[SuggestionItem]


class ActorSummary(BaseModel):
    id: str
    handle: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = "Active Review"
    confidence: Optional[float] = None
    firstSeen: Optional[str] = None
    lastSeen: Optional[str] = None


class SearchResponse(BaseModel):
    items: List[ActorSummary]


# -------------------------------------------------------------
# ACTOR WORKSPACE & 6 CHAPTERS
# -------------------------------------------------------------

class AliasItem(BaseModel):
    id: str
    handle: Optional[str] = None
    detail: Optional[str] = None
    confidence: Optional[float] = None
    nodeId: Optional[str] = None


class KeyItem(BaseModel):
    id: str
    title: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    confidence: Optional[float] = None
    nodeId: Optional[str] = None
    url: Optional[str] = None
    value: Optional[str] = None
    algorithm: Optional[str] = "RSA-4096 / PGP"


class WalletItem(BaseModel):
    id: str
    title: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    confidence: Optional[float] = None
    nodeId: Optional[str] = None
    url: Optional[str] = None
    value: Optional[str] = None
    network: Optional[str] = "Bitcoin / Monero"


class EvidenceItem(BaseModel):
    id: str
    title: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    confidence: Optional[float] = None
    nodeId: Optional[str] = None
    url: Optional[str] = None
    method: Optional[str] = "Infrastructure Correlation"


class SourceItem(BaseModel):
    id: str
    title: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    confidence: Optional[float] = None
    nodeId: Optional[str] = None
    url: Optional[str] = None
    name: Optional[str] = None
    observedAt: Optional[str] = None


class ActivityEventItem(BaseModel):
    id: str
    title: Optional[str] = None
    detail: Optional[str] = None
    source: Optional[str] = None
    date: Optional[str] = None
    confidence: Optional[float] = None
    nodeId: Optional[str] = None
    url: Optional[str] = None
    label: Optional[str] = None


# -------------------------------------------------------------
# GRAPH SCHEMAS
# -------------------------------------------------------------

class GraphNode(BaseModel):
    id: str
    name: Optional[str] = None
    type: str  # 'actor' | 'alias' | 'key' | 'wallet' | 'source'
    identifier: Optional[str] = None
    relation: Optional[str] = None
    detail: Optional[str] = None
    confidence: Optional[float] = None
    observedAt: Optional[str] = None
    recordId: Optional[str] = None
    position: Optional[List[float]] = None


class GraphEdge(BaseModel):
    id: str
    from_node: str = Field(..., alias="from")
    to_node: str = Field(..., alias="to")
    kind: Optional[str] = None
    confidence: Optional[float] = None
    observedAt: Optional[str] = None

    class Config:
        populate_by_name = True


class GraphData(BaseModel):
    nodes: List[GraphNode]
    edges: List[GraphEdge]


# -------------------------------------------------------------
# FULL ACTOR PROFILE
# -------------------------------------------------------------

class ActorDetail(BaseModel):
    id: str
    handle: Optional[str] = None
    description: Optional[str] = None
    priority: Optional[str] = "Active Review"
    confidence: Optional[float] = None
    firstSeen: Optional[str] = None
    lastSeen: Optional[str] = None
    aliases: Optional[List[AliasItem]] = None
    keys: Optional[List[KeyItem]] = None
    wallets: Optional[List[WalletItem]] = None
    evidence: Optional[List[EvidenceItem]] = None
    sources: Optional[List[SourceItem]] = None
    events: Optional[List[ActivityEventItem]] = None
    graph: Optional[GraphData] = None


class ActorDetailResponse(BaseModel):
    actor: ActorDetail


# -------------------------------------------------------------
# ATTRIBUTION & ML SCHEMAS
# -------------------------------------------------------------

class AttributionResponse(BaseModel):
    actor_1: str
    actor_2: str
    assessment: str
    confidence: float
    confidence_label: str
    score_components: dict
    evidence: List[dict]
    limitations: List[str]
