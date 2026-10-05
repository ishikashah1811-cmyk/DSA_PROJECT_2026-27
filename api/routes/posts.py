from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile

from ..ingest import CsvAdapter, InstagramExportAdapter
from ..schemas import ImportResult, PostOut
from ..state import AppState, get_state

router = APIRouter(prefix="/posts", tags=["posts"])


@router.post("/import", response_model=ImportResult)
async def import_posts(
    file: UploadFile = File(..., description="CSV with a caption column, or Instagram JSON"),
    account: str = Form("acc_upload", description="Account label for JSON exports; anonymized before storing"),
    followers: int | None = Form(None, ge=1, description="Follower count of that account, if known"),
    state: AppState = Depends(get_state),
) -> ImportResult:
    data = await file.read(state.settings.max_upload_mb * 1024 * 1024 + 1)
    if len(data) > state.settings.max_upload_mb * 1024 * 1024:
        raise HTTPException(413, f"file is larger than {state.settings.max_upload_mb} MB")
    name = (file.filename or "").lower()
    is_json = name.endswith(".json") or (file.content_type or "").endswith("json")
    adapter = InstagramExportAdapter(account, followers) if is_json else CsvAdapter(account)
    try:
        posts, skipped = adapter.parse(data)
    except (ValueError, UnicodeDecodeError) as e:
        raise HTTPException(422, f"could not read {file.filename or 'upload'}: {e}") from None
    imported = state.db.upsert_posts(posts, source=adapter.source)
    state.reload()
    return ImportResult(imported=imported, skipped=skipped, total_posts=state.db.count_posts())


@router.get("", response_model=list[PostOut])
def list_posts(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    state: AppState = Depends(get_state),
) -> list[PostOut]:
    return [
        PostOut(id=p.id, account=p.account, caption=p.caption, timestamp=p.timestamp, hashtags=p.hashtags,
                likes=p.likes, comments=p.comments, followers=p.followers)
        for p in state.db.list_posts(limit, offset)
    ]


@router.delete("", response_model=ImportResult)
def delete_posts(state: AppState = Depends(get_state)) -> ImportResult:
    """Remove every stored post (for resetting a demo)."""
    removed = state.db.delete_posts()
    state.reload()
    return ImportResult(imported=0, skipped=removed, total_posts=0)
