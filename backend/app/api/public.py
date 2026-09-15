"""Unauthenticated, non-sensitive application metadata."""

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db
from app.schemas.common import success
from app.services.branding_service import get_branding, public_branding_payload

router = APIRouter(prefix="/public", tags=["Public"])


@router.get("/branding")
async def get_public_branding(db: AsyncSession = Depends(get_db)):
    branding = await get_branding(db)
    return success(public_branding_payload(settings.APP_NAME, branding))


@router.get("/branding/logo")
async def get_public_logo(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    branding = await get_branding(db)
    if not branding or not branding.logo_data or not branding.logo_content_type:
        raise HTTPException(status_code=404, detail="logo 未配置")

    etag = f'"system-branding-{int(branding.logo_version or 0)}"'
    headers = {
        "Cache-Control": "public, max-age=300",
        "ETag": etag,
        "Content-Disposition": "inline",
    }
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return Response(
        content=bytes(branding.logo_data),
        media_type=branding.logo_content_type,
        headers=headers,
    )
