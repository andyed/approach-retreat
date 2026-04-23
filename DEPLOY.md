# Deploy — approach-retreat

**Live URL:** https://andyed.github.io/approach-retreat/
**Source branch:** `main`, path `/`
**Deploy trigger:** **Auto on push to main** via GitHub Actions
(`.github/workflows/deploy.yml`).
**Build command:** `npm run build` (runs inside the workflow).
**Deploy command:** Automatic. GH Actions uploads the `site/` artifact and
deploys it. No local deploy command needed.

## Minimal-change protocol (text-only patches)

Workflow-based auto-deploy means the source tree is the source of truth. For
analytics-key changes, copy edits, small fixes:

1. Edit the source file(s) in `src/` or `site/` as appropriate.
2. Commit, push.
3. GH Actions builds and deploys within ~1-2 min.

**Note:** `build.js` mirrors `dist/` → `site/dist/` automatically — no extra
copy step.

## Full build (for local verification)

```bash
npm ci
npm run build
# Output lands in site/ — open site/index.html to inspect
```

## Verification

```bash
curl -s https://andyed.github.io/approach-retreat/ | grep -o "phc_[A-Za-z0-9]*"
# expect phc_pJJNd2...
```

Also check the Actions tab on GitHub for the most recent workflow run status.

## Files to know

- `src/` — source (JS, HTML)
- `site/` — GH Pages artifact (built by `npm run build`)
- `.github/workflows/deploy.yml` — the deploy workflow

## PostHog

Writes to **approach-retreat project (374762)** — the shared "research viewers"
project also used by `attentional-foraging`. Pooling events enables cross-repo
cohort analysis.
