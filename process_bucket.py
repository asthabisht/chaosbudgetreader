"""
process_bucket.py — watch the upload bucket, extract rates from NEW quotes only,
merge them into the shared rates.json. Rewrites rates.json ONLY when new files
were processed (no new uploads => no rewrite), exactly as specced.

Run it:
  • on a 5-min schedule (cron / scheduled job / serverless timer):  python process_bucket.py
  • continuously:                                                   python process_bucket.py --loop 300
  • from your site after an upload (event trigger):                 import process_bucket; process_bucket.run()

Layout in the bucket (keys are relative to S3_PREFIX / LOCAL_DIR):
  uploads/        <- your website drops supplier-quote PDFs here
  rates.json      <- the shared rate library (this script maintains it)
  _processed.json <- bookkeeping: which upload keys have already been ingested
"""
import os, sys, json, time, datetime
from storage import make_storage
from extractor import extract_rates

UPLOAD_PREFIX = os.getenv("UPLOAD_PREFIX", "uploads")
RATES_KEY     = os.getenv("RATES_KEY", "rates.json")
PROCESSED_KEY = os.getenv("PROCESSED_KEY", "_processed.json")

def _load_json(store, key, default):
    raw = store.read_text(key, None)
    if not raw: return default
    try: return json.loads(raw)
    except Exception: return default

def run():
    store = make_storage()
    processed = set(_load_json(store, PROCESSED_KEY, []))
    all_keys = store.list_keys(UPLOAD_PREFIX)
    new = [k for k in all_keys if k.lower().endswith(".pdf") and k not in processed]

    if not new:
        print(f"[{datetime.datetime.now(datetime.timezone.utc):%H:%M:%S}] no new uploads — rates.json untouched.")
        return {"new_files": 0, "new_rates": 0, "rewritten": False}

    rates = _load_json(store, RATES_KEY, [])
    existing = {(r.get("keywords"), round(float(r.get("unit_cost", 0) or 0), 2)) for r in rates}
    added = 0
    for key in new:
        try:
            rows = extract_rates(store.read_bytes(key), key)
        except Exception as e:
            print(f"  ! {key}: {e}"); processed.add(key); continue
        for row in rows:
            sig = (row["keywords"], round(row["unit_cost"], 2))
            if sig in existing or not row["keywords"]: continue
            existing.add(sig); rates.append(row); added += 1
        processed.add(key)
        print(f"  + {key}: {len(rows)} candidate rate(s)")

    # only rewrite rates.json when we actually added something
    if added:
        store.write_text(RATES_KEY, json.dumps(rates, indent=2, ensure_ascii=False))
    store.write_text(PROCESSED_KEY, json.dumps(sorted(processed), indent=2))
    print(f"[{datetime.datetime.now(datetime.timezone.utc):%H:%M:%S}] {len(new)} new file(s) -> "
          f"{added} new rate(s) (flagged LOW for review). rates.json rewritten: {bool(added)}.")
    return {"new_files": len(new), "new_rates": added, "rewritten": bool(added)}

def main():
    if "--loop" in sys.argv:
        every = int(sys.argv[sys.argv.index("--loop") + 1]) if len(sys.argv) > sys.argv.index("--loop") + 1 else 300
        print(f"watching every {every}s …  (Ctrl-C to stop)")
        while True:
            try: run()
            except Exception as e: print("error:", e)
            time.sleep(every)
    else:
        run()

if __name__ == "__main__":
    main()
