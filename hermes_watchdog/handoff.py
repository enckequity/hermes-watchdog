"""Hand an incident to the person with a note the agent can act on.

The page's primary action builds a diagnose-and-fix note from the context Watchdog
already has and marks the incident handed over in Hermes's own lifecycle. It never
fires the job: a manual run executes the job's stored prompt and its normal
delivery, so whatever the job sends could go out a second time. The person pastes
the note into a chat, and the agent diagnoses there. No new tool surface, no shell
of our own.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from . import sources


def build_prompt(incident: Dict[str, Any], job: Optional[Dict[str, Any]] = None) -> str:
    """The instruction the agent receives. Written for a fix, not a re-run."""
    name = str(incident.get("job_name") or incident.get("job_id") or "a scheduled job")
    job_id = str(incident.get("job_id") or "")
    error = str(incident.get("error") or "").strip()
    when = str(incident.get("last_seen_at") or "")
    output_file = str(incident.get("output_file") or "").strip()
    self_check = "sweep" in name.lower() or "watchdog" in name.lower()

    lines = [
        f"The scheduled job \"{name}\" ({job_id}) failed" + (f" at {when}." if when else "."),
    ]
    if error:
        lines.append(f"The recorded failure: {error}")
    else:
        lines.append("No error text was recorded for the failure.")
    if output_file:
        lines.append(f"The run's own output is at {output_file} — read it before deciding anything.")
    if self_check:
        lines.append(
            "This is the watchdog's own check job, not one of the user's jobs. Confirm it is "
            "healthy now (a restart of the assistant is the usual cause) and close the incident if so."
        )
    else:
        lines += [
            "Find the actual cause and fix it — do not simply re-run the job and declare success.",
            "Do not repeat anything the job sends or posts (messages, emails, posts) while you "
            "diagnose; whatever went out before the failure may already have been delivered.",
            "If it cannot be fixed from here, say plainly what a person must change.",
        ]
    lines.append(
        "When you are done, reply with two or three sentences the user can act on: what was wrong, "
        "what you changed, and what happens next. No command snippets unless they are unavoidable."
    )
    return "\n".join(lines)


def hand_off(incident: Dict[str, Any], job: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Escalate the incident with the diagnose-and-fix note; never run the job."""
    job_id = str(incident.get("job_id") or "")
    if not job_id:
        return {"ok": False, "error": "this incident has no job left to run"}
    recorded = sources.mark_alerted(str(incident.get("incident_id") or ""))
    return {"ok": True, "job_id": job_id, "started": False, "recorded": recorded,
            "prompt": build_prompt(incident, job)}
