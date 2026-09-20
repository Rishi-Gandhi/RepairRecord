# RepairRecord

**Document a rental repair problem, generate the written notice Florida law requires, and export an evidence packet.**

CityCamp Gainesville Hack Day — General Civic Tech track.

RepairRecord is documentation and a template, **not legal advice.**

---

## Why it exists

Your AC dies in August. You text your landlord. Nothing. Three weeks later you have a
phone full of unanswered messages and no leverage, because Florida law does not care
about your texts. **Fla. Stat. §83.56(1)** requires *written* notice and a **7-day**
cure period before a tenant has any real remedy. Most renters have never heard of it,
and of those who have, most don't know how to write the letter.

RepairRecord closes that gap: photo in, server-timestamped record + a properly
formatted 7-day notice + a PDF evidence packet out.

---

## Run it

```bash
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env                                  # add your GEMINI_API_KEY
python seed.py                                        # demo data — do this before demoing
uvicorn main:app --reload
```

Open http://127.0.0.1:8000

**It runs without a Gemini key.** `ai.py` falls back to a deterministic template path
and marks the classification `degraded`. Keep that path working — a live demo that
survives an API hiccup beats a perfect prompt that doesn't.

Test the AI module on its own, without the web app:

```bash
python ai.py fixtures/photos/sample_hvac.jpg "AC broken 9 days, 88F inside"
```

---

## Who owns what

| File | Owner | |
|---|---|---|
| `templates/`, `static/` | **A** | Capture page, issue list, detail view, timeline, disclaimer panel |
| `ai.py`, `letter.py` | **B** | Gemini classification, the notice template, statute + deadline math |
| `main.py`, `db.py`, `storage.py`, `pdf.py`, `seed.py` | **C** | Routes, SQLite, photo storage, evidence packet, deploy & submit |

Three lanes, almost no merge conflicts. Work against `fixtures/sample_issue.json`
until integration — **nobody waits on anybody.**

## The contract

`fixtures/sample_issue.json` is the agreed shape. Routes:

| Method | Route | |
|---|---|---|
| `GET` | `/` | Capture form |
| `POST` | `/issues` | Create from form + photo → classify → redirect to detail |
| `GET` | `/issues` | List |
| `GET` | `/issues/{id}` | Detail + timeline |
| `POST` | `/issues/{id}/notice` | Draft the 7-day notice |
| `POST` | `/issues/{id}/sent` | Mark delivered → starts the cure clock |
| `GET` | `/issues/{id}/packet.pdf` | Evidence packet |

---

## Two design decisions worth defending in the demo

**1. The model writes facts, not law.** The letter's legal skeleton is a fixed template
in `letter.py`. Gemini fills only the factual description of what's broken, under a
prompt that forbids citing law or stating legal conclusions. A language model never
invents a statutory claim here.

**2. The record is server-side.** Photos get a server-generated timestamp and a
SHA-256 hash at the moment of upload. A screenshot in a camera roll proves nothing
about when it was taken; this does.

---

## Deploy (Render, free tier)

Build: `pip install -r requirements.txt`
Start: `uvicorn main:app --host 0.0.0.0 --port $PORT`
Env: `GEMINI_API_KEY`

Note the free tier has an **ephemeral filesystem** — uploads and the SQLite file are
wiped on restart. Fine for a hackathon demo (re-run `seed.py`), not fine for real use.
Attach a persistent disk or move to S3 + Postgres if this continues.

## Known limits (say these before a judge finds them)

- Single-user; no accounts or auth.
- Florida only. The statute and cure period are Florida-specific.
- Ephemeral storage on the free tier.
- Classification is a starting point for the tenant to review, not an adjudication.

## Next

Partner with UF Student Legal Services for distribution · landlord-response tracking ·
aggregate anonymized reports into a repair-complaint map by property.


UI: 
I'm working on RepairRecord, a hackathon project. Read CLAUDE.md and README.md first — they explain the product, the data contract, and the ownership lanes.

I'm Person A. I own templates/ and static/ ONLY. Do not edit main.py, db.py, storage.py, pdf.py, seed.py, ai.py, or letter.py — if something in my lane needs a change in one of those, tell me and I'll coordinate with the owner instead of you editing it.

The templates currently work but are deliberately plain. My job is to make them good enough that a judge scoring "design and usability" would say someone would actually use this. The user is a stressed, possibly broke renter on a phone.

Work in this order, and show me the result after each step:

1. templates/detail.html — the screen we demo. Priority is the timeline stepper (documented → notice drafted → notice delivered → cure deadline) with the live day counter. Make it the most legible thing on the page. Then the letter block: it should read like a real letter.
2. templates/capture.html — one calm screen, thumb-reachable on a phone, big submit target. Keep the localStorage prefill and capture="environment" behavior that's already there.
3. templates/list.html — scannable cards, clear status per issue.
4. The disclaimer panel in base.html — make it a designed element, not fine print.

Constraints: Tailwind via the existing CDN, no build step, no new dependencies. No accounts, login, dark mode, or animations. Must look right at 390px wide. Don't invent new fields — render only what's in fixtures/sample_issue.json.

Start by reading the three templates and telling me what you'd change about detail.html before you change anything.

API: I'm working on RepairRecord, a hackathon project. Read CLAUDE.md and README.md first, then read letter.py and ai.py fully before changing anything.

I'm Person B. I own ai.py and letter.py ONLY. Do not edit main.py, db.py, storage.py, pdf.py, seed.py, or anything in templates/ or static/. The functions classify() and draft_notice() are already wired into the app — keep their signatures and return shapes exactly as they are.

One design rule that is not negotiable: the letter's legal skeleton is a fixed template in letter.py, and Gemini fills ONLY the factual description of what's broken. Never move statutory language into a prompt, and never let the model state what a tenant is entitled to do. Our demo line is "the legal structure is fixed, the model only writes what's broken."

Also not negotiable: classify() and draft_notice() must never raise. Missing API key, timeout, bad JSON — all degrade to the template path with degraded: True. The app has to work live with no network.

What I want:
1. Review the CLASSIFY_PROMPT in ai.py against how Fla. Stat. §83.56(1) and §83.51 actually work, and tighten it. Tell me what's weak before you rewrite it.
2. Improve the letter template in letter.py so it reads like something a lawyer wouldn't wince at.
3. Help me build a small test loop: run classify() against several photo + description pairs and print the JSON side by side so I can spot bad habitability calls.

Test with: python ai.py fixtures/photos/sample_hvac.jpg "AC broken 9 days, 88F inside"

Start by reading letter.py and telling me what a Florida §83.56 notice is missing from it.

Backend: 
I'm working on RepairRecord, a hackathon project. Read CLAUDE.md and README.md first — they explain the product, the data contract, and the ownership lanes.

I'm Person C. I own main.py, db.py, storage.py, pdf.py, and seed.py. Do not edit ai.py, letter.py, or anything in templates/ or static/ — those belong to my teammates and they're editing them right now.

The app already runs end to end. My priorities, in order:

1. The evidence packet PDF (pdf.py + templates/packet.html — packet.html is the one template I do own, since it's a PDF document, not a screen). It's our demo's closing shot: clean cover summary, event record, each photo with its server timestamp and SHA-256, the full notice letter, disclaimer footer. IMPORTANT: xhtml2pdf supports only a small CSS subset — no flex, no grid, no border-collapse. Keep it plain CSS and tables. The letter is hard-wrapped in Python via the `wrap` Jinja filter because pre-wrap doesn't work there; don't remove that.
2. Make seed.py produce demo data that looks real — good addresses, plausible descriptions, three issues at three timeline stages.
3. Error handling on the routes: missing issue, huge upload, non-image file, form with no photo. None should show a stack trace during a demo.

Constraints: keep route handlers thin — logic goes in db.py/storage.py/pdf.py. No new dependencies beyond requirements.txt. No accounts or auth. Don't change the JSON shape in fixtures/sample_issue.json without telling me, because my teammates build against it.

Start by generating a packet PDF from the seeded data, looking at it, and telling me the three things most wrong with how it looks.