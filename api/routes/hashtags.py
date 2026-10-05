from fastapi import APIRouter, Depends, Query

from ..schemas import TagRank, TagSuggestion
from ..state import AppState, get_state

router = APIRouter(prefix="/hashtags", tags=["hashtags (Module 2)"])


@router.get("/suggest", response_model=list[TagSuggestion])
def suggest(
    prefix: str = Query("", max_length=100),
    k: int = Query(10, ge=1, le=50),
    state: AppState = Depends(get_state),
) -> list[TagSuggestion]:
    with state.lock:
        return [TagSuggestion(tag=t, count=c) for t, c in state.service.suggest(prefix, k)]


@router.get("/top", response_model=list[TagRank])
def top(
    k: int = Query(10, ge=1, le=100),
    min_count: int = Query(3, ge=1),
    m: float = Query(5.0, ge=0, description="Prior weight of the smoothed mean"),
    state: AppState = Depends(get_state),
) -> list[TagRank]:
    with state.lock:
        result = state.service.run("hashtags", k=k, min_count=min_count, m=m)
    return [TagRank(**t) for t in result.data["top"]]
