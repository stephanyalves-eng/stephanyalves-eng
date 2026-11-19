"""Rewrite the "Recent activity" list in README.md: the latest commit in each of the most recently updated projects.

Replaces the github-activity-readme action, which only lists pull requests, comments and
releases (almost all of the work here is commits) and left stale lines behind whenever the
list got shorter. The profile repository itself and commits by bots are left out.

Usage: GITHUB_TOKEN=... python .github/scripts/recent_activity.py <username> README.md
"""

import json
import os
import re
import sys
import urllib.request
from datetime import datetime

MAX_LINES = 5
MAX_MESSAGE = 90
START, END = "<!--START_SECTION:activity-->", "<!--END_SECTION:activity-->"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def is_bot(commit):
    login = (commit.get("author") or {}).get("login", "")
    name = commit["commit"]["author"]["name"]
    return login.endswith("[bot]") or name.endswith("[bot]") or name.endswith("-bot")


def latest_commits(user):
    repos = [r for r in api(f"/users/{user}/repos?type=owner&sort=pushed&per_page=100")
             if not r["fork"] and not r["private"] and r["name"].lower() != user.lower()]
    found = []
    for repo in repos:
        try:
            commits = api(f"/repos/{repo['full_name']}/commits?per_page=30")
        except urllib.error.HTTPError:  # empty repository
            continue
        mine = [c for c in commits if not is_bot(c) and (c.get("author") or {}).get("login", "").lower() == user.lower()]
        if mine:
            found.append((repo, mine[0]))
        if len(found) == MAX_LINES:
            break
    found.sort(key=lambda rc: rc[1]["commit"]["author"]["date"], reverse=True)
    return found


def line(i, repo, commit):
    msg = commit["commit"]["message"].splitlines()[0].strip()
    if len(msg) > MAX_MESSAGE:
        msg = msg[: MAX_MESSAGE - 1].rstrip() + "…"
    msg = re.sub(r"([\[\]\\`*_<>])", r"\\\1", msg)
    when = datetime.fromisoformat(commit["commit"]["author"]["date"].replace("Z", "+00:00"))
    date = f"{when:%b} {when.day}, {when.year}"
    return f"{i}. 🔨 [{repo['name']}]({repo['html_url']}): [{msg}]({commit['html_url']}) · <sub>{date}</sub>"


def main():
    user, readme = sys.argv[1], sys.argv[2]
    lines = [line(i + 1, repo, commit) for i, (repo, commit) in enumerate(latest_commits(user))]
    text = open(readme, encoding="utf-8").read()
    a, b = text.index(START) + len(START), text.index(END)
    # Replace the whole block so a shorter list never leaves old lines behind.
    text = text[:a] + "\n" + "\n".join(lines) + "\n" + text[b:]
    with open(readme, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


if __name__ == "__main__":
    main()
