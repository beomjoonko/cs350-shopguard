"""Validate uploaded evidence images."""
from fastapi import HTTPException, UploadFile, status

from app.config import settings

_ALLOWED_TYPES = frozenset(
    {"image/jpeg", "image/png", "image/webp", "image/gif"}
)


async def read_validated_evidence(file: UploadFile) -> tuple[bytes, str, str]:
    content_type = (file.content_type or "").split(";")[0].strip().lower()
    if content_type not in _ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Evidence must be a JPEG, PNG, WebP, or GIF image",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Evidence file is empty")
    if len(data) > settings.EVIDENCE_MAX_BYTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Evidence image must be at most {settings.EVIDENCE_MAX_BYTES // (1024 * 1024)}MB",
        )

    filename = file.filename or "evidence"
    return data, content_type, filename
