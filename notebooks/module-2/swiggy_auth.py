"""One-shot OAuth 2.1 + PKCE login for the Swiggy MCP server.

Run this once. It opens a browser, you log in with phone and OTP, and the
resulting token is written to swiggy_token.json next to this file.

    uv run python notebooks/module-2/swiggy_auth.py

The token is a credential for your real Swiggy account. It is gitignored.
"""

import base64
import hashlib
import http.server
import json
import secrets
import threading
import urllib.parse
import webbrowser
from pathlib import Path

import requests

BASE = "https://mcp.swiggy.com"
RESOURCE = f"{BASE}/food"
PORT = 8765
REDIRECT_URI = f"http://localhost:{PORT}/callback"
TOKEN_PATH = Path(__file__).parent / "swiggy_token.json"

# Only tools. Widen to "mcp:tools mcp:resources mcp:prompts" if you need the rest.
SCOPE = "mcp:tools"


def make_pkce() -> tuple[str, str]:
    """Return a PKCE (verifier, S256 challenge) pair."""
    verifier = base64.urlsafe_b64encode(secrets.token_bytes(48)).decode().rstrip("=")
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def register_client() -> str:
    """Register via Dynamic Client Registration and return the client_id."""
    response = requests.post(
        f"{BASE}/auth/register",
        json={
            "client_name": "lc-foundations",
            "redirect_uris": [REDIRECT_URI],
            "grant_types": ["authorization_code", "refresh_token"],
            "response_types": ["code"],
            "token_endpoint_auth_method": "none",
            "scope": SCOPE,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["client_id"]


def catch_code(state: str) -> str:
    """Serve localhost until the browser redirects back, then return the code."""
    result = {}
    done = threading.Event()

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            query = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            result.update({k: v[0] for k, v in query.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h2>Done. You can close this tab.</h2>")
            done.set()

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("localhost", PORT), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    done.wait(timeout=300)
    server.shutdown()

    if result.get("state") != state:
        raise RuntimeError(f"State mismatch - possible CSRF. Got {result!r}")
    if "code" not in result:
        raise RuntimeError(f"No code returned: {result!r}")
    return result["code"]


def main():
    client_id = register_client()
    verifier, challenge = make_pkce()
    state = secrets.token_urlsafe(16)

    params = {
        "response_type": "code",
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "scope": SCOPE,
        "state": state,
        "code_challenge": challenge,
        "code_challenge_method": "S256",
        "resource": RESOURCE,
    }
    url = f"{BASE}/auth/authorize?{urllib.parse.urlencode(params)}"

    print("Opening browser. Log in with your phone number and OTP.")
    print(f"If nothing opens, paste this:\n\n{url}\n")
    webbrowser.open(url)

    code = catch_code(state)
    print("Got the code. Exchanging for a token.")

    response = requests.post(
        f"{BASE}/auth/token",
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": REDIRECT_URI,
            "client_id": client_id,
            "code_verifier": verifier,
            "resource": RESOURCE,
        },
        timeout=30,
    )
    response.raise_for_status()
    token = response.json()

    TOKEN_PATH.write_text(json.dumps(token, indent=2), encoding="utf-8")
    print(f"Token saved to {TOKEN_PATH}")
    print(f"Scope: {token.get('scope')}  expires_in: {token.get('expires_in')}")


if __name__ == "__main__":
    main()
