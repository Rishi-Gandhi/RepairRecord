"""Demo data. OWNER: Person C. Run `python seed.py` before you demo.

An empty app demos terribly, and you do not want to be typing into a form live
in front of judges. This creates three issues at three different timeline stages
so the list screen and the countdown both have something to show.
"""

import os
import shutil
from datetime import datetime, timedelta, timezone

import db
import letter
import storage

SAMPLES = [
    dict(
        photo="fixtures/photos/sample_hvac.jpg",
        description="AC stopped blowing cold air 9 days ago. It's 88F inside. "
                    "I texted the office on Sept 11 and Sept 14, no response.",
        classification=dict(category="hvac", habitability=True, severity="high",
                            rationale="Loss of cooling during extreme heat affects habitability.",
                            factual_description=(
                                "The air conditioning unit in my apartment stopped producing cold "
                                "air approximately nine days ago. The indoor temperature has been "
                                "measured at 88 degrees Fahrenheit. I notified the management "
                                "office by text message on September 11 and again on September 14 "
                                "and have not received a response. The condition remains "
                                "uncorrected."),
                            degraded=False),
        stage="sent",
    ),
    dict(
        photo="fixtures/photos/sample_leak.jpg",
        description="Water coming through the ceiling in the bathroom, spreading stain, "
                    "started three days ago after the upstairs unit's washer ran.",
        classification=dict(category="plumbing", habitability=True, severity="high",
                            rationale="An active water intrusion risks mold and structural damage.",
                            factual_description=(
                                "Water is entering through the bathroom ceiling of my unit. A stain "
                                "has been spreading for approximately three days and began after "
                                "the upstairs unit ran a washing machine. The affected area is "
                                "visibly wet and discolored."),
                            degraded=False),
        stage="drafted",
    ),
    dict(
        photo="fixtures/photos/sample_lock.jpg",
        description="Deadbolt on the front door doesn't latch — the door can be pushed open.",
        classification=dict(category="lock_security", habitability=True, severity="high",
                            rationale="A non-functioning exterior lock affects the security of the unit.",
                            factual_description=(
                                "The deadbolt on the exterior front door of my unit does not engage. "
                                "The door can be pushed open when it appears to be locked."),
                            degraded=False),
        stage="reported",
    ),
]

TENANT = dict(
    tenant_name="Jordan Ruiz",
    tenant_contact="(352) 555-0142 | jordan.ruiz@example.com",
    unit_address="1204 SW 3rd Ave, Apt 7, Gainesville, FL 32601",
    landlord_name="Oakline Property Management",
    landlord_address="PO Box 4412, Gainesville, FL 32602",
)


def _copy_photo(src: str) -> list[dict]:
    if not os.path.exists(src):
        return []
    os.makedirs(storage.UPLOAD_DIR, exist_ok=True)
    dest_name = f"seed_{os.path.basename(src)}"
    shutil.copy(src, os.path.join(storage.UPLOAD_DIR, dest_name))
    with open(src, "rb") as fh:
        content = fh.read()
    import hashlib
    return [{
        "id": f"ph_seed_{os.path.basename(src)[:6]}",
        "path": f"/uploads/{dest_name}",
        "captured_at": db.now_iso(),
        "sha256": hashlib.sha256(content).hexdigest(),
    }]


def main() -> None:
    db.init_db()
    import ai

    for i, s in enumerate(SAMPLES):
        issue = {
            "id": f"iss_demo{i+1}",
            "created_at": (datetime.now(timezone.utc) - timedelta(days=i)).isoformat(timespec="seconds"),
            **TENANT,
            "description": s["description"],
            "photos": _copy_photo(s["photo"]),
            "classification": s["classification"],
            "notice": {"letter_text": None, "generated_at": None,
                       "delivery_method": None, "sent_at": None, "cure_deadline": None},
            "events": [],
        }
        db.add_event(issue, "reported", "Issue documented in RepairRecord")

        if s["stage"] in ("drafted", "sent"):
            issue["notice"]["letter_text"] = ai.draft_notice(issue)
            issue["notice"]["generated_at"] = db.now_iso()
            db.add_event(issue, "notice_generated", "7-day notice drafted")

        if s["stage"] == "sent":
            sent_at = (datetime.now(timezone.utc) - timedelta(days=3)).isoformat(timespec="seconds")
            issue["notice"]["delivery_method"] = "Mailed, certified mail with return receipt"
            issue["notice"]["sent_at"] = sent_at
            issue["notice"]["cure_deadline"] = letter.cure_deadline(sent_at)
            issue["notice"]["letter_text"] = ai.draft_notice(issue)
            db.add_event(issue, "notice_sent", "Notice delivered — certified mail")

        db.save(issue)
        print(f"seeded {issue['id']}  ({s['stage']})")


if __name__ == "__main__":
    main()
