#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "data/profile.json").read_text(encoding="utf-8"))
OWNER = CONFIG["owner"]
MAX_RECENT = int(CONFIG.get("max_recent_repositories", 5))
EXCLUDED = set(CONFIG.get("exclude_repositories", []))


def github_json(url: str):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{OWNER}-dynamic-profile",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        return json.load(response)


def clean(text: str | None) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def short_date(value: str | None) -> str:
    if not value:
        return "—"
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%d")


def load_public_repos():
    url = f"https://api.github.com/users/{OWNER}/repos?per_page=100&sort=pushed&direction=desc&type=owner"
    repos = github_json(url)
    visible = [
        r for r in repos
        if not r.get("fork") and not r.get("archived") and r.get("name") not in EXCLUDED
    ]
    return visible


def render_markdown(repos) -> str:
    lines = [
        "_Generated from public GitHub repository metadata. Updates only when the public signal changes._",
        "",
        "| Recent public repository | Language | Stars | Latest public push |",
        "| --- | --- | ---: | --- |",
    ]
    for repo in repos[:MAX_RECENT]:
        name = clean(repo["name"])
        url = repo["html_url"]
        language = clean(repo.get("language")) or "—"
        stars = int(repo.get("stargazers_count", 0))
        pushed = short_date(repo.get("pushed_at"))
        lines.append(f"| **[{name}]({url})** | {language} | {stars} | `{pushed}` |")
    return "\n".join(lines)


def replace_block(readme: str, body: str) -> str:
    pattern = r"<!-- PUBLIC-ACTIVITY:START -->.*?<!-- PUBLIC-ACTIVITY:END -->"
    replacement = f"<!-- PUBLIC-ACTIVITY:START -->\n{body}\n<!-- PUBLIC-ACTIVITY:END -->"
    updated, count = re.subn(pattern, replacement, readme, flags=re.S)
    if count != 1:
        raise RuntimeError("Expected exactly one PUBLIC-ACTIVITY block in README.md")
    return updated


def render_svg(repos) -> str:
    rows = repos[:MAX_RECENT]
    height = 150 + len(rows) * 54
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Public build signal</title>',
        '<desc id="desc">Recent public repositories generated from GitHub metadata.</desc>',
        f'<rect width="1200" height="{height}" rx="22" fill="#0d1117" stroke="#30363d"/>',
        '<text x="52" y="58" fill="#f0f6fc" font-family="Arial" font-size="25" font-weight="700">PUBLIC BUILD SIGNAL // LIVE</text>',
        '<text x="52" y="88" fill="#8b949e" font-family="monospace" font-size="15">RECENT PUBLIC REPOSITORIES · GENERATED FROM GITHUB METADATA</text>',
    ]
    y = 132
    for index, repo in enumerate(rows, start=1):
        name = html.escape(str(repo["name"]))
        language = html.escape(str(repo.get("language") or "—"))
        pushed = html.escape(short_date(repo.get("pushed_at")))
        stars = int(repo.get("stargazers_count", 0))
        parts.extend([
            f'<circle cx="60" cy="{y - 5}" r="6" fill="#3fb950"/>',
            f'<text x="84" y="{y}" fill="#f0f6fc" font-family="Arial" font-size="18" font-weight="700">{index:02d}  {name}</text>',
            f'<text x="720" y="{y}" fill="#8b949e" font-family="monospace" font-size="15">{language}</text>',
            f'<text x="900" y="{y}" fill="#8b949e" font-family="monospace" font-size="15">★ {stars}</text>',
            f'<text x="1000" y="{y}" fill="#58a6ff" font-family="monospace" font-size="15">{pushed}</text>',
        ])
        y += 54
    parts.append('</svg>')
    return "".join(parts) + "\n"


def main() -> None:
    repos = load_public_repos()
    if not repos:
        raise RuntimeError("No public repositories returned by GitHub API")

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme_path.write_text(replace_block(readme, render_markdown(repos)), encoding="utf-8")

    svg_path = ROOT / "assets/dynamic/public-signal.svg"
    svg_path.parent.mkdir(parents=True, exist_ok=True)
    svg_path.write_text(render_svg(repos), encoding="utf-8")


if __name__ == "__main__":
    main()
