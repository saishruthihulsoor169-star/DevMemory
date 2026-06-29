from parcle import Parcle
from dotenv import load_dotenv
import os

load_dotenv()
print("PARCLE KEY LOADED:", os.getenv("PARCLE_API_KEY"))

memory = Parcle(api_key=os.getenv("PARCLE_API_KEY"))  # fixed: was passing the key itself as a var name

_known_users = set()

def ensure_user(user_id: str):
    """Create the user in Parcle if we haven't already, ignoring 'already exists' errors."""
    if user_id in _known_users:
        return
    try:
        memory.create_user(user_id=user_id)
        print(f"PARCLE: created user '{user_id}'")
    except Exception as e:
        # Likely already exists from a previous run -- safe to ignore, but log it
        print(f"PARCLE CREATE_USER (probably already exists): {e}")
    _known_users.add(user_id)

def get_context(user_id: str, query: str) -> str:
    ensure_user(user_id)
    try:
        result = memory.search(user_id=user_id, query=query)
        return result.answer
    except Exception as e:
        print("PARCLE GET ERROR:", e)
        return ""

def save_conversation(user_id: str, user_message: str, ai_reply: str):
    ensure_user(user_id)
    try:
        memory.ingest_dialog(
            user_id=user_id,
            messages=[
                {"role": "user", "content": user_message},
                {"role": "assistant", "content": ai_reply},
            ],
        )
    except Exception as e:
        print("PARCLE SAVE ERROR:", e)
