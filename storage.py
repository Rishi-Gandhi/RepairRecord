"""Photo storage with a server timestamp and a content hash. OWNER: Person C.

Why the hash matters, and why you should say this in the demo: a screenshot in
someone's camera roll proves nothing about when it was taken. A file whose
SHA-256 and receipt time were recorded by the server the moment it arrived is a
record someone can rely on later.
"""

import hashlib
import os
import uuid

import db

UPLOAD_DIR = os.environ.get("REPAIRRECORD_UPLOADS", "uploads")


def save_photo(content: bytes, original_name: str) -> dict:
    os.makedirs(UPLOAD_DIR, exist_ok=True)
    ext = os.path.splitext(original_name)[1].lower() or ".jpg"
    if ext not in {".jpg", ".jpeg", ".png", ".webp", ".heic"}:
        ext = ".jpg"
    photo_id = f"ph_{uuid.uuid4().hex[:10]}"
    filename = f"{photo_id}{ext}"
    path = os.path.join(UPLOAD_DIR, filename)
    with open(path, "wb") as fh:
        fh.write(content)
    return {
        "id": photo_id,
        "path": f"/uploads/{filename}",
        "captured_at": db.now_iso(),
        "sha256": hashlib.sha256(content).hexdigest(),
    }


def abs_path(web_path: str) -> str:
    """'/uploads/x.jpg' -> absolute path on disk (the PDF renderer needs this)."""
    return os.path.abspath(os.path.join(UPLOAD_DIR, os.path.basename(web_path)))
