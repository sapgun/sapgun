#!/usr/bin/env python3
from __future__ import annotations

import html
import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / "data/profile.json").read_text(encoding="utf-8"))
OWNER = CONFIG["owner"]
MAX_RECENT = int(CONFIG.get("max_recent_repositories", 6))
EXCLUDED = set(CONFIG.get("exclude_repositories", []))
SIGNAL_REPOS = CONFIG.get("signal_repositories", [])
RESEARCH_REPOS = CONFIG.get("research_repositories", [])
RELEASE_REPOS = CONFIG.get("release_repositories", [])
FEATURED = CONFIG.get("featured_projects", [])


def github_json(url: str, optional: bool = False):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"{OWNER}-dynamic-profile",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as response:
            return json.load(response)
    except urllib.error.HTTPError as exc:
        if optional and exc.code in {404, 409, 422}:
            return None
        raise


def clean(text: str | None) -> str:
    return (text or "").replace("|", "\\|").replace("\n", " ").strip()


def shorten(text: str | None, limit: int = 74) -> str:
    value = clean(text)
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def parse_date(value: str | None) -> datetime:
    if not value:
        return datetime.min.replace(tzinfo=timezone.utc)
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def short_date(value: str | None) -> str:
    if not value:
        return "—"
    return parse_date(value).strftime("%Y-%m-%d")


def repo_api(name: str, suffix: str = "") -> str:
    encoded = urllib.parse.quote(name, safe="")
    return f"https://api.github.com/repos/{OWNER}/{encoded}{suffix}"


def load_public_repos():
    url = f"https://api.github.com/users/{OWNER}/repos?per_page=100&sort=pushed&direction=desc&type=owner"
    repos = github_json(url)
    return [
        r for r in repos
        if not r.get("fork") and not r.get("archived") and r.get("name") not in EXCLUDED
    ]


def load_latest_releases(existing_names: set[str]):
    releases = []
    for name in RELEASE_REPOS:
        if name not in existing_names:
            continue
        release = github_json(repo_api(name, "/releases/latest"), optional=True)
        if release:
            releases.append(release)
    releases.sort(key=lambda r: parse_date(r.get("published_at") or r.get("created_at")), reverse=True)
    return releases


def replace_block(readme: str, marker: str, body: str) -> str:
    pattern = rf"<!-- {re.escape(marker)}:START -->.*?<!-- {re.escape(marker)}:END -->"
    replacement = f"<!-- {marker}:START -->\n{body}\n<!-- {marker}:END -->"
    updated, count = re.subn(pattern, replacement, readme, flags=re.S)
    if count != 1:
        raise RuntimeError(f"Expected exactly one {marker} block in README.md")
    return updated


def signal_repositories(public_repos):
    by_name = {repo["name"]: repo for repo in public_repos}
    selected = [by_name[name] for name in SIGNAL_REPOS if name in by_name]
    selected.sort(key=lambda r: parse_date(r.get("pushed_at")), reverse=True)
    return selected, by_name


def render_public_activity(repos) -> str:
    lines = [
        "_Career-signal repositories only. Generated from public GitHub metadata._",
        "",
        "| Public engineering signal | Language | Stars | Latest push |",
        "| --- | --- | ---: | --- |",
    ]
    for repo in repos[:MAX_RECENT]:
        name = clean(repo["name"])
        url = repo["html_url"]
        language = clean(repo.get("language")) or "—"
        stars = int(repo.get("stargazers_count", 0))
        pushed = short_date(repo.get("pushed_at"))
        lines.append(f"| **[{name}]({url})** | {language} | {stars} | `{pushed}` |")
    if len(lines) == 4:
        lines.append("| _No configured public signal repositories found_ | — | — | — |")
    return "\n".join(lines)


def render_output_markdown(signal_repos, by_name, releases) -> str:
    build = signal_repos[0] if signal_repos else None
    research_candidates = [by_name[name] for name in RESEARCH_REPOS if name in by_name]
    research_candidates.sort(key=lambda r: parse_date(r.get("pushed_at")), reverse=True)
    research = research_candidates[0] if research_candidates else None
    release = releases[0] if releases else None

    lines = [
        "| Signal | Latest public evidence | Date |",
        "| --- | --- | --- |",
    ]
    if build:
        desc = shorten(build.get("description")) or "Public repository update"
        lines.append(
            f"| **BUILD** | **[{clean(build['name'])}]({build['html_url']})** — {desc} | `{short_date(build.get('pushed_at'))}` |"
        )
    else:
        lines.append("| **BUILD** | No configured public build signal yet | — |")

    if research:
        desc = shorten(research.get("description")) or "Public research / protocol architecture"
        lines.append(
            f"| **RESEARCH** | **[{clean(research['name'])}]({research['html_url']})** — {desc} | `{short_date(research.get('pushed_at'))}` |"
        )
    else:
        lines.append("| **RESEARCH** | Research surface pending | — |")

    if release:
        repo_url = release.get("html_url") or release.get("url", "")
        tag = clean(release.get("tag_name")) or "release"
        title = clean(release.get("name")) or tag
        lines.append(
            f"| **RELEASE** | **[{title}]({repo_url})** · `{tag}` | `{short_date(release.get('published_at') or release.get('created_at'))}` |"
        )
    else:
        lines.append("| **RELEASE** | Core public release baseline pending | — |")

    return "\n".join(lines)


def svg_open(height: int, title: str, desc: str) -> list[str]:
    return [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}" role="img" aria-labelledby="title desc">',
        f'<title id="title">{html.escape(title)}</title>',
        f'<desc id="desc">{html.escape(desc)}</desc>',
        f'<rect width="1199" height="{height - 1}" x=".5" y=".5" rx="22" fill="#0d1117" stroke="#30363d"/>',
    ]


def render_public_signal_svg(repos) -> str:
    rows = repos[:MAX_RECENT]
    height = 152 + max(1, len(rows)) * 54
    parts = svg_open(height, "Public engineering signal", "Recent career-signal repositories generated from GitHub metadata.")
    parts += [
        '<text x="52" y="58" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="25" font-weight="700">PUBLIC ENGINEERING SIGNAL // LIVE</text>',
        '<text x="52" y="88" fill="#8b949e" font-family="monospace" font-size="15">FILTERED FOR WEB3 · DEFI · AI SYSTEMS · SECURITY</text>',
        '<line x1="52" y1="108" x2="1148" y2="108" stroke="#21262d"/>',
    ]
    if not rows:
        parts.append('<text x="52" y="150" fill="#8b949e" font-family="monospace" font-size="16">NO CONFIGURED PUBLIC SIGNAL REPOSITORIES FOUND</text>')
    y = 150
    for index, repo in enumerate(rows, start=1):
        name = html.escape(str(repo["name"]))
        language = html.escape(str(repo.get("language") or "—"))
        pushed = html.escape(short_date(repo.get("pushed_at")))
        stars = int(repo.get("stargazers_count", 0))
        parts += [
            f'<circle cx="60" cy="{y - 5}" r="5" fill="#3fb950"/>',
            f'<text x="82" y="{y}" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="18" font-weight="700">{index:02d}  {name}</text>',
            f'<text x="700" y="{y}" fill="#8b949e" font-family="monospace" font-size="14">{language}</text>',
            f'<text x="880" y="{y}" fill="#8b949e" font-family="monospace" font-size="14">★ {stars}</text>',
            f'<text x="1000" y="{y}" fill="#58a6ff" font-family="monospace" font-size="14">{pushed}</text>',
        ]
        y += 54
    parts.append("</svg>")
    return "".join(parts) + "\n"


def render_output_feed_svg(signal_repos, by_name, releases) -> str:
    build = signal_repos[0] if signal_repos else None
    research_candidates = [by_name[name] for name in RESEARCH_REPOS if name in by_name]
    research_candidates.sort(key=lambda r: parse_date(r.get("pushed_at")), reverse=True)
    research = research_candidates[0] if research_candidates else None
    release = releases[0] if releases else None

    parts = svg_open(300, "Latest public output", "Latest build, research and release signals.")
    parts += [
        '<text x="52" y="56" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="25" font-weight="700">LATEST OUTPUT // VERIFIED PUBLIC SURFACES</text>',
        '<text x="52" y="84" fill="#8b949e" font-family="monospace" font-size="14">BUILD · RESEARCH · RELEASE</text>',
    ]
    cards = [
        (52, "BUILD", build["name"] if build else "PENDING", short_date(build.get("pushed_at")) if build else "—", build.get("language") if build else None),
        (414, "RESEARCH", research["name"] if research else "PENDING", short_date(research.get("pushed_at")) if research else "—", research.get("language") if research else None),
        (776, "RELEASE", (release.get("tag_name") if release else "BASELINE PENDING"), short_date((release or {}).get("published_at") or (release or {}).get("created_at")) if release else "—", None),
    ]
    for x, label, value, date, meta in cards:
        safe_value = html.escape(str(value))
        safe_meta = html.escape(str(meta or "PUBLIC SIGNAL"))
        parts += [
            f'<rect x="{x}" y="116" width="330" height="130" rx="16" fill="#161b22" stroke="#30363d"/>',
            f'<text x="{x+24}" y="150" fill="#58a6ff" font-family="monospace" font-size="13" font-weight="700">{label}</text>',
            f'<text x="{x+24}" y="182" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="18" font-weight="700">{safe_value[:31]}</text>',
            f'<text x="{x+24}" y="211" fill="#8b949e" font-family="monospace" font-size="13">{safe_meta[:34]}</text>',
            f'<text x="{x+24}" y="232" fill="#8b949e" font-family="monospace" font-size="13">{html.escape(date)}</text>',
        ]
    parts.append("</svg>")
    return "".join(parts) + "\n"


def render_project_deck_svg(by_name) -> str:
    card_w, card_h = 536, 178
    gap_x, gap_y = 24, 24
    start_x, start_y = 52, 118
    rows = (len(FEATURED) + 1) // 2
    height = start_y + rows * card_h + max(0, rows - 1) * gap_y + 46
    parts = svg_open(height, "Selected systems", "Featured project cards with live public repository metadata.")
    parts += [
        '<text x="52" y="54" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="25" font-weight="700">SELECTED SYSTEMS // EVIDENCE DECK</text>',
        '<text x="52" y="82" fill="#8b949e" font-family="monospace" font-size="14">STATUS BOUNDARIES + LIVE REPOSITORY METADATA</text>',
    ]
    for i, project in enumerate(FEATURED):
        col, row = i % 2, i // 2
        x = start_x + col * (card_w + gap_x)
        y = start_y + row * (card_h + gap_y)
        repo = by_name.get(project["name"])
        language = repo.get("language") if repo else "NOT PUBLIC"
        pushed = short_date(repo.get("pushed_at")) if repo else "—"
        stars = int(repo.get("stargazers_count", 0)) if repo else 0
        parts += [
            f'<rect x="{x}" y="{y}" width="{card_w}" height="{card_h}" rx="18" fill="#161b22" stroke="#30363d"/>',
            f'<text x="{x+24}" y="{y+34}" fill="#58a6ff" font-family="monospace" font-size="12" font-weight="700">{html.escape(project["domain"])}</text>',
            f'<text x="{x+24}" y="{y+67}" fill="#f0f6fc" font-family="Arial, sans-serif" font-size="22" font-weight="700">{html.escape(project["display"])}</text>',
            f'<text x="{x+24}" y="{y+94}" fill="#8b949e" font-family="Arial, sans-serif" font-size="14">{html.escape(project["summary"])}</text>',
            f'<text x="{x+24}" y="{y+128}" fill="#d2a8ff" font-family="monospace" font-size="12">{html.escape(project["status"])}</text>',
            f'<text x="{x+24}" y="{y+153}" fill="#8b949e" font-family="monospace" font-size="12">{html.escape(str(language or "—"))}  ·  ★ {stars}  ·  {html.escape(pushed)}</text>',
        ]
    parts.append("</svg>")
    return "".join(parts) + "\n"


def main() -> None:
    public_repos = load_public_repos()
    if not public_repos:
        raise RuntimeError("No public repositories returned by GitHub API")

    signal_repos, by_name = signal_repositories(public_repos)
    releases = load_latest_releases(set(by_name))

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    readme = replace_block(readme, "OUTPUT-FEED", render_output_markdown(signal_repos, by_name, releases))
    readme = replace_block(readme, "PUBLIC-ACTIVITY", render_public_activity(signal_repos))
    readme_path.write_text(readme, encoding="utf-8")

    dynamic = ROOT / "assets/dynamic"
    dynamic.mkdir(parents=True, exist_ok=True)
    (dynamic / "public-signal.svg").write_text(render_public_signal_svg(signal_repos), encoding="utf-8")
    (dynamic / "output-feed.svg").write_text(render_output_feed_svg(signal_repos, by_name, releases), encoding="utf-8")
    (dynamic / "project-deck.svg").write_text(render_project_deck_svg(by_name), encoding="utf-8")


if __name__ == "__main__":
    main()
