from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas import SearchResponse, SuggestionsResponse
from ..services.actor_service import get_suggestions, search_actors

router = APIRouter(tags=["search"])


@router.get("/suggestions", response_model=SuggestionsResponse)
def suggestions_endpoint(db: Session = Depends(get_db)):
    """
    Return suggestion options for the Try dropdown.
    """
    items = get_suggestions(db)
    return {"items": items}


@router.get("/search", response_model=SearchResponse)
def search_endpoint(
    q: str = Query("", description="Search query string"),
    type: str = Query("all", description="Identifier type filter (all, handle, wallet, key)"),
    db: Session = Depends(get_db),
):
    """
    Search across actors, identifiers, posts, and infrastructure.
    """
    results = search_actors(q=q, search_type=type, db=db)
    return {"items": results}