"""Photo storage with a server timestamp and a content hash. OWNER: Person C.

Why the hash matters, and why you should say this in the demo: a screenshot in
someone's camera roll proves nothing about when it was taken. A file whose
SHA-256 and receipt time were recorded by the server the moment it arrived is a
record someone can rely on later.
"""

import hashlib
import os
import struct
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


def image_size(abs_file_path: str) -> tuple[int, int] | None:
    """Pixel dimensions from the file header, or None if we can't tell.

    The PDF needs explicit dimensions for every photo (see pdf.fit_box), and we
    have no image library — Pillow is not in requirements.txt and this is not the
    day to add one. JPEG and PNG cover everything a phone camera produces via the
    upload form; anything else falls back to a fixed display height.
    """
    try:
        with open(abs_file_path, "rb") as fh:
            head = fh.read(32)
            if head[:8] == b"\x89PNG\r\n\x1a\n":
                return struct.unpack(">II", head[16:24])
            if head[:3] == b"GIF":
                return struct.unpack("<HH", head[6:10])
            if head[:2] != b"\xff\xd8":
                return None
            # JPEG: walk the marker segments looking for a start-of-frame.
            fh.seek(2)
            while True:
                marker = fh.read(2)
                if len(marker) < 2 or marker[0] != 0xFF:
                    return None
                (seg_len,) = struct.unpack(">H", fh.read(2))
                if marker[1] in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7,
                                 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", fh.read(5)[1:])
                    return (w, h)
                fh.seek(seg_len - 2, 1)
    except (OSError, struct.error, ValueError):
        return None
