#!/usr/bin/env python3
"""Build the portfolio as a single self-contained index.html.

Data flow:
    GitHub REST API (public repos)  ─┐
    data/repos.seed.json (fallback) ─┼─> merge + filter ─> Jinja2 template ─> _site/index.html
    config.yaml + featured.yaml ─────┘

Usage:
    python3 build.py            # fetch live data, fall back to the seed file on error
    python3 build.py --offline  # seed file only (no network)
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
import urllib.error
import urllib.request
from pathlib import Path

import yaml
from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "_site"
API = "https://api.github.com"


def load_yaml(name: str):
    with open(ROOT / name, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def fetch_repos(user: str) -> list[dict]:
    """Public, owner-only repos. Uses GITHUB_TOKEN when present (CI) for a higher rate limit."""
    url = f"{API}/users/{user}/repos?per_page=100&type=owner&sort=pushed"
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
        "User-Agent": f"{user}-portfolio-build",
    }
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=20) as r:
        data = json.load(r)
    if not isinstance(data, list):
        raise RuntimeError(f"Unexpected API response: {data}")
    return data


def load_repos(user: str, offline: bool) -> tuple[list[dict], str]:
    if not offline:
        try:
            return fetch_repos(user), "live"
        except (urllib.error.URLError, RuntimeError, TimeoutError) as e:
            print(f"[warn] GitHub API unavailable ({e}); using seed file", file=sys.stderr)
    with open(ROOT / "data" / "repos.seed.json", encoding="utf-8") as f:
        return json.load(f), "seed"


def normalize(repo: dict, user: str, overrides: dict) -> dict:
    o = overrides.get(repo["name"], {})
    return {
        "name": repo["name"],
        "title": o.get("title") or repo["name"].replace("_", " ").replace("-", " "),
        "description": o.get("description") or repo.get("description") or "",
        "language": repo.get("language") or "",
        "stars": repo.get("stargazers_count", 0),
        "topics": repo.get("topics") or [],
        "updated": (repo.get("pushed_at") or "")[:10],
        "url": repo.get("html_url") or f"https://github.com/{user}/{repo['name']}",
        "homepage": repo.get("homepage") or "",
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true")
    args = ap.parse_args()

    cfg = load_yaml("config.yaml")
    featured = load_yaml("featured.yaml") or []
    user = cfg["github_user"]
    excluded = {n.lower() for n in cfg.get("exclude_repos", [])}
    overrides = cfg.get("repo_overrides", {})

    raw, source = load_repos(user, args.offline)
    by_name = {r["name"].lower(): r for r in raw}

    # Attach live repo data to featured cards; warn on typos instead of failing.
    featured_names = set()
    for p in featured:
        name = (p.get("repo") or "").strip()
        if not name:
            continue
        r = by_name.get(name.lower())
        if r is None:
            print(f"[warn] featured repo '{name}' not found among public repos", file=sys.stderr)
            continue
        featured_names.add(name.lower())
        p["gh"] = normalize(r, user, overrides)

    repos = [
        normalize(r, user, overrides)
        for r in raw
        if not r.get("fork")
        and not r.get("archived")
        and r["name"].lower() not in excluded
        and r["name"].lower() not in featured_names
    ]
    repos.sort(key=lambda r: r["updated"], reverse=True)
    languages = sorted({r["language"] for r in repos if r["language"]})

    env = Environment(
        loader=FileSystemLoader(ROOT / "templates"),
        autoescape=select_autoescape(["html", "j2"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    html = env.get_template("index.html.j2").render(
        cfg=cfg,
        p=cfg["profile"],
        featured=featured,
        repos=repos,
        languages=languages,
        css=(ROOT / "templates" / "style.css").read_text(encoding="utf-8"),
        built=dt.date.today().isoformat(),
        source=source,
    )

    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir()
    (OUT / "index.html").write_text(html, encoding="utf-8")
    if (ROOT / "static").is_dir():  # e.g. cv.pdf, avatar
        shutil.copytree(ROOT / "static", OUT / "static")
    print(f"Built {OUT/'index.html'} — {len(featured)} featured, {len(repos)} repos ({source} data)")


if __name__ == "__main__":
    main()
