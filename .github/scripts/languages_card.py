"""Render assets/languages.svg: the share of code by language across the owner's public repositories.

Replaces the hosted top-languages card, whose fixed GitHub language colors made
TypeScript, Python and PLpgSQL three near-identical blues. Colors here come from
the profile palette and are assigned by rank, so neighbours always contrast.

Usage: GITHUB_TOKEN=... python .github/scripts/languages_card.py <username> <output.svg>
"""

import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

MAX_LANGS = 6

# Ranked palette, chosen to stay distinct from each other on the dark green card.
PALETTE = ["#35D58A", "#F2C14E", "#5AB1EF", "#E07A5F", "#B48EF0", "#F5F4EC"]
OTHER_COLOR = "#5E7F73"

BG, BORDER, TITLE, TEXT, MUTED, TRACK = "#0B302B", "#1E5246", "#35D58A", "#D2DED7", "#8FA99D", "#123D35"


def api(path):
    req = urllib.request.Request(f"https://api.github.com{path}")
    req.add_header("Accept", "application/vnd.github+json")
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def language_bytes(user):
    totals = {}
    for repo in api(f"/users/{user}/repos?type=owner&per_page=100"):
        if repo["fork"] or repo["name"].lower() == user.lower():
            continue
        for lang, size in api(f"/repos/{repo['full_name']}/languages").items():
            totals[lang] = totals.get(lang, 0) + size
    return totals


def top_shares(totals):
    total = sum(totals.values())
    ranked = sorted(totals.items(), key=lambda kv: kv[1], reverse=True)
    shares = [(lang, size / total) for lang, size in ranked[:MAX_LANGS]]
    rest = sum(size for _, size in ranked[MAX_LANGS:])
    if rest:
        # Fold the tail into the last slot so the legend never exceeds six rows.
        shares = shares[: MAX_LANGS - 1] + [("Other", (rest + ranked[MAX_LANGS - 1][1]) / total)]
    return shares


def render(shares):
    width, height, pad = 495, 200, 25
    bar_y, bar_w, bar_h = 62, width - 2 * pad, 10
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="t d">',
        '<title id="t">Most Used Languages</title>',
        '<desc id="d">' + escape(", ".join(f"{lang} {share:.1%}" for lang, share in shares)) + "</desc>",
        "<style>text{font-family:'Segoe UI',Ubuntu,'Helvetica Neue',Arial,sans-serif}"
        f".title{{font-size:20px;font-weight:600;fill:{TITLE}}}"
        f".lang{{font-size:13px;fill:{TEXT}}}.pct{{font-size:13px;fill:{MUTED}}}</style>",
        f'<rect x="0.5" y="0.5" width="{width - 1}" height="{height - 1}" rx="8" fill="{BG}" stroke="{BORDER}"/>',
        f'<text class="title" x="{pad}" y="38">Most Used Languages</text>',
        f'<clipPath id="bar"><rect x="{pad}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5"/></clipPath>',
        f'<rect x="{pad}" y="{bar_y}" width="{bar_w}" height="{bar_h}" rx="5" fill="{TRACK}"/>',
        '<g clip-path="url(#bar)">',
    ]
    colors = [OTHER_COLOR if lang == "Other" else PALETTE[i] for i, (lang, _) in enumerate(shares)]
    x = pad
    for (lang, share), color in zip(shares, colors):
        w = share * bar_w
        # A 1px gap between segments keeps adjacent colors readable.
        parts.append(f'<rect x="{x:.2f}" y="{bar_y}" width="{max(w - 1, 0.5):.2f}" height="{bar_h}" fill="{color}"/>')
        x += w
    parts.append("</g>")

    col_x, row_y, row_h = [pad, pad + 235], 100, 30
    for i, ((lang, share), color) in enumerate(zip(shares, colors)):
        cx, cy = col_x[i % 2], row_y + (i // 2) * row_h
        parts.append(f'<circle cx="{cx + 6}" cy="{cy - 4}" r="6" fill="{color}"/>')
        parts.append(f'<text class="lang" x="{cx + 20}" y="{cy}">{escape(lang)}</text>')
        parts.append(f'<text class="pct" x="{cx + 215}" y="{cy}" text-anchor="end">{share:.1%}</text>')
    parts.append("</svg>")
    return "\n".join(parts) + "\n"


def main():
    user, out = sys.argv[1], sys.argv[2]
    svg = render(top_shares(language_bytes(user)))
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)


if __name__ == "__main__":
    main()
