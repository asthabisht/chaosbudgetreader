# Co Chaos — Export Service

Tiny web service that turns the generator's line items into Enigma-branded files:
- **xlsx** — internal working budget (BUY/sell/profit, green section bars, blue cost
  columns, live formulas, margin %, T&C) via openpyxl.
- **pdf** — client-facing quote (ENIGMA wordmark, centered title block, 4-column
  table, green SUB TOTAL bars, totals, footer address, T&C page) via reportlab.

## Run locally
```
pip install -r requirements.txt
uvicorn app:app --reload --port 8000
```
Test: `POST http://localhost:8000/generate` with a JSON payload (see app.py models).

## Deploy (same host as your rate watcher works well — Render / Railway)
- Start command: `uvicorn app:app --host 0.0.0.0 --port $PORT`
- No env vars required.
- Note the public URL, then set `EXPORT_BASE` in the generator's `app.js` to it.

## Wiring
The generator builds the payload (header + sections with unit BUY, supplier, contact,
confidence) and POSTs it here. The service only lays it out + writes formulas — it does
not re-price anything. If the service is unreachable, the app falls back to its plain
in-browser Excel export / browser print, so offline still works.

## Fonts
The xlsx is set to "Proxima Nova Regular" and renders correctly on machines that have
it installed. The PDF uses Helvetica as a Proxima Nova stand-in; drop a Proxima Nova
TTF next to this service and register it in enigma_export.py (build_pdf) to embed it.
