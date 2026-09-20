"""The notice letter's fixed skeleton and the cure-deadline math. OWNER: Person B.

DESIGN RULE — read this before you touch ai.py:

    The legal structure lives HERE, as a fixed template with slots.
    The model fills the factual slots. The model does NOT write the legal parts.

That split is why this tool is defensible: a language model never invents a
statutory claim, it only describes what is broken. Say this in the demo — it is
the difference between "we asked an AI for legal advice" and "we automated the
paperwork around a statute."

RepairRecord produces documentation and a template. It is not legal advice.
"""

from datetime import datetime, timedelta, timezone

# Florida's residential landlord/tenant statute. §83.56(1) requires the tenant to
# deliver WRITTEN notice of a landlord's material noncompliance with §83.51(1)
# and to allow 7 days for the landlord to cure before the tenant may terminate.
# The citation is shown to the user so they can read the source themselves.
STATUTE_CITE = "Fla. Stat. §83.56(1)"
STATUTE_SUMMARY = (
    "Under Florida Statute §83.56(1), a tenant who believes the landlord has "
    "materially failed to comply with §83.51(1) or the lease must deliver written "
    "notice specifying the noncompliance and allow at least 7 days for the "
    "landlord to correct it."
)
CURE_DAYS = 7

DELIVERY_METHODS = [
    "Hand delivery",
    "Mailed, U.S. first-class mail",
    "Mailed, certified mail with return receipt",
    "Posted on the premises",
    "Email (if the lease permits notice by email)",
]

LETTER_TEMPLATE = """{today}

{landlord_name}
{landlord_address}

RE: Notice of Maintenance Defect and Request to Cure — {unit_address}

Dear {landlord_name},

I am the tenant at {unit_address}. I am writing to give you written notice of a
maintenance problem at the unit and to request that it be corrected.

DESCRIPTION OF THE PROBLEM

{factual_description}

{habitability_paragraph}

REQUEST

I am requesting that this condition be repaired. {statute_summary} This letter is
that written notice. Please correct the condition within {cure_days} days of
receiving this letter, or contact me to arrange access to the unit.

Photographs documenting this condition, with the date and time each was recorded,
are attached to this notice.

You can reach me at {tenant_contact}.

Sincerely,

{tenant_name}
{unit_address}

--
Delivery method: {delivery_method}
Statutory reference: {statute_cite}
"""

HABITABILITY_PARAGRAPH = (
    "I believe this condition affects the habitability of the unit and falls within "
    "the landlord's maintenance obligations under Fla. Stat. §83.51(1)."
)

FALLBACK_DESCRIPTION = (
    "The tenant reports the following condition at the unit:\n\n{raw}\n\n"
    "The condition remains uncorrected as of the date of this notice."
)


def render_letter(
    *,
    tenant_name: str,
    tenant_contact: str,
    unit_address: str,
    landlord_name: str,
    landlord_address: str,
    factual_description: str,
    habitability: bool,
    delivery_method: str | None = None,
    today: datetime | None = None,
) -> str:
    today = today or datetime.now(timezone.utc)
    return LETTER_TEMPLATE.format(
        today=today.strftime("%B %-d, %Y") if hasattr(today, "strftime") else str(today),
        landlord_name=landlord_name or "[Landlord name]",
        landlord_address=landlord_address or "[Landlord address]",
        unit_address=unit_address or "[Unit address]",
        factual_description=factual_description.strip(),
        habitability_paragraph=HABITABILITY_PARAGRAPH if habitability else "",
        statute_summary=STATUTE_SUMMARY,
        cure_days=CURE_DAYS,
        tenant_contact=tenant_contact or "[Your phone or email]",
        tenant_name=tenant_name or "[Your name]",
        delivery_method=delivery_method or "[to be recorded when delivered]",
        statute_cite=STATUTE_CITE,
    )


def wrap_for_print(text: str, width: int = 68) -> str:
    """Hard-wrap the letter for the PDF. xhtml2pdf's `white-space: pre-wrap` is
    unreliable, so long lines run off the right margin unless we wrap in Python.
    Browsers don't need this — detail.html wraps fine on its own."""
    import textwrap

    out = []
    for line in (text or "").split("\n"):
        out.append(textwrap.fill(line, width=width) if line.strip() else "")
    return "\n".join(out)


def cure_deadline(sent_at_iso: str) -> str:
    """7 days from delivery. The clock starts when the notice is DELIVERED, not
    when it is written — which is exactly why the app records delivery separately."""
    sent = datetime.fromisoformat(sent_at_iso)
    return (sent + timedelta(days=CURE_DAYS)).isoformat(timespec="seconds")


def days_remaining(deadline_iso: str | None) -> int | None:
    if not deadline_iso:
        return None
    delta = datetime.fromisoformat(deadline_iso) - datetime.now(timezone.utc)
    return int(delta.total_seconds() // 86400)
