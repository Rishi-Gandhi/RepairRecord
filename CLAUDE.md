# CLAUDE.md — RepairRecord

Context for Claude Code / AI assistants working in this repo. Read before editing.

## What this is

A hackathon project (CityCamp Gainesville, General Civic Tech track, 6-hour build,
submission 5:00 PM). A renter photographs a repair problem; the app records it with a
server timestamp and content hash, drafts the written 7-day notice **Fla. Stat.
§83.56(1)** requires, tracks the cure deadline, and exports a PDF evidence packet.

**It is documentation and a template, not legal advice.** Every surface says so. Do not
remove those disclaimers or the legal-aid referrals.

## Stack

FastAPI · Jinja2 templates · Tailwind via CDN · SQLite · xhtml2pdf · Gemini
(`google-genai`). One process, one deploy. No React, no separate API, no build step.

## Commands

```bash
pip install -r requirements.txt
python seed.py                 # 3 demo issues at 3 timeline stages
uvicorn main:app --reload      # http://127.0.0.1:8000
python ai.py fixtures/photos/sample_hvac.jpg "AC broken 9 days"   # test AI alone
```

## File ownership — respect these lanes

Three people are working in parallel. Edit outside your lane only if asked.

| Files | Owner | Scope |
|---|---|---|
| `templates/`, `static/` | **A** | All UI |
| `ai.py`, `letter.py` | **B** | Gemini calls, notice template, statute + deadline math |
| `main.py`, `db.py`, `storage.py`, `pdf.py`, `seed.py` | **C** | Routes, storage, PDF, deploy |

## The data contract

`fixtures/sample_issue.json` is the agreed issue shape. The whole issue is stored as
JSON in one SQLite column, so adding a field needs no migration. **If you change the
shape, update the fixture in the same commit** — the other two are building against it.

Routes: `GET /` · `POST /issues` · `GET /issues` · `GET /issues/{id}` ·
`POST /issues/{id}/notice` · `POST /issues/{id}/sent` · `GET /issues/{id}/packet.pdf`

## Design rules that are not negotiable

1. **The model writes facts, not law.** The letter's legal skeleton is a fixed template
   in `letter.py`. Gemini fills only `factual_description`, under a prompt that forbids
   citing law or stating legal conclusions. Never move statutory language into a prompt,
   and never let the model assert what a tenant is entitled to do.
2. **`classify()` and `draft_notice()` never raise.** Missing API key, timeout, bad
   JSON — all degrade to the template path with `degraded: True`. The app must work in a
   live demo with no network.
3. **Timestamps are server-generated.** `db.now_iso()` and `storage.save_photo()` only.
   Never accept a client-supplied time; the point of the product is a record someone can
   rely on.
4. **The cure clock starts on delivery, not on drafting.** `POST /sent` sets
   `cure_deadline = sent_at + 7 days` via `letter.cure_deadline()`.

## Gotchas already hit — don't re-discover these

- **`TemplateResponse(request, "x.html", {...})`** — request first. Starlette ≥1.0
  removed the old `(name, {"request": request})` form; it fails with a confusing
  `unhashable type: 'dict'`.
- **xhtml2pdf supports a small CSS subset.** No flex, no grid, no `border-collapse`.
  `packet.html` is deliberately plain CSS and tables. Don't Tailwind it.
- **`white-space: pre-wrap` doesn't wrap reliably in xhtml2pdf.** The letter is
  hard-wrapped in Python via the `wrap` Jinja filter (`letter.wrap_for_print`). Keep it.
- **PDF images need absolute filesystem paths**, not web paths. `main.py` sets
  `p["abs_path"]` via `storage.abs_path()` before rendering `packet.html`.
- **Render's free tier has an ephemeral filesystem.** Uploads and the SQLite file are
  wiped on restart; re-run `seed.py` after deploying.

## Do not build

Accounts, login, multi-user, roles, dark mode, animations, a mobile app, a landlord
portal, tests beyond a smoke check, or a scraper. One user, one device, a few excellent
screens. Scope creep is the main way this project fails.

## Tone for any user-facing copy

Plain language at roughly an 8th-grade reading level. Calm and factual — the user is
stressed and possibly broke. Never alarmist, never chummy. No emoji. Say "notice," not
"legal action."

## Schedule

Feature freeze 3:30 PM · deploy 4:00 · submit 4:30 · demo video after. After freeze,
only bug fixes, copy, and demo prep — no new features, no refactors.
