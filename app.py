"""FastAPI export service — turns the generator's payload into Enigma-branded files.
POST /generate  body: {format:"xlsx"|"pdf", filename, header{...}, sections[...]}
Returns the file as a download. CORS open so the PWA (different origin) can call it.
Run: uvicorn app:app --host 0.0.0.0 --port 8000
"""
import os, tempfile, datetime
from typing import List
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import enigma_export as EE

app = FastAPI(title="Co Chaos Export Service")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class Line(BaseModel):
    item: str; qty: float = 1; unitBuy: float = 0
    supplier: str = ""; contact: str = ""; note: str = ""; confidence: str = ""
class Section(BaseModel):
    title: str; excl: bool = False; lines: List[Line] = []
class Header(BaseModel):
    client: str = ""; event: str = ""; job: str = ""
    version: str = "Estimated Budget V1"; date: str = ""
class Payload(BaseModel):
    header: Header; sections: List[Section] = []
    format: str = "xlsx"; filename: str = "Estimate"

@app.get("/health")
def health(): return {"ok": True}

@app.post("/generate")
def generate(p: Payload):
    payload = {"header": p.header.dict(),
               "sections": [s.dict() for s in p.sections]}
    if not payload["header"].get("date"):
        payload["header"]["date"] = datetime.date.today().strftime("%d/%m/%Y")
    is_pdf = (p.format == "pdf")
    fd, path = tempfile.mkstemp(suffix=".pdf" if is_pdf else ".xlsx"); os.close(fd)
    try:
        if is_pdf:
            EE.build_pdf(payload, path)
            media = "application/pdf"
        else:
            EE.build_xlsx(payload, path)
            media = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        data = open(path, "rb").read()
    finally:
        try: os.remove(path)
        except OSError: pass
    fn = p.filename + (".pdf" if is_pdf else ".xlsx")
    return Response(content=data, media_type=media,
                    headers={"Content-Disposition": f'attachment; filename="{fn}"'})
