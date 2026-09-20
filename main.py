"""RepairRecord — routes and app wiring. OWNER: Person C.

Keep this file thin. Logic belongs in ai.py (B), letter.py (B), pdf.py / db.py (C).
Run:  uvicorn main:app --reload
"""

import os

from fastapi import FastAPI, Form, Request, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

import ai
import db
import letter
import pdf
import storage

app = FastAPI(title="RepairRecord")
templates = Jinja2Templates(directory="templates")
templates.env.filters["days_remaining"] = letter.days_remaining
templates.env.filters["wrap"] = letter.wrap_for_print
templates.env.filters["category"] = pdf.category_label

os.makedirs(storage.UPLOAD_DIR, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=storage.UPLOAD_DIR), name="uploads")
app.mount("/static", StaticFiles(directory="static"), name="static")


@app.on_event("startup")
def _startup() -> None:
    db.init_db()


# ---------------------------------------------------------------- capture ----

@app.get("/", response_class=HTMLResponse)
def capture_page(request: Request):
    return templates.TemplateResponse(request, "capture.html", {})


@app.post("/issues")
async def create_issue(
    description: str = Form(...),
    tenant_name: str = Form(""),
    tenant_contact: str = Form(""),
    unit_address: str = Form(""),
    landlord_name: str = Form(""),
    landlord_address: str = Form(""),
    photo: UploadFile | None = File(None),
):
    photos = []
    photo_bytes = None
    if photo is not None and photo.filename:
        photo_bytes = await photo.read()
        if photo_bytes:
            photos.append(storage.save_photo(photo_bytes, photo.filename))

    issue = {
        "id": db.new_id(),
        "created_at": db.now_iso(),
        "tenant_name": tenant_name,
        "tenant_contact": tenant_contact,
        "unit_address": unit_address,
        "landlord_name": landlord_name,
        "landlord_address": landlord_address,
        "description": description,
        "photos": photos,
        "classification": ai.classify(photo_bytes, description),
        "notice": {
            "letter_text": None, "generated_at": None,
            "delivery_method": None, "sent_at": None, "cure_deadline": None,
        },
        "events": [],
    }
    db.add_event(issue, "reported", "Issue documented in RepairRecord")
    db.save(issue)
    return RedirectResponse(f"/issues/{issue['id']}", status_code=303)


# ------------------------------------------------------------------ views ----

@app.get("/issues", response_class=HTMLResponse)
def list_issues(request: Request):
    return templates.TemplateResponse(
        request, "list.html", {"issues": db.list_all()}
    )


@app.get("/issues/{issue_id}", response_class=HTMLResponse)
def issue_detail(request: Request, issue_id: str):
    issue = db.get(issue_id)
    if not issue:
        return HTMLResponse("Not found", status_code=404)
    return templates.TemplateResponse(
        request, "detail.html",
        {"issue": issue, "delivery_methods": letter.DELIVERY_METHODS},
    )


# ------------------------------------------------------------ state changes --

@app.post("/issues/{issue_id}/notice")
def generate_notice(issue_id: str):
    issue = db.get(issue_id)
    if not issue:
        return HTMLResponse("Not found", status_code=404)
    # Idempotent: a double-click must not append a second drafting event, and a
    # delivered notice must keep the exact text that was delivered.
    if issue["notice"]["letter_text"]:
        return RedirectResponse(f"/issues/{issue_id}", status_code=303)
    issue["notice"]["letter_text"] = ai.draft_notice(issue)
    issue["notice"]["generated_at"] = db.now_iso()
    db.add_event(issue, "notice_generated", "7-day notice drafted")
    db.save(issue)
    return RedirectResponse(f"/issues/{issue_id}", status_code=303)


@app.post("/issues/{issue_id}/sent")
def mark_sent(issue_id: str, delivery_method: str = Form(...)):
    issue = db.get(issue_id)
    if not issue:
        return HTMLResponse("Not found", status_code=404)
    # The cure clock starts on first delivery and never restarts — re-submitting
    # must not push the deadline later or duplicate the delivery event.
    if issue["notice"]["sent_at"]:
        return RedirectResponse(f"/issues/{issue_id}", status_code=303)
    sent_at = db.now_iso()
    issue["notice"]["delivery_method"] = delivery_method
    issue["notice"]["sent_at"] = sent_at
    issue["notice"]["cure_deadline"] = letter.cure_deadline(sent_at)
    # Re-render so the letter's footer records how it was delivered.
    issue["notice"]["letter_text"] = ai.draft_notice(issue)
    db.add_event(issue, "notice_sent", f"Notice delivered — {delivery_method}")
    db.save(issue)
    return RedirectResponse(f"/issues/{issue_id}", status_code=303)


# ------------------------------------------------------------------- packet --

@app.get("/issues/{issue_id}/packet.pdf")
def packet(request: Request, issue_id: str):
    issue = db.get(issue_id)
    if not issue:
        return HTMLResponse("Not found", status_code=404)
    pdf.prepare_photos(issue.get("photos", []))
    html = templates.get_template("packet.html").render(
        issue=issue, generated_at=db.now_iso(), statute=letter.STATUTE_SUMMARY
    )
    return Response(
        content=pdf.render(html),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="repairrecord_{issue_id}.pdf"'},
    )
