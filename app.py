"""
app.py — optional HTTP wrapper around the rate-card generator.

  POST /process   run an ingest pass now (call this from your site after an upload,
                  or point a scheduler at it every 5 min). No-op if no new uploads.
  GET  /rates     returns the current shared rates.json — the OFFLINE generator app
                  fetches this when online to refresh its cached rate library.
  GET  /health    liveness check.

Run:  uvicorn app:app --host 0.0.0.0 --port 8000
"""
import os, json
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from storage import make_storage
import process_bucket as pb

app = FastAPI(title="Co Chaos — Rate-Card Generator")
app.add_middleware(CORSMiddleware,
    allow_origins=(os.getenv("CORS_ORIGINS", "*").split(",")),
    allow_methods=["GET", "POST"], allow_headers=["*"])

@app.post("/process")
def process():
    return pb.run()

@app.get("/rates")
def rates():
    store = make_storage()
    raw = store.read_text(os.getenv("RATES_KEY", "rates.json"), "[]")
    try: data = json.loads(raw)
    except Exception: data = []
    return JSONResponse(content=data)

@app.get("/health")
def health():
    return {"ok": True}
