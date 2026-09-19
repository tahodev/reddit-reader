#!/usr/bin/env python3
"""reddit-reader: personal Reddit CLI reader.

Local, personal-use script for my own account (u/Wild-Rush6576). Reads
threads/comments from my subscribed subreddits for personal research.
Writes are manual only: the comment command prints the exact text and
posts only after interactive confirmation. No scheduled, automatic, or
bulk posting. Caps itself at ~100 Reddit API calls per day.
"""

import json
import os
import secrets
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlencode, urlparse

import requests

AUTH_URL = "https://www.reddit.com/api/v1/authorize"
TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
API = "https://oauth.reddit.com"
REDIRECT_URI = "http://localhost:8080"
SCOPES = ["identity", "mysubreddits", "read", "submit"]

CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET", "")
USER_AGENT = os.environ.get(
    "REDDIT_USER_AGENT", "script:reddit-reader:v0.1.0 (by /u/Wild-Rush6576)"
)

TOKEN_FILE = Path(".reddit_reader_token.json")
STATE_FILE = Path(".reddit_reader_state.json")
DAILY_CALL_CAP = 100  # personal ceiling, far below Reddit's rate limits


def _load_json(path):
    if path.exists():
        return json.loads(path.read_text())
    return {}


def _save_json(path, data):
    path.write_text(json.dumps(data, indent=2))


def _check_daily_budget(state):
    today = time.strftime("%Y-%m-%d")
    if state.get("day") != today:
        state["day"], state["calls"] = today, 0
    if state["calls"] >= DAILY_CALL_CAP:
        sys.exit(f"Daily API budget of {DAILY_CALL_CAP} calls used up. Try again tomorrow.")
    state["calls"] += 1
    _save_json(STATE_FILE, state)


def _exchange_code(code):
    resp = requests.post(
        TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "authorization_code", "code": code, "redirect_uri": REDIRECT_URI},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _refresh_token(refresh_token):
    resp = requests.post(
        TOKEN_URL,
        auth=(CLIENT_ID, CLIENT_SECRET),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers={"User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def _access_token():
    saved = _load_json(TOKEN_FILE)
    if not saved.get("refresh_token"):
        sys.exit("Not authorized yet. Run: python reddit_reader.py auth")
    if saved.get("access_token") and saved.get("expires_at", 0) > time.time() + 60:
        return saved["access_token"]
    fresh = _refresh_token(saved["refresh_token"])
    saved.update(
        access_token=fresh["access_token"],
        expires_at=time.time() + fresh.get("expires_in", 3600),
    )
    _save_json(TOKEN_FILE, saved)
    return saved["access_token"]


def api_get(path, **params):
    state = _load_json(STATE_FILE)
    _check_daily_budget(state)
    resp = requests.get(
        f"{API}{path}",
        params=params,
        headers={"Authorization": f"bearer {_access_token()}", "User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def cmd_auth():
    if not CLIENT_ID:
        sys.exit("Set REDDIT_CLIENT_ID (and REDDIT_CLIENT_SECRET) first.")
    state = secrets.token_urlsafe(16)
    url = AUTH_URL + "?" + urlencode({
        "client_id": CLIENT_ID,
        "response_type": "code",
        "state": state,
        "redirect_uri": REDIRECT_URI,
        "duration": "permanent",
        "scope": " ".join(SCOPES),
    })

    class Handler(BaseHTTPRequestHandler):
        code = None

        def do_GET(self):
            qs = parse_qs(urlparse(self.path).query)
            if qs.get("state", [""])[0] == state and "code" in qs:
                Handler.code = qs["code"][0]
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"reddit-reader: authorization received. You can close this tab.")
            else:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(b"State mismatch or missing code.")

        def log_message(self, *args):
            pass

    server = HTTPServer(("localhost", 8080), Handler)
    print("Opening Reddit consent page in your browser...")
    webbrowser.open(url)
    server.handle_request()  # one request is enough: the redirect with the code
    if not Handler.code:
        sys.exit("No authorization code received.")
    tokens = _exchange_code(Handler.code)
    _save_json(TOKEN_FILE, {
        "refresh_token": tokens["refresh_token"],
        "access_token": tokens["access_token"],
        "expires_at": time.time() + tokens.get("expires_in", 3600),
    })
    me = api_get("/api/v1/me")
    print(f"Authorized as u/{me['name']}.")


def cmd_subs():
    subs = api_get("/subreddits/mine/subscriber", limit=100)
    for s in subs["data"]["children"]:
        print(s["data"]["display_name"])


def cmd_hot(subreddit, limit=10):
    data = api_get(f"/r/{subreddit}/hot", limit=limit)
    for post in data["data"]["children"]:
        d = post["data"]
        print(f"{d['id']}  [{d['score']:>5}]  {d['title']}")


def cmd_comments(post_id, limit=20):
    data = api_get(f"/comments/{post_id}", limit=limit, depth=2)
    post, comments = data[0]["data"]["children"][0]["data"], data[1]["data"]["children"]
    print(f"# {post['title']}\n")
    for c in comments:
        d = c.get("data", {})
        if d.get("body"):
            print(f"u/{d.get('author')} [{d.get('score')}]")
            print(d["body"].strip(), "\n")


def cmd_comment(post_id):
    """Manual posting only: I type the text, review it, and confirm by hand."""
    print("Write your comment. End with a single '.' on its own line:")
    lines = []
    for line in sys.stdin:
        if line.strip() == ".":
            break
        lines.append(line.rstrip("\n"))
    text = "\n".join(lines).strip()
    if not text:
        sys.exit("Empty comment, nothing posted.")
    print("\n--- you are about to post this as u/Wild-Rush6576 ---")
    print(text)
    print("-----------------------------------------------------")
    if input("Post this comment? Type 'yes' to send: ").strip().lower() != "yes":
        sys.exit("Aborted, nothing posted.")
    state = _load_json(STATE_FILE)
    _check_daily_budget(state)
    resp = requests.post(
        f"{API}/api/comment",
        data={"thing_id": f"t3_{post_id}", "text": text},
        headers={"Authorization": f"bearer {_access_token()}", "User-Agent": USER_AGENT},
        timeout=30,
    )
    resp.raise_for_status()
    print("Posted.")


HELP = """reddit-reader: personal Reddit CLI reader.

usage:
  python reddit_reader.py auth                  authorize with Reddit (one-time OAuth setup)
  python reddit_reader.py subs                  list my subscribed subreddits
  python reddit_reader.py hot <subreddit> [n]   show hot threads in a subreddit (default 10)
  python reddit_reader.py comments <post_id> [n] show comments on a thread (default 20)
  python reddit_reader.py comment <post_id>     write a comment by hand, review, confirm
  python reddit_reader.py help                  show this help

Read-only by default; the comment command is the only write and always
requires typing the text and confirming it interactively.
"""

if __name__ == "__main__":
    args = sys.argv[1:]
    if not args:
        sys.exit(HELP)
    cmd, rest = args[0], args[1:]
    if cmd in ("help", "--help", "-h"):
        print(HELP)
        sys.exit(0)
    if cmd == "auth":
        cmd_auth()
    elif cmd == "subs":
        cmd_subs()
    elif cmd == "hot" and rest:
        cmd_hot(rest[0], int(rest[1]) if len(rest) > 1 else 10)
    elif cmd == "comments" and rest:
        cmd_comments(rest[0], int(rest[1]) if len(rest) > 1 else 20)
    elif cmd == "comment" and rest:
        cmd_comment(rest[0])
    else:
        sys.exit(HELP)
