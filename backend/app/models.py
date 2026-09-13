from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from .database import Base


class Actor(Base):
    __tablename__ = "actors"

    actor_id = Column(String(20), primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    identifiers = relationship("Identifier", back_populates="actor", lazy="selectin")
    posts = relationship("Post", back_populates="actor", lazy="selectin")
    observations = relationship("Observation", back_populates="actor", lazy="selectin")
    infrastructure = relationship("Infrastructure", back_populates="actor", lazy="selectin")
    activity_timeline = relationship("ActivityTimeline", back_populates="actor", lazy="selectin")


class Source(Base):
    __tablename__ = "sources"

    source_id = Column(String(20), primary_key=True, index=True)
    source_name = Column(Text, nullable=False)
    source_type = Column(String(50))
    source_category = Column(String(100))
    source_url = Column(Text)
    collection_method = Column(String(100))
    first_seen = Column(DateTime(timezone=True))
    last_checked = Column(DateTime(timezone=True))
    reliability_score = Column(Float)
    status = Column(String(30))
    description = Column(Text)


class Observation(Base):
    __tablename__ = "observations"

    observation_id = Column(String(20), primary_key=True, index=True)
    source_id = Column(String(20), ForeignKey("sources.source_id"), nullable=False, index=True)
    actor_id = Column(String(20), ForeignKey("actors.actor_id"), nullable=True, index=True)
    handle = Column(Text)
    content = Column(Text)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    pgp_key = Column(Text)
    wallet_address = Column(Text)
    domain = Column(Text)
    url = Column(Text)
    category = Column(String(100))
    language = Column(String(20))
    observation_type = Column(String(50))
    confidence = Column(Float)
    first_seen = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))

    actor = relationship("Actor", back_populates="observations")
    source = relationship("Source")


class Post(Base):
    __tablename__ = "posts"

    post_id = Column(String(20), primary_key=True, index=True)
    actor_id = Column(String(20), ForeignKey("actors.actor_id"), nullable=False, index=True)
    handle = Column(Text)
    source_id = Column(String(20), ForeignKey("sources.source_id"), nullable=False, index=True)
    content = Column(Text)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    language = Column(String(20))
    category = Column(String(50))
    reply_count = Column(Integer, default=0)
    parent_post_id = Column(String(20), ForeignKey("posts.post_id"), nullable=True)
    sentiment_score = Column(Float)
    word_count = Column(Integer)
    avg_sentence_length = Column(Float)
    punctuation_ratio = Column(Float)
    technical_term_ratio = Column(Float)
    repeated_phrase_flag = Column(Boolean)

    actor = relationship("Actor", back_populates="posts")
    source = relationship("Source")


class Identifier(Base):
    __tablename__ = "identifiers"

    identifier_id = Column(String(20), primary_key=True, index=True)
    actor_id = Column(String(20), ForeignKey("actors.actor_id"), nullable=False, index=True)
    identifier_type = Column(String(50), nullable=False)
    identifier_value = Column(Text, nullable=False, index=True)
    source_id = Column(String(20), ForeignKey("sources.source_id"), nullable=False)
    first_seen = Column(DateTime(timezone=True))
    last_seen = Column(DateTime(timezone=True))
    confidence = Column(Float)
    status = Column(String(50))
    observation_id = Column(String(20), ForeignKey("observations.observation_id"), nullable=True)

    actor = relationship("Actor", back_populates="identifiers")
    source = relationship("Source")


class Infrastructure(Base):
    __tablename__ = "infrastructure"

    indicator_id = Column(String(20), primary_key=True, index=True)
    actor_id = Column(String(20), ForeignKey("actors.actor_id"), nullable=True, index=True)
    indicator_type = Column(String(100))
    indicator_value = Column(Text, nullable=False, index=True)
    source_id = Column(String(20), ForeignKey("sources.source_id"), nullable=False)
    observed_at = Column(DateTime(timezone=True))
    indicator_detail = Column(Text)
    match_target = Column(String(100))
    confidence = Column(Float)
    status = Column(String(30))
    evidence_id = Column(String(30))

    actor = relationship("Actor", back_populates="infrastructure")
    source = relationship("Source")


class WalletTransaction(Base):
    __tablename__ = "wallet_transactions"

    transaction_id = Column(String(20), primary_key=True, index=True)
    from_wallet = Column(Text, nullable=False, index=True)
    to_wallet = Column(Text, nullable=False, index=True)
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    amount = Column(Float)
    currency = Column(String(20))
    transaction_type = Column(String(50))
    source_id = Column(String(20), ForeignKey("sources.source_id"), nullable=True)
    confidence = Column(Float)
    actor_from = Column(String(20), ForeignKey("actors.actor_id"), nullable=True)
    actor_to = Column(String(20), ForeignKey("actors.actor_id"), nullable=True)
    transaction_cluster = Column(String(100))
    risk_signal = Column(String(20))

    source = relationship("Source")


class ActivityTimeline(Base):
    __tablename__ = "activity_timeline"

    event_id = Column(String(20), primary_key=True, index=True)
    actor_id = Column(String(20), ForeignKey("actors.actor_id"), nullable=False, index=True)
    handle = Column(Text)
    event_type = Column(String(50))
    event_timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    source_id = Column(String(20), ForeignKey("sources.source_id"), nullable=False)
    description = Column(Text)
    event_metadata = Column("metadata", JSONB)
    confidence = Column(Float)

    actor = relationship("Actor", back_populates="activity_timeline")
    source = relationship("Source")


class Relationship(Base):
    __tablename__ = "relationships"

    relationship_id = Column(String(20), primary_key=True, index=True)
    source_entity_type = Column(String(50), nullable=False)
    source_entity_id = Column(String(100), nullable=False)
    relationship_type = Column(String(100), nullable=False, index=True)
    target_entity_type = Column(String(50), nullable=False)
    target_entity_id = Column(String(100), nullable=False)
    source_id = Column(String(20), ForeignKey("sources.source_id"), nullable=False)
    event_timestamp = Column(DateTime(timezone=True), nullable=False)
    confidence = Column(Float)
    evidence_id = Column(String(30))
    relationship_status = Column(String(30))

    source = relationship("Source")
