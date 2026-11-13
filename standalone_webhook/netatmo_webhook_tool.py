#!/usr/bin/env python3
"""
Standalone Netatmo Webhook Listener & Tester (Runs locally on your Mac, no PG3/ISY)

Features:
- Pure Python 3 standard library (no pip packages required)
- Local HTTP webhook receiver with HMAC-SHA256 (X-Netatmo-secret) verification
- Optional built-in HTTPS tunnel via macOS ssh + localhost.run (--tunnel)
- Standalone OAuth2 Authorization Code flow + token refresh
- Direct Netatmo /webhooks/v1/ management (GET, POST, PUT, DELETE)
- Weather station data viewer (/api/getstationsdata)
"""

import argparse
import hashlib
import hmac
import json
import os
import re
import ssl
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

CLIENT_ID = os.environ.get("NETATMO_CLIENT_ID", "6aee280752c9011377071819")
CLIENT_SECRET = os.environ.get("NETATMO_CLIENT_SECRET", "MUwesrYBstni3Gg9WTFUK42tf9bJMGRvjCgCvgmFfV509")
SCOPE = "read_station"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TOKEN_FILE = os.path.join(BASE_DIR, "tokens.json")
EVENTS_LOG_FILE = os.path.join(BASE_DIR, "webhook_events.log")
PG3_SLOT17_LOG = "/Volumes/ns/0021b902748c_17/logs/debug.log"

SSL_CTX = ssl._create_unverified_context()


def log(msg: str) -> None:
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    print(f"[{ts}] {msg}", flush=True)


def verify_signature(raw_body: bytes, secret_header: str, client_secret: str) -> bool:
    if not secret_header or not client_secret:
        return False
    computed = hmac.new(client_secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest().lower()
    return hmac.compare_digest(computed, secret_header.strip().lower())


class WebhookHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        resp = {"status": "ok", "message": "Netatmo standalone webhook listener is running"}
        self.wfile.write(json.dumps(resp).encode("utf-8"))

    def do_POST(self):
        length = int(self.headers.get("Content-Length", "0") or 0)
        raw_body = self.rfile.read(length) if length > 0 else b""

        # Respond immediately with 200 OK so Netatmo never times out
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b'{"status":"ok"}')

        headers_dict = {k: v for k, v in self.headers.items()}
        secret_hdr = next((v for k, v in headers_dict.items() if k.lower() == "x-netatmo-secret"), None)
        sig_valid = verify_signature(raw_body, secret_hdr, CLIENT_SECRET) if secret_hdr else None

        body_text = raw_body.decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body_text)
            pretty_body = json.dumps(parsed, indent=2)
        except Exception:
            pretty_body = body_text

        source_ip = headers_dict.get("X-Forwarded-For") or headers_dict.get("X-Real-IP") or self.client_address[0]
        user_agent = headers_dict.get("User-Agent", "Unknown")

        banner = "=" * 70
        event_text = (
            f"\n{banner}\n"
            f"INCOMING WEBHOOK POST {self.path}\n"
            f"Time       : {datetime.now().isoformat()}\n"
            f"Source IP  : {source_ip}\n"
            f"User-Agent : {user_agent}\n"
            f"HMAC Header: {'present' if secret_hdr else 'none'} | Valid: {sig_valid}\n"
            f"Body:\n{pretty_body}\n"
            f"{banner}"
        )
        print(event_text, flush=True)

        try:
            with open(EVENTS_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(event_text + "\n")
        except Exception as e:
            log(f"Warning: could not write to {EVENTS_LOG_FILE}: {e}")


class NetatmoClient:
    def __init__(self):
        self.tokens = self._load_tokens()

    def _load_tokens(self) -> dict:
        if os.path.exists(TOKEN_FILE):
            try:
                with open(TOKEN_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                log(f"Failed to load {TOKEN_FILE}: {e}")
        return {}

    def _save_tokens(self) -> None:
        with open(TOKEN_FILE, "w", encoding="utf-8") as f:
            json.dump(self.tokens, f, indent=2)
        log(f"Saved tokens to {TOKEN_FILE}")

    def import_from_pg3_log(self, log_path: str = PG3_SLOT17_LOG) -> bool:
        if not os.path.exists(log_path):
            log(f"Log file not found: {log_path}")
            return False
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        for line in reversed(lines):
            m = re.search(r"'Authorization':\s*'Bearer\s+([^']+)'", line)
            if m:
                token = m.group(1).strip()
                self.tokens = {
                    "access_token": token,
                    "imported_from": log_path,
                    "imported_at": datetime.now().isoformat(),
                }
                self._save_tokens()
                log(f"Imported Bearer token: {token[:20]}... (len={len(token)})")
                return True
        log("No Bearer token found in log.")
        return False

    def start_oauth_flow(self, redirect_uri: str = "http://localhost:8765/callback") -> bool:
        state = f"netatmo_{int(time.time())}"
        auth_params = urllib.parse.urlencode({
            "client_id": CLIENT_ID,
            "redirect_uri": redirect_uri,
            "scope": SCOPE,
            "state": state,
        })
        auth_url = f"https://api.netatmo.com/oauth2/authorize?{auth_params}"

        parsed_redir = urllib.parse.urlparse(redirect_uri)
        code_holder = {"code": None, "error": None}

        if parsed_redir.hostname in ("localhost", "127.0.0.1") and parsed_redir.port:
            class CallbackHandler(BaseHTTPRequestHandler):
                def log_message(self, format, *args):
                    pass

                def do_GET(self):
                    q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
                    code_holder["code"] = q.get("code", [None])[0]
                    code_holder["error"] = q.get("error", [None])[0]
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"<h2>Authorization received. You can close this tab and return to the terminal.</h2>")

            srv = ThreadingHTTPServer((parsed_redir.hostname, parsed_redir.port), CallbackHandler)
            srv.timeout = 120
            log("Opening browser for Netatmo OAuth2 authorization...")
            log(f"URL: {auth_url}")
            webbrowser.open(auth_url)
            log(f"Waiting for OAuth callback on {redirect_uri} (timeout 120s)...")
            srv.handle_request()
            srv.server_close()
        else:
            log(f"Open this URL in your browser to authorize:\n  {auth_url}")
            redirected = input("Paste the full redirected URL (or just the 'code=' value): ").strip()
            if "code=" in redirected:
                q = urllib.parse.parse_qs(urllib.parse.urlparse(redirected).query)
                code_holder["code"] = q.get("code", [None])[0]
            else:
                code_holder["code"] = redirected

        if code_holder["error"]:
            log(f"OAuth error: {code_holder['error']}")
            return False
        if not code_holder["code"]:
            log("No authorization code received.")
            return False

        return self.exchange_code(code_holder["code"], redirect_uri)

    def exchange_code(self, code: str, redirect_uri: str) -> bool:
        data = urllib.parse.urlencode({
            "grant_type": "authorization_code",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "redirect_uri": redirect_uri,
            "scope": SCOPE,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.netatmo.com/oauth2/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
                tok = json.loads(resp.read().decode("utf-8"))
                tok["expires_at"] = time.time() + int(tok.get("expires_in", 10800))
                self.tokens = tok
                self._save_tokens()
                log("OAuth2 token exchange succeeded!")
                return True
        except urllib.error.HTTPError as e:
            log(f"Token exchange failed HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")
            return False

    def refresh_access_token(self) -> bool:
        refresh_tok = self.tokens.get("refresh_token")
        if not refresh_tok:
            return False
        data = urllib.parse.urlencode({
            "grant_type": "refresh_token",
            "refresh_token": refresh_tok,
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
        }).encode("utf-8")
        req = urllib.request.Request(
            "https://api.netatmo.com/oauth2/token",
            data=data,
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
                tok = json.loads(resp.read().decode("utf-8"))
                tok["expires_at"] = time.time() + int(tok.get("expires_in", 10800))
                self.tokens = tok
                self._save_tokens()
                log("Access token refreshed.")
                return True
        except urllib.error.HTTPError as e:
            log(f"Token refresh failed HTTP {e.code}: {e.read().decode('utf-8', errors='replace')}")
            return False

    def get_access_token(self) -> str:
        if not self.tokens.get("access_token"):
            raise RuntimeError("No access token available. Run 'auth' or 'import-token' first.")
        expires_at = self.tokens.get("expires_at")
        if expires_at and time.time() > (expires_at - 60) and self.tokens.get("refresh_token"):
            self.refresh_access_token()
        return self.tokens["access_token"]

    def api_call(self, method: str, url: str, body: dict = None):
        token = self.get_access_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "NetatmoStandaloneWebhook/1.0",
        }
        data = json.dumps(body).encode("utf-8") if body is not None else None
        req = urllib.request.Request(url, data=data, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=15, context=SSL_CTX) as resp:
                text = resp.read().decode("utf-8")
                return resp.status, json.loads(text) if text else {}
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")
            try:
                return e.code, json.loads(text)
            except Exception:
                return e.code, text
        except Exception as e:
            return 0, str(e)

    def get_webhooks(self):
        st, res = self.api_call("GET", "https://api.netatmo.com/webhooks/v1/")
        log(f"GET /webhooks/v1/ -> HTTP {st}: {json.dumps(res)}")
        return st, res

    def drop_webhooks(self):
        st, res = self.api_call("DELETE", "https://api.netatmo.com/webhooks/v1/")
        log(f"DELETE /webhooks/v1/ -> HTTP {st}: {json.dumps(res)}")
        st2, res2 = self.api_call("POST", "https://api.netatmo.com/api/dropwebhook")
        log(f"POST /api/dropwebhook -> HTTP {st2}: {json.dumps(res2)}")
        return st, res

    def register_webhook(self, webhook_url: str):
        log(f"Dropping previous webhooks before registering: {webhook_url}")
        self.drop_webhooks()
        time.sleep(1)

        st, res = self.api_call("POST", "https://api.netatmo.com/webhooks/v1/", body={"url": webhook_url})
        log(f"POST /webhooks/v1/ -> HTTP {st}: {json.dumps(res)}")
        if st in (200, 201):
            return True

        st_put, res_put = self.api_call("PUT", "https://api.netatmo.com/webhooks/v1/", body={"url": webhook_url})
        log(f"PUT /webhooks/v1/ -> HTTP {st_put}: {json.dumps(res_put)}")
        if st_put in (200, 201):
            return True

        encoded = urllib.parse.quote_plus(webhook_url)
        st_leg, res_leg = self.api_call("POST", f"https://api.netatmo.com/api/addwebhook?url={encoded}")
        log(f"POST /api/addwebhook -> HTTP {st_leg}: {json.dumps(res_leg)}")
        return st_leg == 200

    def get_stations(self):
        st, res = self.api_call("GET", "https://api.netatmo.com/api/getstationsdata")
        log(f"GET /api/getstationsdata -> HTTP {st}")
        if st == 200 and isinstance(res, dict):
            devices = res.get("body", {}).get("devices", [])
            for dev in devices:
                dash = dev.get("dashboard_data", {})
                print(
                    f"  Station: {dev.get('station_name')} ({dev.get('_id')}) | "
                    f"home_id={dev.get('home_id')} | Temp={dash.get('Temperature')} | "
                    f"CO2={dash.get('CO2')} | Hum={dash.get('Humidity')} | ts={dash.get('time_utc')}"
                )
                for mod in dev.get("modules", []):
                    mdash = mod.get("dashboard_data", {})
                    print(
                        f"    Module: {mod.get('module_name')} ({mod.get('_id')}, {mod.get('type')}) | "
                        f"reachable={mod.get('reachable')} | Temp={mdash.get('Temperature')} | ts={mdash.get('time_utc')}"
                    )
        else:
            print(res)


def start_ssh_tunnel(port: int):
    """Start a built-in HTTPS reverse tunnel via localhost.run using macOS ssh."""
    log(f"Starting SSH reverse tunnel (localhost.run -> 127.0.0.1:{port})...")
    proc = subprocess.Popen(
        [
            "ssh",
            "-T",
            "-o", "StrictHostKeyChecking=no",
            "-o", "BatchMode=yes",
            "-o", "ServerAliveInterval=30",
            "-R", f"80:localhost:{port}",
            "nokey@localhost.run",
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    url_holder = {"url": None}
    lines_seen = []

    def reader():
        for line in proc.stdout:
            clean = re.sub(r"\x1b\[[0-9;]*[mK]", "", line).strip()
            if clean:
                lines_seen.append(clean)
            m = re.search(r"(https://[a-zA-Z0-9.-]+\.lhr\.life)", clean)
            if m and not url_holder["url"]:
                url_holder["url"] = m.group(1) + "/webhook"
                log(f"Public HTTPS tunnel ready: {url_holder['url']}")
        rc = proc.wait()
        if url_holder["url"]:
            log(f"WARNING: SSH tunnel exited (code {rc}). {url_holder['url']} is no longer reachable.")

    threading.Thread(target=reader, daemon=True).start()
    for _ in range(30):
        if url_holder["url"] or proc.poll() is not None:
            break
        time.sleep(0.5)
    if not url_holder["url"]:
        log(f"Warning: SSH tunnel did not return a URL yet. Output: {lines_seen[-5:]}")
    return proc, url_holder["url"]


def send_local_test(port: int):
    payload = {
        "push_type": "device_event",
        "home_id": "test_home",
        "device_id": "70:ee:50:29:2f:e0",
        "extra_params": {
            "modules": [{"id": "70:ee:50:29:2f:e0", "type": "NAMain", "temperature": 20.5, "co2": 450}]
        },
    }
    raw = json.dumps(payload).encode("utf-8")
    sig = hmac.new(CLIENT_SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest().lower()
    req = urllib.request.Request(
        f"http://127.0.0.1:{port}/webhook",
        data=raw,
        headers={"Content-Type": "application/json", "X-Netatmo-secret": sig},
        method="POST",
    )
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(req, timeout=5) as resp:
        log(f"Local test POST -> HTTP {resp.status}: {resp.read().decode('utf-8')}")


def main():
    parser = argparse.ArgumentParser(description="Standalone Netatmo Webhook Listener & Tester")
    parser.add_argument("--port", type=int, default=8080, help="Local HTTP port to listen on (default: 8080)")
    parser.add_argument("--tunnel", action="store_true", help="Open a public HTTPS tunnel via macOS ssh + localhost.run")
    parser.add_argument("--webhook-url", type=str, help="Public HTTPS URL to register immediately on startup")
    parser.add_argument("--import-log", action="store_true", help="Import active token from PG3 slot 17 debug.log")
    args = parser.parse_args()

    server = ThreadingHTTPServer(("0.0.0.0", args.port), WebhookHandler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    log(f"Webhook HTTP listener started on http://0.0.0.0:{args.port}/webhook")

    tunnel_proc = None
    tunnel_url = None
    if args.tunnel:
        tunnel_proc, tunnel_url = start_ssh_tunnel(args.port)

    client = NetatmoClient()
    if args.import_log and not client.tokens.get("access_token"):
        client.import_from_pg3_log()

    target_url = args.webhook_url or tunnel_url
    if target_url and client.tokens.get("access_token"):
        client.register_webhook(target_url)

    print(
        "\nCommands:\n"
        "  auth [redirect_uri]   - Run OAuth2 browser login (default: http://localhost:8765/callback)\n"
        "  import-token          - Import current Bearer token from PG3 slot 17 debug.log\n"
        "  status                - Show registered webhooks on Netatmo (GET /webhooks/v1/)\n"
        "  register [https_url]  - Register public HTTPS URL (defaults to active tunnel URL)\n"
        "  drop                  - Drop all webhooks on Netatmo\n"
        "  stations              - Fetch current Weather Station & module readings\n"
        "  check-tunnel [url]    - Test whether the public HTTPS tunnel reaches this listener\n"
        "  test-local            - Send a signed test POST to the local listener\n"
        "  quit                  - Exit\n"
    )

    try:
        while True:
            cmd_line = input("netatmo> ").strip()
            if not cmd_line:
                continue
            parts = cmd_line.split()
            cmd = parts[0].lower()

            try:
                if cmd in ("quit", "exit", "q"):
                    break
                elif cmd == "auth":
                    redir = parts[1] if len(parts) > 1 else "http://localhost:8765/callback"
                    client.start_oauth_flow(redir)
                elif cmd == "import-token":
                    client.import_from_pg3_log()
                elif cmd == "status":
                    client.get_webhooks()
                elif cmd == "register":
                    url_to_reg = parts[1] if len(parts) > 1 else tunnel_url
                    if not url_to_reg:
                        print("Usage: register https://<your-public-tunnel-host>/webhook (or start with --tunnel)")
                    else:
                        client.register_webhook(url_to_reg)
                elif cmd == "drop":
                    client.drop_webhooks()
                elif cmd == "stations":
                    client.get_stations()
                elif cmd == "check-tunnel":
                    url_to_check = parts[1] if len(parts) > 1 else tunnel_url
                    if not url_to_check:
                        print("Usage: check-tunnel [https_url] (or start with --tunnel)")
                    else:
                        req = urllib.request.Request(url_to_check, method="GET")
                        with urllib.request.urlopen(req, timeout=10, context=SSL_CTX) as resp:
                            log(f"Tunnel check {url_to_check} -> HTTP {resp.status}: {resp.read().decode('utf-8', errors='replace')}")
                elif cmd == "test-local":
                    send_local_test(args.port)
                else:
                    print(f"Unknown command: {cmd}")
            except Exception as e:
                log(f"Command error: {e}")
    except (KeyboardInterrupt, EOFError):
        pass
    finally:
        if tunnel_proc:
            tunnel_proc.terminate()
        server.shutdown()
        log("Stopped.")


if __name__ == "__main__":
    main()
