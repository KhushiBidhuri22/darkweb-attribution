from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Actor(Base):
    __tablename__ = "actors"

    id = Column(Integer, primary_key=True, index=True)
    primary_handle = Column(String, nullable=False)
    confidence = Column(Float, default=0.0)
    last_seen = Column(DateTime, default=datetime.utcnow)

    # One actor → many identifiers
    identifiers = relationship("Identifier", back_populates="actor")

class Identifier(Base):
    __tablename__ = "identifiers"

    id = Column(Integer, primary_key=True, index=True)
    actor_id = Column(Integer, ForeignKey("actors.id"))
    type = Column(String)  # "handle", "pgp_key", "wallet"
    value = Column(String)

    # Many identifiers → one actor
    actor = relationship("Actor", back_populates="identifiers")

class Post(Base):
    __tablename__ = "posts"

    id = Column(Integer, primary_key=True, index=True)
    source = Column(String)          # e.g. "forum_x", "market_y"
    handle = Column(String)          # username/handle used in the post
    pgp_key = Column(String, nullable=True)
    wallet = Column(String, nullable=True)
    text = Column(String)            # post content
    timestamp = Column(DateTime, default=datetime.utcnow)