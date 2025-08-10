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
from fastapi import Form, Request
from fastapi.responses import JSONResponse, FileResponse
import markdown as md
import logging
import traceback

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

logger = logging.getLogger("uvicorn.error")  # or "myapp" if custom logger
logger.setLevel(logging.DEBUG)

# Ensure data directory exists
os.makedirs(os.path.dirname(DATABASE), exist_ok=True)


# Entry hash: hash of name and room (or "N/A" if room is blank)
def entry_hash(name: str, room: Optional[str], building: Optional[str]) -> str:
    key = f"{name.strip()}::{(room or '').strip() or 'N/A'}::{(building or '').strip() or 'Unassigned'}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


# Initialize database (with new schema)
def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entries (
            hash TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            room TEXT,
            weights TEXT NOT NULL,
            admission_date TEXT NOT NULL
        )
    """
    )
    conn.close()


init_db()

def get_building_options():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT DISTINCT COALESCE(NULLIF(building, ''), 'Unassigned') FROM entries")
    buildings = sorted([b[0] for b in cur.fetchall()])
    conn.close()
    # Always offer at least one option
    return buildings or ["Unassigned"]



@app.get("/", response_class=HTMLResponse)
async def form(request: Request, building: Optional[str] = None):
    buildings = get_building_options()
    selected_building = building or (buildings[0] if buildings else "Unassigned")
    return templates.TemplateResponse(
        "entry_form.html",
        {"request": request, "buildings": buildings, "selected_building": selected_building},
    )

@app.get("/boom")
def boom():
    raise ValueError("Kaboom")


@app.exception_handler(Exception)
async def custom_500_handler(request: Request, exc: Exception):
    tb_str = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    logger.error("Unhandled exception", exc_info=exc)
    return templates.TemplateResponse(
        "500.html", {"request": request, "traceback": tb_str}, status_code=500
    )


@app.post("/add")
async def add_entry(
    name: str = Form(...),
    room: Optional[str] = Form(None),
    admission_date: str = Form(...),
    weight: float = Form(...),
    building: Optional[str] = Form(None),
):
    building_val = (building or "").strip() or "Unassigned"
    room_val = (room or "").strip()
    h = entry_hash(name, room_val, building_val)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT weights FROM entries WHERE hash=?", (h,))
    row = cursor.fetchone()
    if row:
        weights = row[0].split(",") + [str(weight)]
        weights = weights[-5:]
        cursor.execute(
            "UPDATE entries SET weights=?, admission_date=?, building=? WHERE hash=?",
            (",".join(weights), admission_date, building_val, h),
        )
    else:
        cursor.execute(
            "INSERT INTO entries (hash, name, room, weights, admission_date, building) VALUES (?, ?, ?, ?, ?, ?)",
            (h, name.strip(), room_val, str(weight), admission_date, building_val),
        )
    conn.commit()
    conn.close()
    # keep the building in the redirect so the form stays on that building
    return RedirectResponse(f"/?building={building_val}", status_code=303)


@app.post("/add_weight/{entry_hash}")
async def add_weight(entry_hash: str, weight: float = Form(...)):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT weights FROM entries WHERE hash=?", (entry_hash,))
    row = cursor.fetchone()
    if row:
        weights = row[0].split(",") + [str(weight)]
        weights = weights[-5:]
        cursor.execute(
            "UPDATE entries SET weights=? WHERE hash=?", (",".join(weights), entry_hash)
        )
        conn.commit()
    conn.close()
    return RedirectResponse("/entries", status_code=303)


@app.post("/update_field")
async def update_field(
    hash: str = Form(...),
    field: str = Form(...),
    value: str = Form(...),
    index: int = Form(None),  # Optional index parameter for weights
):
    if field not in {"name", "room", "admission_date", "weight"}:
        return JSONResponse({"error": "Invalid field"}, status_code=400)
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    if field == "weight":
        if index is None:
            return JSONResponse(
                {"error": "Missing index for weight update"}, status_code=400
            )
        # Fetch current weights string
        cursor.execute("SELECT weights FROM entries WHERE hash=?", (hash,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return JSONResponse({"error": "Entry not found"}, status_code=404)
        weights_str = row[0] or ""
        weights = weights_str.split(",") if weights_str else []
        # Pad weights if needed
        if len(weights) < index + 1:
            weights = ([""] * (index + 1 - len(weights))) + weights
        weights[index] = value
        new_weights_str = ",".join(weights)
        cursor.execute(
            "UPDATE entries SET weights=? WHERE hash=?", (new_weights_str, hash)
        )
    else:
        cursor.execute(f"UPDATE entries SET {field}=? WHERE hash=?", (value, hash))

    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "value": value})


@app.get("/entries", response_class=HTMLResponse)
async def entries(request: Request, building: Optional[str] = None):
    buildings = get_building_options()
    selected_building = building or (buildings[0] if buildings else "Unassigned")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    if selected_building and selected_building != "All":
        cursor.execute(
            "SELECT hash, name, room, weights, admission_date FROM entries WHERE COALESCE(NULLIF(building,''),'Unassigned') = ?",
            (selected_building,),
        )
    else:
        cursor.execute("SELECT hash, name, room, weights, admission_date FROM entries")
    rows = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "entries.html",
        {
            "request": request,
            "entries": rows,
            "buildings": buildings,
            "selected_building": selected_building,
        },
    )



@app.post("/delete")
async def delete(delete_hashes: Optional[List[str]] = Form(None)):
    if delete_hashes:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.executemany(
            "DELETE FROM entries WHERE hash=?", [(h,) for h in delete_hashes]
        )
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
async def generate_report(building: Optional[str] = None):
    selected = (building or "").strip() or None
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    if selected:
        cursor.execute(
            "SELECT name, room, weights, admission_date FROM entries WHERE COALESCE(NULLIF(building,''),'Unassigned') = ?",
            (selected,),
        )
    else:
        cursor.execute("SELECT name, room, weights, admission_date FROM entries")
    rows = cursor.fetchall()
    conn.close()

    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 14)
    scope = f" — {selected}" if selected else ""
    report_title = f"Weight Report{scope} — Generated {datetime.now().strftime('%B %d, %Y')}"
    pdf.cell(0, 10, report_title, ln=True, align="C")

    col_widths = {"name": 50, "room": 30, "admission_date": 40, "last_weight": 30, "weights": 40}

    pdf.set_font("Arial", "B", 12)
    pdf.cell(col_widths["name"], 10, "Name", 1)
    pdf.cell(col_widths["room"], 10, "Room", 1)
    pdf.cell(col_widths["admission_date"], 10, "Admission Date", 1)
    pdf.cell(col_widths["last_weight"], 10, "Last Weight", 1)
    pdf.cell(col_widths["weights"], 10, "Weights", 1, ln=True)

    pdf.set_font("Arial", "", 12)
    for name, room, weights, admission_date in rows:
        last_weight = weights.split(",")[-1]
        pdf.cell(col_widths["name"], 10, name, 1)
        pdf.cell(col_widths["room"], 10, room or "N/A", 1)
        formatted_date = ""
        if admission_date:
            try:
                formatted_date = datetime.strptime(admission_date, "%Y-%m-%d").strftime("%B %d")
            except ValueError:
                logger.warning(f"Date {admission_date} did not match %Y-%m-%d")
                formatted_date = admission_date
        pdf.cell(col_widths["admission_date"], 10, formatted_date, 1)
        pdf.cell(col_widths["last_weight"], 10, str(int(float(last_weight))), 1)
        pdf.cell(col_widths["weights"], 10, "", 1, ln=True)

    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    pdf.output(REPORT_PATH)
    # keep the building on the download route so your UI can preserve selection
    filename = f"weight_report{('-' + selected) if selected else ''}.pdf"
    return FileResponse(REPORT_PATH, media_type="application/pdf", filename=filename)
