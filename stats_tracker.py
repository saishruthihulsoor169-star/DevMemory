"""
Tracks user statistics for the dashboard:
- Number of questions asked
- Topics discussed
- Memory recall rate
- Memory strength
"""

import json
import os
from datetime import datetime

_DIR = os.path.dirname(os.path.abspath(__file__))
STATS_FILE = os.path.join(_DIR, "stats.json")

def _load() -> dict:
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def _save(data: dict) -> None:
    with open(STATS_FILE, "w") as f:
        json.dump(data, f, indent=2)

def track_question(email: str, question: str) -> None:
    """Increment question count for a user."""
    data = _load()
    if email not in data:
        data[email] = {
            "questions": 0,
            "topics": 0,
            "recall_rate": 0,
            "memory_strength": 0,
            "last_active": datetime.now().isoformat()
        }
    
    data[email]["questions"] = data[email].get("questions", 0) + 1
    data[email]["last_active"] = datetime.now().isoformat()
    
    # Update topics count (approximate)
    data[email]["topics"] = data[email].get("topics", 0) + 0.5  # Increment by half, will be rounded
    
    _save(data)

def update_memory_strength(email: str, increment: int) -> None:
    """Increase memory strength when memory is successfully recalled."""
    data = _load()
    if email not in data:
        data[email] = {
            "questions": 0,
            "topics": 0,
            "recall_rate": 0,
            "memory_strength": 0,
            "last_active": datetime.now().isoformat()
        }
    
    current = data[email].get("memory_strength", 0)
    data[email]["memory_strength"] = min(100, current + increment)
    
    # Update recall rate based on memory strength
    data[email]["recall_rate"] = min(100, data[email]["memory_strength"] * 0.9)
    
    _save(data)

def get_stats(email: str) -> dict:
    """Get all stats for a user."""
    data = _load()
    if email not in data:
        return {
            "questions": 0,
            "topics": 0,
            "recall_rate": 0,
            "memory_strength": 0
        }
    
    stats = data[email]
    return {
        "questions": stats.get("questions", 0),
        "topics": int(stats.get("topics", 0)),
        "recall_rate": int(stats.get("recall_rate", 0)),
        "memory_strength": int(stats.get("memory_strength", 0))
    }

def update_stats_from_conversation(email: str, had_memory: bool) -> None:
    """Update stats based on conversation outcome."""
    data = _load()
    if email not in data:
        data[email] = {
            "questions": 0,
            "topics": 0,
            "recall_rate": 0,
            "memory_strength": 0,
            "last_active": datetime.now().isoformat()
        }
    
    if had_memory:
        current = data[email].get("memory_strength", 0)
        data[email]["memory_strength"] = min(100, current + 3)
        data[email]["recall_rate"] = min(100, data[email]["memory_strength"] * 0.9)
    
    _save(data)