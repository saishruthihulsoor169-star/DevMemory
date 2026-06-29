from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from groq import Groq
from dotenv import load_dotenv
import os

from parcle_client import get_context, save_conversation
from auth import create_account, verify_login, make_token, get_user_name, verify_token
from topics_store import add_topic, get_topics
from profile_builder import build_profile

load_dotenv()

app = FastAPI()
client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ---------- request/response shapes ----------

class SignupRequest(BaseModel):
    name: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class UserMessage(BaseModel):
    message: str


# ---------- auth dependency ----------
# Any route that takes `user_email: str = Depends(get_current_user)` will
# automatically require a valid "Authorization: Bearer <token>" header.

def get_current_user(authorization: str = Header(None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="You need to sign in first.")
    token = authorization.split(" ", 1)[1]
    email = verify_token(token)
    if not email:
        raise HTTPException(status_code=401, detail="Your session has expired. Please sign in again.")
    return email


# ---------- auth routes ----------

@app.post("/signup")
def signup(data: SignupRequest):
    try:
        create_account(data.email, data.password, data.name)
    except ValueError as e:
        # create_account raises ValueError with a message safe to show the user
        raise HTTPException(status_code=400, detail=str(e))

    email = data.email.strip().lower()
    token = make_token(email)
    return {"token": token, "name": get_user_name(email), "email": email}


@app.post("/login")
def login(data: LoginRequest):
    user = verify_login(data.email, data.password)
    if not user:
        raise HTTPException(status_code=401, detail="Incorrect email or password.")

    email = data.email.strip().lower()
    token = make_token(email)
    return {"token": token, "name": user["name"], "email": email}


@app.get("/me")
def me(user_email: str = Depends(get_current_user)):
    """Lets the frontend re-identify a returning user from a saved token,
    so refreshing the page doesn't kick them back to the login screen."""
    return {"email": user_email, "name": get_user_name(user_email)}


# ---------- topic labels for the sidebar ----------

def generate_topic_label(message: str) -> str:
    """Best-effort short topic label, e.g. 'Hackathon app features', for the
    sidebar list. Wrapped in try/except so a hiccup here never breaks the
    actual chat reply -- it just falls back to a plain truncation."""
    try:
        result = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "Reply with only a 2-5 word topic label summarizing the user's message. No punctuation, no quotes around it -- just the bare phrase."},
                {"role": "user", "content": message},
            ],
            max_tokens=12,
        )
        label = result.choices[0].message.content.strip().strip('"').strip("'")
        return label or (message[:40] + ("…" if len(message) > 40 else ""))
    except Exception:
        return message[:40] + ("…" if len(message) > 40 else "")


# ---------- chat route ----------

@app.post("/chat")
def chat(data: UserMessage, user_email: str = Depends(get_current_user)):
    # user_email comes from the verified session token now, instead of a
    # hardcoded "shruthi_demo" -- this is what makes memory per-account.
    past_context = get_context(user_email, data.message)

    system_prompt = "You are a helpful, encouraging coding mentor for beginner developers."
    if past_context:
        system_prompt += f" Here is what you remember about this student: {past_context}"

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": data.message}
        ]
    )
    reply = response.choices[0].message.content

    save_conversation(user_email, data.message, reply)

    topic = generate_topic_label(data.message)
    add_topic(user_email, topic)

    # "remembered" powers the Memory Retrieved box -- it shows exactly what
    # was pulled from Parcle to answer THIS question, so the memory feature
    # is something visible, not just a backend detail.
    return {"reply": reply, "topic": topic, "remembered": past_context or None}


@app.get("/topics")
def topics(user_email: str = Depends(get_current_user)):
    """Powers the sidebar topic list."""
    return {"topics": get_topics(user_email)}


@app.get("/profile")
def profile(refresh: bool = False, user_email: str = Depends(get_current_user)):
    """Powers the Developer Profile card. Pass ?refresh=true to force a
    rebuild instead of using the cached version."""
    return build_profile(user_email, force=refresh)


# Must stay LAST: this mounts the whole project folder as static files and
# serves index.html at "/". If it were defined before the routes above, it
# would swallow requests to /signup, /login, /chat, /me before they ever
# reached those handlers.
app.mount("/", StaticFiles(directory=".", html=True), name="static")