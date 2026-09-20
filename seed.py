"""Demo data. OWNER: Person C. Run `python seed.py` before you demo.

An empty app demos terribly, and you do not want to be typing into a form live
in front of judges. This creates three issues at three different timeline stages
so the list screen and the countdown both have something to show.

Every timestamp here is derived from one set of offsets per issue, so the event
log, the photo capture times, the notice dates and any date named in the prose
all agree. They did not always: the events used to be stamped with the seed
run's wall clock while the notice carried a backdated delivery, which put
"delivered" three days before "documented" on the same page of the packet.
"""

import hashlib
import os
import shutil
from datetime import datetime, timedelta, timezone

import db
import letter
import storage


def _ago(days: int = 0, hours: int = 0) -> str:
    return (
        datetime.now(timezone.utc) - timedelta(days=days, hours=hours)
    ).isoformat(timespec="seconds")


def _spoken_date(iso: str) -> str:
    """'September 11' — for dates named inside the tenant's own prose."""
    return datetime.fromisoformat(iso).strftime("%B %-d")


# Each sample declares its timeline as offsets from now. `documented` is when the
# tenant filed it, `drafted` when the notice was written, `delivered` when it was
# actually sent — the cure clock runs from `delivered`.
SAMPLES = [
    dict(
        photo="fixtures/photos/sample_hvac.jpg",
        documented=dict(days=9, hours=2),
        followed_up=dict(days=6, hours=2),
        drafted=dict(days=4, hours=1),
        delivered=dict(days=3),
        delivery_method="Mailed, certified mail with return receipt",
        delivery_note="Notice delivered — certified mail",
        description=(
            "AC stopped blowing cold air and it's 88F inside. I texted the "
            "office on {t1} and again on {t2}. No response, nobody has come out."
        ),
        classification=dict(
            category="hvac", habitability=True, severity="high",
            rationale="Loss of cooling during extreme heat affects habitability.",
            factual_description=(
                "The air conditioning unit in my apartment stopped producing cold "
                "air on {t1}. The indoor temperature has been measured at 88 "
                "degrees Fahrenheit. I notified the management office by text "
                "message on {t1} and again on {t2} and have not received a "
                "response. The condition remains uncorrected."),
            degraded=False),
    ),
    dict(
        photo="fixtures/photos/sample_leak.jpg",
        documented=dict(days=3, hours=5),
        drafted=dict(hours=20),
        description=(
            "Water coming through the bathroom ceiling. The stain showed up on "
            "{t1} after the upstairs unit ran their washer and it's still spreading."
        ),
        classification=dict(
            category="plumbing", habitability=True, severity="high",
            rationale="An active water intrusion risks mold and structural damage.",
            factual_description=(
                "Water is entering through the bathroom ceiling of my unit. A "
                "stain first appeared on {t1} and has continued to spread since. "
                "The condition began after the upstairs unit operated a washing "
                "machine. The affected area is visibly wet and discolored."),
            degraded=False),
    ),
    dict(
        photo="fixtures/photos/sample_lock.jpg",
        documented=dict(hours=5),
        description=(
            "The deadbolt on the front door doesn't latch. The door can be pushed "
            "open even when it looks locked."
        ),
        classification=dict(
            category="lock_security", habitability=True, severity="high",
            rationale="A non-functioning exterior lock affects the security of the unit.",
            factual_description=(
                "The deadbolt on the exterior front door of my unit does not "
                "engage. The door can be pushed open when it appears to be locked."),
            degraded=False),
    ),
]

TENANT = dict(
    tenant_name="Jordan Ruiz",
    tenant_contact="(352) 555-0142 | jordan.ruiz@example.com",
    unit_address="1204 SW 3rd Ave, Apt 7, Gainesville, FL 32601",
    landlord_name="Oakline Property Management",
    landlord_address="PO Box 4412, Gainesville, FL 32602",
)


def _copy_photo(src: str, captured_at: str) -> list[dict]:
    if not os.path.exists(src):
        return []
    os.makedirs(storage.UPLOAD_DIR, exist_ok=True)
    dest_name = f"seed_{os.path.basename(src)}"
    shutil.copy(src, os.path.join(storage.UPLOAD_DIR, dest_name))
    with open(src, "rb") as fh:
        content = fh.read()
    return [{
        "id": f"ph_seed_{os.path.basename(src)[:6]}",
        "path": f"/uploads/{dest_name}",
        "captured_at": captured_at,
        "sha256": hashlib.sha256(content).hexdigest(),
    }]


def main() -> None:
    db.init_db()
    import ai

    for i, s in enumerate(SAMPLES):
        documented = _ago(**s["documented"])
        # Dates the tenant names in their own words, derived from the same
        # timeline so the prose can't drift from the event log.
        dates = {"t1": _spoken_date(documented)}
        if s.get("followed_up"):
            dates["t2"] = _spoken_date(_ago(**s["followed_up"]))

        issue = {
            "id": f"iss_demo{i+1}",
            "created_at": documented,
            **TENANT,
            "description": s["description"].format(**dates),
            "photos": _copy_photo(s["photo"], documented),
            "classification": {
                **s["classification"],
                "factual_description": s["classification"]["factual_description"].format(**dates),
            },
            "notice": {"letter_text": None, "generated_at": None,
                       "delivery_method": None, "sent_at": None, "cure_deadline": None},
            "events": [],
        }
        db.add_event(issue, "reported", "Issue documented in RepairRecord", at=documented)

        stage = "reported"
        if s.get("drafted"):
            drafted = _ago(**s["drafted"])
            issue["notice"]["letter_text"] = ai.draft_notice(issue)
            issue["notice"]["generated_at"] = drafted
            db.add_event(issue, "notice_generated", "7-day notice drafted", at=drafted)
            stage = "drafted"

        if s.get("delivered"):
            delivered = _ago(**s["delivered"])
            issue["notice"]["delivery_method"] = s["delivery_method"]
            issue["notice"]["sent_at"] = delivered
            issue["notice"]["cure_deadline"] = letter.cure_deadline(delivered)
            # Re-render so the letter's footer records how it was delivered.
            issue["notice"]["letter_text"] = ai.draft_notice(issue)
            db.add_event(issue, "notice_sent", s["delivery_note"], at=delivered)
            stage = "sent"

        db.save(issue)
        print(f"seeded {issue['id']}  ({stage}, documented {documented[:10]})")


if __name__ == "__main__":
    main()
