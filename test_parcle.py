from parcle import Parcle
from dotenv import load_dotenv
import os

load_dotenv()
key = os.getenv("PARCLE_API_KEY")

client = Parcle(api_key=key)

try:
    client.create_user(user_id="ada")
    print("USER CREATED: ada")
except Exception as e:
    print("CREATE_USER (probably already exists):", e)

result = client.ingest_dialog(
    user_id="ada",
    messages=[
        {"role": "user", "content": "I'm allergic to peanuts."},
        {"role": "assistant", "content": "Got it — I'll avoid peanuts in suggestions."},
    ],
)
print("SUCCESS:", result)
