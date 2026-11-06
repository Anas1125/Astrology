"""Authenticated local Vastu floor-plan review endpoint."""
from __future__ import annotations
import json
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from app.api.routes import current_user
from app.models.entities import User
from app.services.vastu import NORTH_SIDES, analyze_vastu_rooms
router = APIRouter(tags=["Vastu"])
MAX_IMAGE_BYTES = 10 * 1024 * 1024
_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp"}

def _valid_image_signature(content: bytes, content_type: str) -> bool:
    if content_type == "image/png": return content.startswith(b"\x89PNG\r\n\x1a\n")
    if content_type == "image/jpeg": return content.startswith(b"\xff\xd8\xff")
    if content_type == "image/webp": return len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP"
    return False

@router.post("/vastu/analyze")
async def analyze_vastu_floor_plan(
    file: UploadFile = File(...), north_side: str = Form(...), rooms: str = Form(...),
    boundary: str = Form(...), user: User = Depends(current_user),
):
    """Validate the uploaded image in memory and review user-marked positions."""
    del user
    content_type = (file.content_type or "").split(";", 1)[0].strip().lower()
    if content_type not in _ALLOWED_IMAGE_TYPES:
        raise HTTPException(415, "Upload a PNG, JPG or WebP floor-plan image.")
    image_bytes = await file.read(MAX_IMAGE_BYTES + 1)
    if not image_bytes: raise HTTPException(400, "The uploaded floor-plan image is empty.")
    if len(image_bytes) > MAX_IMAGE_BYTES: raise HTTPException(413, "Floor-plan images must be 10 MB or smaller.")
    if not _valid_image_signature(image_bytes, content_type):
        raise HTTPException(415, "The image file is invalid or does not match its image type.")
    if north_side not in NORTH_SIDES: raise HTTPException(422, "Choose which edge of the floor plan points north.")
    if not rooms or len(rooms) > 12000: raise HTTPException(422, "Mark at least one room on the floor plan.")
    if not boundary or len(boundary) > 3000: raise HTTPException(422, "Mark all four outer corners of the building boundary.")
    try:
        room_markers=json.loads(rooms)
        boundary_points=json.loads(boundary)
    except json.JSONDecodeError as exc:
        raise HTTPException(422, "Room markers or building boundary could not be read.") from exc
    try:
        return analyze_vastu_rooms(room_markers, north_side, boundary_points)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
