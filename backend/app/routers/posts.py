from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Post

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("")
def list_posts(
    limit: int = Query(50, ge=1, le=200),
    actor_id: str = Query(None),
    db: Session = Depends(get_db),
):
    query = db.query(Post)
    if actor_id:
        query = query.filter(Post.actor_id == actor_id)
    posts = query.order_by(Post.event_timestamp.desc()).limit(limit).all()

    return [
        {
            "post_id": p.post_id,
            "actor_id": p.actor_id,
            "handle": p.handle,
            "source_id": p.source_id,
            "content": p.content,
            "timestamp": p.event_timestamp.isoformat() if p.event_timestamp else None,
            "category": p.category,
            "sentiment_score": p.sentiment_score,
            "reply_count": p.reply_count,
        }
        for p in posts
    ]


@router.get("/{post_id}")
def get_post(post_id: str, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.post_id == post_id).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    return {
        "post_id": post.post_id,
        "actor_id": post.actor_id,
        "handle": post.handle,
        "source_id": post.source_id,
        "content": post.content,
        "timestamp": post.event_timestamp.isoformat() if post.event_timestamp else None,
        "category": post.category,
        "language": post.language,
        "reply_count": post.reply_count,
        "sentiment_score": post.sentiment_score,
        "word_count": post.word_count,
        "avg_sentence_length": post.avg_sentence_length,
        "punctuation_ratio": post.punctuation_ratio,
        "technical_term_ratio": post.technical_term_ratio,
    }