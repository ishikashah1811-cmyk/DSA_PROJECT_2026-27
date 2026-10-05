from fastapi import APIRouter, Depends

from ..schemas import Health
from ..state import AppState, get_state

router = APIRouter(tags=["health"])


@router.get("/health", response_model=Health)
def health(state: AppState = Depends(get_state)) -> Health:
    return Health(status="ok", posts=len(state.service.posts))
