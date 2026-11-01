"""backend/urlroute_webhook.py - FastAPI webhook for URL Route extension.

Receives actions from the extension and routes them to the Team Leader, which
dispatches to sub-bots: ordem (8001) and conhecimento (8002).
"""
from fastapi import FastAPI, Request
from pydantic import BaseModel
from typing import Any

app = FastAPI(title="URL Route Webhook")

SUB_BOTS = {
    "ordem": "http://localhost:8001/v1",
    "conhecimento": "http://localhost:8002/v1",
}

# Actions routed to ordem
ORDEM_ACTIONS = {
    "copy-url", "copy-title", "copy-url-title",
    "theme-auto", "theme-light", "theme-dark", "open-options", "theme-default",
}

class ActionPayload(BaseModel):
    action: str
    payload: dict = None
    text: str = None

@app.get("/healthz")
def healthz():
    return {"status": "ok", "service": "url-route-webhook"}

@app.post("/api/url-route/actions")
async def handle_action(payload: ActionPayload):
    action = payload.action or "share"
    sub_bot = "ordem" if action in ORDEM_ACTIONS else "conhecimento"

    # 1) Deliver to Team Leader's bot_relay outbox (preferred)
    deliver_to_team_leader(payload, sub_bot)

    # 2) Fallback: forward to the team-leader receiver if configured
    receiver = __import__("os").environ.get("TEAM_LEADER_RECEIVER_URL")
    if receiver:
        try:
            import json, aiohttp
            async def _f():
                async with aiohttp.ClientSession() as s:
                    await s.post(receiver, json=payload.dict())
            import asyncio
            asyncio.get_event_loop().run_until_complete(_f())
        except Exception as e:
            print("fallback post failed:", e)

    return {
        "ok": True, "action": action, "route": sub_bot,
        "sub_bot_url": SUB_BOTS.get(sub_bot),
        "delivery": "bot_relay",
    }

def deliver_to_team_leader(payload: ActionPayload, sub_bot: str):
    """Write the action into the Team Leader bot_relay outbox (local pattern)."""
    import json, os
    env = payload.dict()
    entry = {
        "action": payload.action,
        "payload": payload.payload or {},
        "target": sub_bot,
        "received_at": "now",
    }
    outbox = os.path.expanduser("~/.urlroute/bot_relay/outbox")
    os.makedirs(os.path.dirname(outbox), exist_ok=True)
    with open(outbox, "a") as f:
        f.write(json.dumps(entry) + "\n")
