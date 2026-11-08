# Deploy to Cloudflare

The site is static: `web/index.html` plus one JSON file per lesson in `web/lessons/` and the fonts.
`wrangler.jsonc` in the repo root tells Cloudflare to serve the `web/` folder as a Worker with static assets.
The only code is `site/worker.js`, which runs for `/video/*` and answers HTTP range requests (206 Partial Content),
so the videos play in Safari and seek in every browser. There is no sign-in: anyone with the link can read every lesson, and each visitor's
progress is saved in their own browser.

Cloudflare's dashboard changes now and then, so button names may differ a little from these steps.

## Option A: GitHub Actions deploys on every push (set up once)

The repo has `.github/workflows/ci.yml`. On every push to `main` it validates the lessons, checks that the
committed `web/` matches a fresh build, runs every lab's reference solutions, and then runs `wrangler deploy`.
The deploy step needs two secrets from your Cloudflare account:

1. Create an API token. In the Cloudflare dashboard, open **My Profile** → **API Tokens** → **Create Token**,
   use the **Edit Cloudflare Workers** template, pick your account, then **Create Token**. Copy it (it is shown once).
2. Find your Account ID under **Workers & Pages** (right-hand panel).
3. In the GitHub repo, open **Settings** → **Secrets and variables** → **Actions** → **New repository secret**
   and add `CLOUDFLARE_API_TOKEN` and `CLOUDFLARE_ACCOUNT_ID`.
4. Push to `main`, or open **Actions** → **ci** → **Run workflow**.

Without the secrets, the deploy step is skipped and the checks still run.

## Option B: let Cloudflare watch the repo

In **Workers & Pages** → **Create** → **Import a repository**, pick this repo, set the production branch to `main`,
no build command, deploy command `npx wrangler deploy`, root directory `/`. Use this instead of Option A, not as well.

## Option C: deploy from your Mac

```bash
npx wrangler login
```

```bash
npx wrangler deploy
```

`wrangler login` opens a browser to approve access once. `wrangler deploy` prints the site's URL at the end.

## Changing the course later

1. Edit lessons in `content/lessons/<id>.json` (or the site in `site/`).
2. Check and rebuild:

   ```bash
   python3 site/validate.py --all
   ```

   ```bash
   python3 site/build.py
   ```

3. Commit `content/` and `web/` together and push.

## If something goes wrong

- "Worker name does not match": make the dashboard name and `"name"` in `wrangler.jsonc` the same.
- The page shows old content: run `python3 site/build.py` and commit `web/`.
- A lesson says "Couldn't load this lesson": its `web/lessons/<id>.json` is missing; rebuild and commit.
