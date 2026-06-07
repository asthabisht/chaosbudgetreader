# Run the watcher on GitHub (Actions) — no server

The watcher runs as a GitHub Action: it wakes on a schedule (and on a manual button),
reads new supplier PDFs from your R2 bucket, and updates quotes/rates.json. Free.

## 1. Make a repo
Use a new GitHub repo, or reuse your existing `chaosbudgetreader` repo (replace its
contents with these files). Public repo = unlimited Action minutes; private = 2000
free min/month (plenty at this cadence).

## 2. Upload these files
Upload everything here, keeping the folder layout — including the hidden
`.github/workflows/build-rates.yml`.
  - On a Mac the `.github` folder is hidden: press  Cmd + Shift + .  in Finder to show it.
  - Easiest path if that's fiddly: on GitHub click **Add file -> Create new file**, type
    the name exactly:  `.github/workflows/build-rates.yml`  (GitHub makes the folders),
    then paste the contents of that file (also shown at the bottom of this note) and commit.
  - The other files (process_bucket.py, extractor.py, storage.py, requirements.txt,
    app.py, .gitignore) go in the repo root.

## 3. Add your R2 secrets
Repo -> **Settings -> Secrets and variables -> Actions -> New repository secret**.
Add these four (same values as your review-enigma site):
  - R2_ENDPOINT
  - R2_ACCESS_KEY_ID
  - R2_SECRET_ACCESS_KEY
  - R2_BUCKET

## 4. Run it
Repo -> **Actions** tab -> if prompted, enable workflows -> pick **Build rate library**
-> **Run workflow** to test right now. Open the run and check the log line:
  `N new file(s) -> M new rate(s)`
After that it runs automatically every ~30 min. Hit **Run workflow** any time you've
just uploaded new supplier quotes and want them picked up immediately.

## Good to know
- New rates land as **LOW** — confirm/correct them in the app's Rate Library tab.
- GitHub pauses *scheduled* runs after 60 days of no repo activity; a manual run or any
  commit resumes them.
- The app re-syncs the library each time you open it, so new rates show up on their own.
