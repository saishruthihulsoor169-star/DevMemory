# DevMemory

An AI coding mentor for beginner developers that remembers each student across
sessions — their projects, what they're stuck on, and how they like things
explained — instead of starting from zero every conversation.

Built for the Quackathon hackathon (Produck).

## Tech stack

- **Backend:** FastAPI (Python)
- **LLM:** Groq, Llama 3.3 70B
- **Persistent memory:** Parcle
- **Auth:** stdlib-only password hashing + signed session tokens (no extra dependencies)
- **Frontend:** vanilla HTML/CSS/JS, no build step

## What it does

- Chat with an AI mentor (powered by Groq's Llama 3.3 70B) that gives
  plain-English, beginner-friendly coding help.
- Every student has their own account (email + password). Memory is tied to
  *that account*, not a shared demo session — so what the mentor remembers
  about you is actually yours.
- Persistent memory is powered by [Parcle](https://parcle.ai). Every message
  is ingested into Parcle, and relevant past context is pulled back in before
  each reply, so the mentor's answers are informed by what it already knows
  about you.
- A **Developer Profile card** auto-builds a short profile (skills, current
  project, focus areas) from your logged topics using a single Groq call --
  turning chat history into something you can actually look at, not just
  scroll back through.
- A **Memory Retrieved box** shows exactly what context was pulled from
  Parcle to answer your most recent question, so the memory feature is
  something visible, not just a backend detail.

## Architecture

```
index.html        →  single-page UI: sign in / create account, then chat
main.py           →  FastAPI app: /signup, /login, /me, /chat, /topics, /profile
auth.py           →  password hashing + session tokens (stdlib only)
parcle_client.py  →  wraps Parcle's create_user / ingest_dialog / search
topics_store.py   →  short topic labels for the sidebar list (separate from Parcle)
profile_builder.py →  turns logged topics into a structured developer profile
users.json        →  local user store (created automatically on first signup)
topics.json       →  local topics log (created automatically on first chat)
```

## Debugging story: getting Parcle memory actually working

This was the hardest part of the project, and worth documenting honestly
rather than glossing over.

**Bug 1 — `user_not_found` on every `ingest_dialog` call.**
Parcle requires a user to be explicitly created with `create_user(user_id=...)`
*before* you can call `ingest_dialog` or `search` for that user. We were
calling `ingest_dialog` directly, so every save failed with a 404. The fix was
an `ensure_user()` helper that calls `create_user` once per user_id (cached in
memory so it doesn't re-fire on every message) before any read/write call.

**Bug 2 — the API key was never actually being passed to the client.**
```python
memory = Parcle(api_key=os.getenv("pmem_jilsw227RKfLYe9RTHwp4fryoVG2HXOPmsSQMkkbkc8"))
```
`os.getenv()` expects the *name* of an environment variable, not the key
itself. This line was asking Python for an env var literally named
`pmem_jilsw227...`, which doesn't exist, so it silently returned `None` — the
Parcle client had no API key at all. Fixed by passing the correct variable
name: `os.getenv("PARCLE_API_KEY")`.

**Bug 3 — memory was being saved and retrieved, but never actually used.**
After fixing bugs 1 and 2, Parcle calls succeeded with no errors — but the
chat still didn't seem to remember anything. The cause: `main.py` built a
`system_prompt` string with the retrieved memory appended, but then sent a
*different*, hardcoded system message to the Groq API instead of that
variable. The memory was there the whole time; it just never reached the
model. Fixed by passing `system_prompt` into the actual API call.

Each of these produced a different symptom (a hard error, a silent failure,
and a misleadingly "successful" call that did nothing useful) — which is part
of why they took real debugging rather than a one-line fix.

## Authentication

Lightweight and dependency-free by design, so there's nothing extra to
`pip install`:

- Passwords are hashed with PBKDF2-HMAC-SHA256 + a random per-user salt
  (100,000 iterations) — never stored in plain text.
- Sessions are signed, expiring tokens (HMAC-SHA256), not a full JWT library.
- Users live in a local `users.json` file, not a database.

This is appropriate for a hackathon demo, not a production deployment. A
production version would add a real database, HTTPS-only cookies, token
revocation, and rate limiting on login attempts.

## Running locally

**Prerequisites:** Python 3.10+, a [Groq API key](https://console.groq.com), and a [Parcle API key](https://parcle.ai).

1. Create a `.env` file with:
   ```
   GROQ_API_KEY=your_groq_key
   PARCLE_API_KEY=your_parcle_key
   AUTH_SECRET_KEY=any_long_random_string
   ```
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `uvicorn main:app --reload`
4. Open `http://127.0.0.1:8000`, create an account, and start chatting.

