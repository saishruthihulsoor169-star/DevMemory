"""
Builds a short "developer profile" from a student's logged topics --
skills, current project, and what they seem to be focused on right now.

This is what turns CodeMentor from "a chatbot with memory" into something
that actually shows you a profile of who you are as a developer, built
from what you've talked about, not just a longer scrollback.
"""

import json
import os
from groq import Groq

from topics_store import get_topics

_client = Groq(api_key=os.getenv("GROQ_API_KEY"))

_DEFAULT_PROFILE = {
    "tagline": "Just getting started — ask a few questions and I'll build your profile.",
    "skills": [],
    "current_project": "",
    "focus_areas": [],
}

# Tiny in-memory cache so reloading the page doesn't re-call the LLM every
# time. Resets when the server restarts -- fine for a demo, not meant to
# survive a redeploy.
_cache = {}


def build_profile(email: str, force: bool = False) -> dict:
    if not force and email in _cache:
        return _cache[email]

    topics = get_topics(email)
    if not topics:
        return _DEFAULT_PROFILE

    topics_text = "\n".join(f"- {t}" for t in topics[:20])

    try:
        result = _client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You build a short developer profile from a list of topics a "
                        "student has discussed with their coding mentor. Reply with ONLY "
                        "valid JSON, no markdown fences, no extra text, in exactly this "
                        "shape: "
                        '{"tagline": "one short encouraging sentence", '
                        '"skills": ["up to 5 short skill or technology names"], '
                        '"current_project": "short phrase, or empty string if unclear", '
                        '"focus_areas": ["up to 3 short phrases describing what they seem '
                        'to be learning or stuck on right now"]}'
                    ),
                },
                {"role": "user", "content": topics_text},
            ],
            max_tokens=220,
        )
        raw = result.choices[0].message.content.strip()
        raw = raw.strip("`")
        if raw.lower().startswith("json"):
            raw = raw[4:].strip()
        parsed = json.loads(raw)
    except Exception:
        return _DEFAULT_PROFILE

    profile = {
        "tagline": parsed.get("tagline") or _DEFAULT_PROFILE["tagline"],
        "skills": parsed.get("skills") or [],
        "current_project": parsed.get("current_project") or "",
        "focus_areas": parsed.get("focus_areas") or [],
    }
    _cache[email] = profile
    return profile