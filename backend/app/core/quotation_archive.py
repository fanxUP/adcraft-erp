"""Historical quotation reads remain available; new business writes orders."""
from fastapi import Depends, HTTPException, Request
from app.core.deps import get_current_user


async def quotation_archive_only(request: Request, current_user=Depends(get_current_user)):
    if request.method in {"GET", "HEAD", "OPTIONS"}:
        return
    path = request.url.path
    if path.startswith("/api/v1/quotes") or path.startswith("/api/v1/cdr/quotes"):
        raise HTTPException(status_code=410, detail="报价业务已停用，请直接创建或编辑订单；历史报价仍可只读查询")
