# Pheonix64.github.io

Personal portfolio, generated from my GitHub profile plus hand-curated content.
Live at **https://pheonix64.github.io**.

## How it works

```
GitHub API (public repos) ─┐
data/repos.seed.json ──────┼─> build.py ─> templates/ ─> _site/index.html ─> GitHub Pages
config.yaml + featured.yaml┘
```

- `config.yaml` — profile, experience, education, skills, repos to hide, description overrides.
- `featured.yaml` — "Selected work" cards. Projects without a public repo are allowed.
- `build.py` — fetches public repos (falls back to the seed file offline) and renders one self-contained HTML page.
- `.github/workflows/deploy.yml` — rebuilds on every push and once a day, then deploys to Pages.

## Edit content

Edit the YAML files and push. Empty fields are not rendered.

## Run locally

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python build.py            # or: python build.py --offline
# open _site/index.html
```

## One-time setup

1. Rename the repository `Phoenix64.github.io` → `Pheonix64.github.io`
   (Settings → General → Repository name). The name must match the username exactly.
2. Replace its contents with this project and push to `main`.
3. Settings → Pages → Build and deployment → Source: **GitHub Actions**.
4. Wait for the "Build & deploy portfolio" workflow to finish (Actions tab).
