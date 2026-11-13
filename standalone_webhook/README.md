# Standalone Netatmo Webhook Listener & Tester

This is a self-contained Python 3 tool (zero external dependencies) that runs directly on your Mac to test Netatmo's OAuth2 + Webhooks API (`https://dev.netatmo.com/apidocumentation/webhooks`) without any PG3 or ISY dependencies.

## Credentials Pre-configured
- **Client ID**: `6aee280752c9011377071819`
- **Client Secret**: `MUwesrYBstni3Gg9WTFUK42tf9bJMGRvjCgCvgmFfV509`
- **Scope**: `read_station`

(Override anytime via `NETATMO_CLIENT_ID` / `NETATMO_CLIENT_SECRET` environment variables.)

## Quick Start (Runs Completely on This Mac)

Because Netatmo's cloud servers must send HTTP `POST` requests to a public `https://` URL, you can use the built-in `--tunnel` flag (which uses macOS's built-in `ssh` and `localhost.run`, no installs needed):

```bash
cd standalone_webhook
python3 netatmo_webhook_tool.py --tunnel --import-log
```

This will:
1. Start the local HTTP webhook receiver on `http://127.0.0.1:8080/webhook`.
2. Open a public HTTPS tunnel (`https://<random>.lhr.life/webhook`) pointing straight to your Mac.
3. Import your current active Netatmo Bearer token (or you can run `auth` inside the prompt to do a fresh OAuth2 login).
4. Register that public HTTPS URL with Netatmo (`POST /webhooks/v1/`) and immediately display Netatmo's `webhook_activation` callback as it hits your Mac!

## Interactive Commands

Inside the `netatmo>` prompt:
- `auth [redirect_uri]` — Run a full browser OAuth2 login (default `http://localhost:8765/callback`, or pass your registered redirect URI).
- `import-token` — Grab the latest active Bearer token from `/Volumes/ns/0021b902748c_17/logs/debug.log`.
- `status` — Query `GET https://api.netatmo.com/webhooks/v1/`.
- `register [https_url]` — Drop old webhooks and register a new URL (defaults to the active `--tunnel` URL).
- `drop` — Unregister all webhooks (`DELETE /webhooks/v1/`).
- `stations` — Fetch current Weather Station & module readings (`GET /api/getstationsdata`).
- `test-local` — Send a signed `device_event` POST to `http://127.0.0.1:8080/webhook` to verify HMAC-SHA256 verification.
- `quit` — Shut down tunnel and exit.

All incoming webhook payloads are printed to the terminal and saved to `standalone_webhook/webhook_events.log`.

