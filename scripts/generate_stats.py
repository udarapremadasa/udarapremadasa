#!/usr/bin/env python3
"""Generate gruvbox nvim-style GitHub stat cards (dark + light) as SVGs.

Runs in GitHub Actions with GITHUB_TOKEN. Use --mock to render sample data locally.
"""
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

USER = "udarapremadasa"
OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

DARK = {
    "bg": "#282828", "bg_h": "#1d2021", "bg1": "#3c3836", "bg2": "#504945",
    "fg": "#ebdbb2", "fg4": "#a89984", "gray": "#928374", "num": "#7c6f64",
    "red": "#fb4934", "green": "#b8bb26", "yellow": "#fabd2f", "blue": "#83a598",
    "purple": "#d3869b", "aqua": "#8ec07c", "orange": "#fe8019", "border": "#504945",
    "mode_bg": "#a89984", "mode_fg": "#282828", "suffix": "dark",
}
LIGHT = {
    "bg": "#fbf1c7", "bg_h": "#f2e5bc", "bg1": "#ebdbb2", "bg2": "#d5c4a1",
    "fg": "#3c3836", "fg4": "#7c6f64", "gray": "#928374", "num": "#a89984",
    "red": "#9d0006", "green": "#79740e", "yellow": "#b57614", "blue": "#076678",
    "purple": "#8f3f71", "aqua": "#427b58", "orange": "#af3a03", "border": "#d5c4a1",
    "mode_bg": "#7c6f64", "mode_fg": "#fbf1c7", "suffix": "light",
}

LANG_COLOR_KEYS = ["yellow", "blue", "green", "orange", "aqua", "purple", "red"]

QUERY = """
query($login: String!) {
  user(login: $login) {
    followers { totalCount }
    pullRequests { totalCount }
    issues { totalCount }
    contributionsCollection {
      totalCommitContributions
      restrictedContributionsCount
      contributionCalendar { totalContributions }
    }
    repositoriesContributedTo(contributionTypes: [COMMIT, PULL_REQUEST, ISSUE, REPOSITORY]) { totalCount }
    repositories(first: 100, ownerAffiliations: OWNER, isFork: false) {
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) {
          edges { size node { name } }
        }
      }
    }
  }
}
"""


def fetch_stats():
    token = os.environ["GITHUB_TOKEN"]
    body = json.dumps({"query": QUERY, "variables": {"login": USER}}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=body,
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as r:
        data = json.load(r)
    if "errors" in data:
        raise SystemExit(f"GraphQL errors: {data['errors']}")
    u = data["data"]["user"]

    langs = {}
    stars = 0
    for repo in u["repositories"]["nodes"]:
        stars += repo["stargazerCount"]
        for e in repo["languages"]["edges"]:
            langs[e["node"]["name"]] = langs.get(e["node"]["name"], 0) + e["size"]

    cc = u["contributionsCollection"]
    return {
        "year": datetime.now(timezone.utc).year,
        "stars": stars,
        "commits": cc["totalCommitContributions"] + cc["restrictedContributionsCount"],
        "contributions": cc["contributionCalendar"]["totalContributions"],
        "prs": u["pullRequests"]["totalCount"],
        "issues": u["issues"]["totalCount"],
        "contributed_to": u["repositoriesContributedTo"]["totalCount"],
        "followers": u["followers"]["totalCount"],
        "langs": sorted(langs.items(), key=lambda kv: -kv[1])[:6],
    }


def mock_stats():
    return {
        "year": datetime.now(timezone.utc).year,
        "stars": 12, "commits": 340, "contributions": 512, "prs": 25,
        "issues": 8, "contributed_to": 6, "followers": 3,
        "langs": [("TypeScript", 52000), ("C++", 31000), ("Go", 18000),
                  ("Python", 12000), ("Lua", 6000), ("HTML", 4000)],
    }


def window(p, w, h, title, body, position):
    """nvim float-window chrome around card body."""
    return f'''<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" xmlns="http://www.w3.org/2000/svg" font-family="ui-monospace,SFMono-Regular,'SF Mono',Menlo,Consolas,'Liberation Mono',monospace" xml:space="preserve">
  <defs><clipPath id="win"><rect width="{w}" height="{h}" rx="8"/></clipPath></defs>
  <g clip-path="url(#win)">
    <rect width="{w}" height="{h}" fill="{p['bg']}"/>
    <rect width="{w}" height="30" fill="{p['bg_h']}"/>
    <rect width="120" height="30" fill="{p['bg']}"/>
    <rect width="120" height="2" fill="{p['yellow']}"/>
    <text x="60" y="20" font-size="12" fill="{p['fg']}" text-anchor="middle">{title}</text>
{body}
    <rect x="0" y="{h - 26}" width="{w}" height="26" fill="{p['bg1']}"/>
    <rect x="0" y="{h - 26}" width="74" height="26" fill="{p['mode_bg']}"/>
    <text x="37" y="{h - 9}" font-size="11" font-weight="bold" fill="{p['mode_fg']}" text-anchor="middle">NORMAL</text>
    <text x="84" y="{h - 9}" font-size="11" fill="{p['fg4']}">{title}</text>
    <text x="{w - 12}" y="{h - 9}" font-size="11" fill="{p['fg4']}" text-anchor="end">{position}</text>
  </g>
  <rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="8" fill="none" stroke="{p['border']}"/>
</svg>
'''


def stats_card(s, p):
    w, h = 440, 210
    rows = [
        ("stars", s["stars"], "yellow"),
        ("commits", s["commits"], "green"),
        ("contributions", s["contributions"], "aqua"),
        ("pull_requests", s["prs"], "blue"),
        ("issues", s["issues"], "purple"),
        ("followers", s["followers"], "orange"),
    ]
    pad = max(len(r[0]) for r in rows)
    lines = [f'    <text x="46" y="52" font-size="13" fill="{p["gray"]}" font-style="italic">-- {s["year"]} · github.com/{USER}</text>']
    y = 76
    for i, (k, v, color) in enumerate(rows):
        lines.append(f'    <text x="24" y="{y}" font-size="13" fill="{p["num"]}" text-anchor="end">{i + 1}</text>')
        lines.append(
            f'    <text x="46" y="{y}" font-size="13" fill="{p["fg"]}">{k.ljust(pad)} '
            f'<tspan fill="{p["orange"]}">=</tspan> <tspan fill="{p[color]}" font-weight="bold">{v:,}</tspan>,</text>'
        )
        y += 20
    body = "\n".join(lines)
    return window(p, w, h, "stats.lua", body, f"{len(rows)}:1")


def langs_card(s, p):
    w, h = 440, 210
    total = sum(v for _, v in s["langs"]) or 1
    bar_x, bar_w = 190, 160
    lines = [f'    <text x="46" y="52" font-size="13" fill="{p["gray"]}" font-style="italic">-- most used languages</text>']
    y = 76
    for i, (name, size) in enumerate(s["langs"]):
        pct = 100.0 * size / total
        color = p[LANG_COLOR_KEYS[i % len(LANG_COLOR_KEYS)]]
        fill_w = max(3, round(bar_w * pct / 100))
        lines.append(f'    <text x="24" y="{y}" font-size="13" fill="{p["num"]}" text-anchor="end">{i + 1}</text>')
        lines.append(f'    <text x="46" y="{y}" font-size="13" fill="{p["fg"]}">{name}</text>')
        lines.append(f'    <rect x="{bar_x}" y="{y - 10}" width="{bar_w}" height="10" rx="3" fill="{p["bg1"]}"/>')
        lines.append(f'    <rect x="{bar_x}" y="{y - 10}" width="{fill_w}" height="10" rx="3" fill="{color}"/>')
        lines.append(f'    <text x="{bar_x + bar_w + 14}" y="{y}" font-size="12" fill="{p["fg4"]}">{pct:.1f}%</text>')
        y += 20
    body = "\n".join(lines)
    return window(p, w, h, "languages.lua", body, f"{len(s['langs'])}:1")


def main():
    s = mock_stats() if "--mock" in sys.argv else fetch_stats()
    os.makedirs(OUT_DIR, exist_ok=True)
    for p in (DARK, LIGHT):
        for name, svg in (("stats", stats_card(s, p)), ("langs", langs_card(s, p))):
            path = os.path.join(OUT_DIR, f"{name}-{p['suffix']}.svg")
            with open(path, "w") as f:
                f.write(svg)
            print(f"wrote {path}")


if __name__ == "__main__":
    main()
