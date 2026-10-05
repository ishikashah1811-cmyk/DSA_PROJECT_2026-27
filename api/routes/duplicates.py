from fastapi import APIRouter, Depends, HTTPException, Query

from ..schemas import Cluster, DuplicateRunRequest, DuplicateRunSummary
from ..state import AppState, get_state

router = APIRouter(prefix="/duplicates", tags=["duplicates (Module 1)"])


@router.post("/run", response_model=DuplicateRunSummary)
def run_duplicates(body: DuplicateRunRequest | None = None, state: AppState = Depends(get_state)) -> DuplicateRunSummary:
    params = (body or DuplicateRunRequest()).model_dump()
    with state.lock:
        try:
            result = state.service.run("duplicates", **params)
        except ValueError as e:  # e.g. bands * rows != num_hashes
            raise HTTPException(422, str(e)) from None
    data = {**result.data, "runtime_ms": result.runtime_ms}
    run_id = state.db.save_run("duplicates", result.params, data)
    return DuplicateRunSummary(run_id=run_id, **{f: data[f] for f in DuplicateRunSummary.model_fields if f != "run_id"})


@router.get("/clusters", response_model=list[Cluster])
def clusters(
    run_id: int | None = Query(None, description="Defaults to the latest run"),
    state: AppState = Depends(get_state),
) -> list[Cluster]:
    run = state.db.get_run(run_id) if run_id is not None else state.db.latest_run("duplicates")
    if run is None or run["module"] != "duplicates":
        raise HTTPException(404, "no such duplicates run; POST /api/duplicates/run first")
    return [Cluster(**c) for c in run["result"]["clusters"]]
