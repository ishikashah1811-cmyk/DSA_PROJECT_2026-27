import json

from fastapi import APIRouter, Depends, HTTPException

from ..schemas import BenchmarkRow
from ..state import AppState, get_state

router = APIRouter(tags=["benchmark"])


@router.get("/benchmark", response_model=list[BenchmarkRow])
def benchmark(state: AppState = Depends(get_state)) -> list[BenchmarkRow]:
    """LSH vs brute-force results recorded by engine/benchmarks/report.py."""
    path = state.settings.benchmark_path
    if not path.exists():
        raise HTTPException(404, "no benchmark results; run engine/benchmarks/report.py")
    return [BenchmarkRow(**row) for row in json.loads(path.read_text())]
