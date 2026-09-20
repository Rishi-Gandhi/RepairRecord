"""Evidence packet PDF. OWNER: Person C. This is the demo's closer.

Renders templates/packet.html and converts it with xhtml2pdf.

WHY xhtml2pdf AND NOT WeasyPrint: WeasyPrint gives nicer CSS but needs system
libraries (pango, cairo) that are a 20-minute yak-shave on a fresh Mac and a
deploy-time failure on Render. xhtml2pdf is pure pip. On a 6-hour clock, "installs
with one command on three different laptops" beats "prettier box model." If you
finish early and want the upgrade, swap the render() body — the template is
deliberately simple CSS that works in both.
"""

from io import BytesIO

from xhtml2pdf import pisa

import storage

# Printable area inside the @page margins in packet.html (letter, 0.85in sides).
CONTENT_WIDTH_IN = 6.8
# Ceiling on one photo so it can never swallow a whole page, and so two photos
# plus their captions still fit together.
MAX_PHOTO_HEIGHT_IN = 3.4
# Used when we can't read the image header: height alone still preserves the
# aspect ratio in xhtml2pdf, we just can't guarantee the width.
FALLBACK_PHOTO_HEIGHT_IN = 3.2

CATEGORY_LABELS = {
    "hvac": "Heating / cooling (HVAC)",
    "plumbing": "Plumbing",
    "electrical": "Electrical",
    "pest": "Pest infestation",
    "mold": "Mold",
    "structural": "Structural",
    "appliance": "Appliance",
    "lock_security": "Locks / security",
    "cosmetic": "Cosmetic",
    "other": "Other",
}


def category_label(category: str | None) -> str:
    """'lock_security' -> 'Locks / security'. Unknown values still read as prose."""
    if not category:
        return "Uncategorized"
    return CATEGORY_LABELS.get(category, category.replace("_", " ").capitalize())


def fit_box(size: tuple[int, int] | None) -> str:
    """CSS sizing for one photo, scaled to fit the content box.

    xhtml2pdf does not honour `max-width`/`max-height` the way a browser does — a
    portrait phone photo set to `max-width: 100%` renders taller than the page and
    overflows. Explicit width and height are respected, so we compute them here.
    Images are never scaled up past their natural size at 96dpi.
    """
    if not size or size[0] <= 0 or size[1] <= 0:
        return f"height:{FALLBACK_PHOTO_HEIGHT_IN}in"
    nat_w_in, nat_h_in = size[0] / 96, size[1] / 96
    scale = min(CONTENT_WIDTH_IN / nat_w_in, MAX_PHOTO_HEIGHT_IN / nat_h_in, 1.0)
    return f"width:{nat_w_in * scale:.2f}in;height:{nat_h_in * scale:.2f}in"


def prepare_photos(photos: list[dict]) -> list[dict]:
    """Give each photo the absolute path and explicit size the renderer needs."""
    for photo in photos:
        photo["abs_path"] = storage.abs_path(photo["path"])
        photo["img_style"] = fit_box(storage.image_size(photo["abs_path"]))
    return photos


def render(html: str) -> bytes:
    out = BytesIO()
    result = pisa.CreatePDF(src=html, dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError("PDF generation failed")
    return out.getvalue()
