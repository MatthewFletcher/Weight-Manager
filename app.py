import os
import sqlite3
import hashlib
from datetime import datetime
from typing import List, Optional

from fastapi import FastAPI, Request, Form, Body
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF
import markdown as md

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATABASE = os.path.join(BASE_DIR, "data", "weights.db")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")
HELP_DIR = os.path.join(BASE_DIR, "help")
REPORT_PATH = os.path.join(BASE_DIR, "data", "report.pdf")

app = FastAPI()
templates = Jinja2Templates(directory=TEMPLATES_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Ensure data directory exists
os.makedirs(os.path.dirname(DATABASE), exist_ok=True)

# Entry hash: hash of name and room (or "N/A" if room is blank)
def entry_hash(name: str, room: Optional[str]) -> str:
    key = f"{name.strip()}::{(room or '').strip() or 'N/A'}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]

# Initialize database (with new schema)
def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            hash TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            room TEXT,
            weights TEXT NOT NULL,
            admission_date TEXT NOT NULL
        )
    ''')
    conn.close()
init_db()

@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    return templates.TemplateResponse("entry_form.html", {"request": request})

@app.post("/add")
async def add_entry(
    name: str = Form(...),
    room: Optional[str] = Form(None),
    admission_date: str = Form(...),
    weight: float = Form(...)
):
    room_val = (room or "").strip()
    h = entry_hash(name, room_val)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT weights FROM entries WHERE hash=?", (h,))
    row = cursor.fetchone()
    if row:
        weights = row[0].split(",") + [str(weight)]
        weights = weights[-5:]
        cursor.execute(
            "UPDATE entries SET weights=?, admission_date=? WHERE hash=?",
            (",".join(weights), admission_date, h)
        )
    else:
        cursor.execute(
            "INSERT INTO entries (hash, name, room, weights, admission_date) VALUES (?, ?, ?, ?, ?)",
            (h, name.strip(), room_val, str(weight), admission_date)
        )
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)

@app.post("/add_weight/{entry_hash}")
async def add_weight(entry_hash: str, weight: float = Form(...)):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT weights FROM entries WHERE hash=?", (entry_hash,))
    row = cursor.fetchone()
    if row:
        weights = row[0].split(",") + [str(weight)]
        weights = weights[-5:]
        cursor.execute("UPDATE entries SET weights=? WHERE hash=?", (",".join(weights), entry_hash))
        conn.commit()
    conn.close()
    return RedirectResponse("/entries", status_code=303)

@app.post("/update_field")
async def update_field(
    hash: str = Form(...),
    field: str = Form(...),
    value: str = Form(...)
):
    if field not in {"name", "room", "admission_date"}:
        return JSONResponse({"error": "Invalid field"}, status_code=400)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    # Update the field
    cursor.execute(f"UPDATE entries SET {field}=? WHERE hash=?", (value, hash))
    conn.commit()
    conn.close()
    # For room/name, might need to recalculate hash (not implemented here)
    return JSONResponse({"success": True, "value": value})


@app.get("/entries", response_class=HTMLResponse)
async def entries(request: Request):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT hash, name, room, weights, admission_date FROM entries")
    rows = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse("entries.html", {"request": request, "entries": rows})

@app.post("/delete")
async def delete(delete_hashes: Optional[List[str]] = Form(None)):
    if delete_hashes:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.executemany("DELETE FROM entries WHERE hash=?", [(h,) for h in delete_hashes])
        conn.commit()
        conn.close()
    return RedirectResponse("/entries", status_code=303)

@app.get("/help/{page}")
async def get_help(page: str):
    help_file = os.path.join(HELP_DIR, f"{page}.md")
    if not os.path.isfile(help_file):
        return JSONResponse({"error": "Help not found"}, status_code=404)
    with open(help_file, encoding="utf-8") as f:
        md_content = f.read()
    html = md.markdown(md_content)
    return JSONResponse({"html": html})

@app.get("/report")
async def generate_report():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, room, weights, admission_date FROM entries")
    rows = cursor.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    report_title = f"Weight Report -- Generated {datetime.now().strftime('%B %d, %Y')}"
    pdf.cell(0, 10, report_title, ln=True, align="C")

    pdf.set_font("Arial", "B", 12)
    pdf.cell(60, 10, "Name", 1)
    pdf.cell(40, 10, "Room", 1)
    pdf.cell(40, 10, "Admission Date", 1)
    pdf.cell(40, 10, "Last Weight", 1)
    pdf.cell(50, 10, "Notes", 1, ln=True)

    pdf.set_font("Arial", "", 12)
    for name, room, weights, admission_date in rows:
        last_weight = weights.split(",")[-1]
        pdf.cell(60, 10, name, 1)
        pdf.cell(40, 10, room or "N/A", 1)
        pdf.cell(40, 10, admission_date or "", 1)
        pdf.cell(40, 10, last_weight, 1)
        pdf.cell(50, 10, "", 1, ln=True)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    pdf.output(REPORT_PATH)
    return FileResponse(REPORT_PATH, media_type="application/pdf", filename="weight_report.pdf")
