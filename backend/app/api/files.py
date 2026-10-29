"""Private, authenticated compatibility route for existing upload URLs."""
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.security import HTTPAuthorizationCredentials

from app.core.config import settings
from app.core.database import get_db
from app.core.deps import get_current_user, security_scheme
from app.core.file_security import confined_path
from app.services.file_access_service import can_read_upload

router = APIRouter(tags=["Private files"])
FILE_COOKIE = "adcraft_file_session"


def set_file_cookie(response, request, token):
    response.set_cookie(FILE_COOKIE, token, httponly=True, secure=request.url.scheme == "https",
                        samesite="strict", path="/uploads", max_age=settings.JWT_EXPIRE_MINUTES * 60)


async def file_viewer(request: Request, credentials=Depends(security_scheme), db=Depends(get_db)):
    if credentials is None:
        cookie = request.cookies.get(FILE_COOKIE)
        credentials = HTTPAuthorizationCredentials(scheme="Bearer", credentials=cookie) if cookie else None
    return await get_current_user(request, credentials, db)


@router.get("/uploads/{relative:path}")
async def private_upload(relative: str, request: Request, db=Depends(get_db), viewer=Depends(file_viewer)):
    path = Path(confined_path(settings.LOCAL_UPLOAD_DIR, relative))
    if not path.is_file() or not await can_read_upload(db, relative, viewer):
        raise HTTPException(404, "文件不存在或无权访问")
    with path.open("rb") as source:
        header = source.read(32)
    mime = "application/octet-stream"
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        mime = "image/png"
    elif header.startswith(b"\xff\xd8\xff"):
        mime = "image/jpeg"
    elif header.startswith(b"RIFF") and header[8:12] == b"WEBP":
        mime = "image/webp"
    elif header.startswith(b"%PDF-"):
        mime = "application/pdf"
    elif len(header) > 12 and header[4:8] == b"ftyp":
        mime = "video/mp4"
    return FileResponse(path, media_type=mime, filename=path.name,
        content_disposition_type="attachment" if mime == "application/octet-stream" else "inline",
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff",
                 "Content-Security-Policy": "sandbox; default-src 'none'; frame-ancestors 'self'", "Referrer-Policy": "no-referrer"})
