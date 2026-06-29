"""
Lightweight per-user "topics" log, just for the sidebar UI.

This is separate from Parcle. Parcle still handles the actual memory the
mentor uses to answer questions -- this file only keeps a short,
human-readable list of what's been discussed, so the sidebar can show
something like a chat-history list ("Hackathon copilot app", "React state
management") instead of dumping raw remembered text.
"""

import json
import os

_DIR = os.path.dirname(os.path.abspath(__file__))
TOPICS_FILE = os.path.join(_DIR, "topics.json")
MAX_TOPICS_PER_USER = 30


def _load() -> dict:
    if not os.path.exists(TOPICS_FILE):
        return {}
    with open(TOPICS_FILE, "r") as f:
        return json.load(f)


def _save(data: dict) -> None:
    with open(TOPICS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def add_topic(email: str, label: str) -> None:
    label = label.strip()
    if not label:
        return
    data = _load()
    topics = data.get(email, [])
    # Skip if it's basically the same as the last topic, so a few follow-up
    # questions on the same thing don't spam the sidebar with duplicates.
    if topics and topics[-1].lower() == label.lower():
        return
    topics.append(label)
    data[email] = topics[-MAX_TOPICS_PER_USER:]
    _save(data)


def get_topics(email: str) -> list:
    """Most recent topic first."""
    return list(reversed(_load().get(email, [])))