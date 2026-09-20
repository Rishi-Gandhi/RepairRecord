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
