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


def render(html: str) -> bytes:
    out = BytesIO()
    result = pisa.CreatePDF(src=html, dest=out, encoding="utf-8")
    if result.err:
        raise RuntimeError("PDF generation failed")
    return out.getvalue()
