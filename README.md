# Co Chaos — Rate-library Watcher (the thing that READS the supplier files)

Reads supplier-quote PDFs uploaded to your R2 bucket (quotes/uploads/), extracts
candidate rates, and writes the shared library to quotes/rates.json — which your
review-enigma /api/rates serves and the generator app caches. Pure Python
(pdfplumber), no system dependencies. Reads only NEW files; rewrites rates.json
only when it finds new rates. Every new rate is flagged LOW so you review it.

================================================================
WHERE TO ADD IT — pick ONE
================================================================

OPTION A — Render Cron Job  (you already use Render)
  1. Put these files in a GitHub repo. You can reuse your now-free
     `chaosbudgetreader` repo — replace its contents with these files and commit.
     (The old export code there is no longer needed; exports are in the app now.)
  2. Render Dashboard -> New + -> Cron Job   (or "Blueprint" to use render.yaml).
  3. Connect the repo. Runtime: Python.
       Build command:  pip install -r requirements.txt
       Command:        python process_bucket.py
       Schedule:       */10 * * * *      (every 10 minutes)
  4. Add Environment variables — the SAME four values as your review-enigma
     Netlify site (copy them across):
       R2_ENDPOINT
       R2_ACCESS_KEY_ID
       R2_SECRET_ACCESS_KEY
       R2_BUCKET
     (S3_PREFIX=quotes is already set for you.)
  5. Create. It runs on schedule, reads quotes/uploads/, writes quotes/rates.json.
     Check "Logs" — you'll see "N new file(s) -> M new rate(s)".

OPTION B — GitHub Actions  (free, no server)
  The included .github/workflows/build-rates.yml runs the same script every 15 min
  and on demand. In the repo:
     Settings -> Secrets and variables -> Actions -> New repository secret
     add: R2_ENDPOINT, R2_ACCESS_KEY_ID, R2_SECRET_ACCESS_KEY, R2_BUCKET
  Then the Actions tab runs it automatically; "Run workflow" triggers it manually.

================================================================
HOW IT FITS
================================================================
  upload on review-enigma  ->  R2 quotes/uploads/*.pdf
        -> THIS watcher reads new PDFs, extracts rates
        -> writes R2 quotes/rates.json
        -> review-enigma /api/rates serves it
        -> generator app syncs + caches it (new rates show as LOW to review)

Note: extraction is heuristic across many different supplier layouts, so it pulls
candidates and flags them all LOW for review rather than trusting them blindly.
You confirm/correct in the app; accuracy improves as the library grows.

Local test:  STORAGE=local LOCAL_DIR=./bucket python process_bucket.py
  (drop PDFs in ./bucket/uploads/, rates.json appears in ./bucket/)
