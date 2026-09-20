"""Gemini: photo classification + factual drafting. OWNER: Person B — this file
is yours alone, nobody else edits it.

Two public functions, exactly as agreed in the contract meeting:

    classify(photo_bytes, description) -> dict
    draft_notice(issue) -> str

Both ALWAYS return something usable. If the API key is missing, the call fails,
or the model times out, they fall back to a deterministic template path and set
`degraded: True`. Wire that fallback before 2pm — a live demo that survives an
API hiccup beats a perfect prompt that doesn't.

Test without running the web app:

    python ai.py fixtures/photos/sample_hvac.jpg "AC broken 9 days, 88F inside"
"""

from __future__ import annotations

import json
import os
import sys

import letter

MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
API_KEY = os.environ.get("GEMINI_API_KEY")

CATEGORIES = [
    "hvac", "plumbing", "electrical", "pest", "mold",
    "structural", "appliance", "lock_security", "cosmetic", "other",
]

CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "category": {"type": "string", "enum": CATEGORIES},
        "habitability": {"type": "boolean"},
        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
        "rationale": {"type": "string"},
        "factual_description": {"type": "string"},
    },
    "required": ["category", "habitability", "severity", "rationale", "factual_description"],
}

CLASSIFY_PROMPT = """You are helping a residential tenant in Florida document a \
maintenance problem in their rental unit.

You are given a photo and the tenant's own description.

Return JSON with:
- category: the best-fitting maintenance category.
- habitability: true only if the condition plausibly affects the unit's basic \
habitability (heat/AC in extreme weather, running water, sewage, electricity, \
secure locks, active leaks, mold, pest infestation, structural safety). Cosmetic \
wear is false.
- severity: low, medium, or high.
- rationale: ONE sentence, plain language, explaining the habitability call.
- factual_description: two to four sentences describing ONLY what is observable \
in the photo and stated by the tenant, written in neutral third-person-free \
first-person tenant voice suitable for a formal notice letter. Include how long \
the tenant says it has been going on if they said. Do NOT cite any law. Do NOT \
state legal conclusions. Do NOT speculate about cause or fault. Do NOT invent \
details that are not in the photo or the description.

Tenant's description: {description}
"""


def _client():
    if not API_KEY:
        raise RuntimeError("GEMINI_API_KEY not set")
    from google import genai  # imported lazily so the app runs without the SDK

    return genai.Client(api_key=API_KEY)


def _fallback_classification(description: str) -> dict:
    return {
        "category": "other",
        "habitability": True,
        "severity": "medium",
        "rationale": "Not automatically classified — review this before sending.",
        "factual_description": letter.FALLBACK_DESCRIPTION.format(raw=description.strip()),
        "degraded": True,
    }


def classify(photo_bytes: bytes | None, description: str) -> dict:
    """Photo + tenant description -> structured classification. Never raises."""
    try:
        from google.genai import types

        client = _client()
        parts = [CLASSIFY_PROMPT.format(description=description.strip())]
        if photo_bytes:
            parts.append(types.Part.from_bytes(data=photo_bytes, mime_type="image/jpeg"))

        resp = client.models.generate_content(
            model=MODEL,
            contents=parts,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=CLASSIFY_SCHEMA,
                temperature=0.2,
            ),
        )
        data = json.loads(resp.text)
        data["degraded"] = False
        return data
    except Exception as exc:  # noqa: BLE001 — degrade, never crash the request
        print(f"[ai.classify] falling back: {exc}", file=sys.stderr)
        return _fallback_classification(description)


def draft_notice(issue: dict) -> str:
    """Render the §83.56 notice. The legal skeleton comes from letter.py; only the
    factual paragraph comes from the model."""
    cls = issue.get("classification") or {}
    factual = (cls.get("factual_description") or "").strip()
    if not factual:
        factual = letter.FALLBACK_DESCRIPTION.format(raw=issue.get("description", ""))

    return letter.render_letter(
        tenant_name=issue.get("tenant_name", ""),
        tenant_contact=issue.get("tenant_contact", ""),
        unit_address=issue.get("unit_address", ""),
        landlord_name=issue.get("landlord_name", ""),
        landlord_address=issue.get("landlord_address", ""),
        factual_description=factual,
        habitability=bool(cls.get("habitability", True)),
        delivery_method=(issue.get("notice") or {}).get("delivery_method"),
    )


if __name__ == "__main__":
    photo = None
    if len(sys.argv) > 1 and os.path.exists(sys.argv[1]):
        photo = open(sys.argv[1], "rb").read()
    desc = sys.argv[2] if len(sys.argv) > 2 else "AC stopped working 9 days ago."
    result = classify(photo, desc)
    print(json.dumps(result, indent=2))
    print("\n" + "=" * 60 + "\n")
    print(draft_notice({
        "tenant_name": "Jordan Ruiz",
        "tenant_contact": "(352) 555-0142",
        "unit_address": "1204 SW 3rd Ave, Apt 7, Gainesville, FL 32601",
        "landlord_name": "Oakline Property Management",
        "landlord_address": "PO Box 4412, Gainesville, FL 32602",
        "description": desc,
        "classification": result,
    }))
