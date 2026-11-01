# Backend URL Route Webhook

FastAPI webhook that receives actions from the URL Route extension and routes them
to the Team Leader, which dispatches to sub-bots `ordem` (8001) and `conhecimento` (8002).

## Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/healthz` | Liveness check |
| POST | `/api/url-route/actions` | Receive an action and route it |

## Request body
```json
{ "action": "copy-url", "payload": { "url": "https://example.com", "title": "Example" } }
```

## Response
```json
{ "ok": true, "action": "copy-url", "route": "ordem", "sub_bot_url": "http://localhost:8001/v1" }
```

## Routing matrix

| Action | Sub-bot |
|---|---|
| copy-*, theme-*, open-options | ordem (`localhost:8001`) |
| share | conhecimento (`localhost:8002`) |

## Team Leader integration

1. **bot_relay outbox** — writes to `~/.urlroute/bot_relay/outbox`.
2. **Generic HTTP forward** — POST to `TEAM_LEADER_RECEIVER_URL` (env var).

## Install & run

```sh
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install fastapi uvicorn
uvicorn urlroute_webhook:app --host 0.0.0.0 --port 8007
```
