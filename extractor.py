"""
extractor.py — turn a supplier-quote PDF into candidate rate-card rows.

Pure-pip (pdfplumber only, no poppler/system deps). Returns rows in the shared
rate-library schema. Auto-ingested rows are marked confidence='low' (needs review)
so they never silently pollute the shared library — a human confirms, then promotes.
"""
import re, io, os, shutil, subprocess, tempfile, datetime
import pdfplumber

def _get_text(pdf_bytes):
    """Prefer pdftotext -layout (clean columns); fall back to pdfplumber (pure-pip)."""
    if shutil.which("pdftotext"):
        tf = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        try:
            tf.write(pdf_bytes); tf.close()
            txt = subprocess.run(["pdftotext", "-layout", tf.name, "-"],
                                 capture_output=True, text=True, timeout=60).stdout
            if txt.strip(): return txt
        except Exception: pass
        finally:
            try: os.unlink(tf.name)
            except OSError: pass
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return "\n".join((p.extract_text() or "") for p in pdf.pages)

MONEY = re.compile(r"\d{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+\.\d{2}")
QTY   = re.compile(r"^(\d{1,3})(?:\.0+)?$")
SKIP  = re.compile(r"sub ?total|vat|tax\b|amount in words|standard rate|grand total|"
                   r"\btotal\b|^total|aed total|page \d|purchase order|\bp\.?o\.?\b|trn|reference|"
                   r"quote number|expiry|date\b|approved|terms|payment|bank|iban|account|balance|"
                   r"discount total|charge total|^aed\b|^amount\b", re.I)

# category / driver hints — same vocabulary as the rate library
CAT_HINTS = [
    (["host","hostess","promoter","band","dancer","performer","dj","musician","mc","aerial"], "entertainment", "show"),
    (["led","screen","speaker","audio","sound","pa ","lighting","light","truss","rigging","projector","stage tech"], "av", "day"),
    (["carpet","floor","wall","backdrop","scenic","plinth","mdf","fabricat","cutout","signage","mirror","standee","build","structure"], "scenic", "m2"),
    (["magnet","badge","pin","sticker","keychain","keyring","lanyard","tote","bag","gift","cup","giveaway","mug","notebook","pen"], "giveaway", "piece"),
    (["booth","machine","game","activation","arcade","claw","vr","simulator","inflatable"], "activation", "day"),
    (["manager","producer","director","technician","designer","engineer","crew","supervisor"], "staffing", "day"),
]
STOP = {"the","and","for","with","size","piece","pieces","pcs","incl","including","each","per","aed",
        "set","per","unit","approx","custom","customized","material","width","height","design","branded"}

def _num(s):
    try: return float(str(s).replace(",", ""))
    except: return None

def guess_cat(name):
    n = name.lower()
    for kws, cat, drv in CAT_HINTS:
        if any(k in n for k in kws): return cat, drv
    return "review", "piece"

def clean_keywords(desc):
    words = [w for w in re.sub(r"[^a-zA-Z ]", " ", desc).lower().split() if w not in STOP and len(w) > 2]
    return " ".join(words[:3]) or desc.lower()[:24]

def supplier_from_name(filename):
    stem = re.sub(r"\.[^.]+$", "", filename.split("/")[-1])
    stem = re.sub(r"(?i)\b(quote|quotation|po|invoice|est|final|v\d+|\d{4,})\b", "", stem)
    stem = re.split(r"[-_]", stem)
    cand = next((p.strip() for p in stem if len(p.strip()) > 2), "")
    return cand.title()

def _line_items(text):
    out = []
    for ln in (text or "").splitlines():
        s = " ".join(ln.split())
        if len(s) < 6 or SKIP.search(s): continue
        toks = MONEY.findall(s)
        nums = [n for n in (_num(t) for t in toks) if n is not None and n > 0]
        if not nums: continue
        desc = re.sub(r"^\d{1,3}\s+", "", s[:s.find(toks[0])].strip(" .-#"))  # drop leading row no.
        if len(desc) < 4 or desc.replace(" ", "").isdigit(): continue
        total = max(nums)
        if total < 10: continue
        # find the qty×unit pair whose product best matches the total (handles VAT columns)
        best = None
        for i in range(len(nums)):
            for j in range(len(nums)):
                if i == j: continue
                err = abs(nums[i] * nums[j] - total) / total
                if err <= 0.06 and (best is None or err < best[0]):
                    best = (err, nums[i], nums[j])
        if best:
            _, q, u = best; qty, unit = q, u
        else:
            qty, unit = 1, total  # flat / lump-sum line
        out.append((re.sub(r"\s+", " ", desc)[:120], qty, unit, total))
    return out

def extract_rates(pdf_bytes, filename):
    supplier = supplier_from_name(filename)
    now = datetime.datetime.utcnow().isoformat(timespec="seconds") + "Z"
    items = []
    try:
        items = _line_items(_get_text(pdf_bytes))
    except Exception as e:
        return [{"keywords": "", "category": "review", "driver": "piece", "unit_cost": 0,
                 "supplier": supplier, "contact": "", "email": "", "confidence": "low",
                 "note": f"could not parse ({e})", "source_file": filename, "source_item": "", "added_at": now}]
    rows, seen = [], set()
    for desc, qty, unit, amt in items:
        cat, drv = guess_cat(desc)
        unit_cost = unit if (unit and unit > 0) else (round(amt / qty, 2) if qty else amt)
        kw = clean_keywords(desc)
        key = (kw, round(unit_cost, 2))
        if key in seen: continue
        seen.add(key)
        rows.append({"keywords": kw, "category": cat, "driver": drv, "unit_cost": round(unit_cost, 2),
                     "supplier": supplier, "contact": "", "email": "", "confidence": "low",
                     "note": f"auto-ingested from {filename} — review & confirm",
                     "source_file": filename, "source_item": desc, "added_at": now})
    return rows
