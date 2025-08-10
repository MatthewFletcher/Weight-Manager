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


from fastapi import UploadFile, File, Form
import json

def count_entries_by_building():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("""
        SELECT COALESCE(NULLIF(building,''), 'Unassigned') AS b, COUNT(*)
        FROM entries
        GROUP BY b
        ORDER BY b COLLATE NOCASE
    """)
    rows = cur.fetchall()
    conn.close()
    return rows  # list[(building, count)]



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


@app.get("/", response_class=HTMLResponse)
async def form(request: Request, building: Optional[str] = None):
    # If user typed a brand-new building via the filter, add it so it shows up even with 0 entries
    if building and not building_exists(building):
        ensure_building_exists(building)

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


def get_building_options():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT name FROM buildings ORDER BY name COLLATE NOCASE")
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows or ["Unassigned"]

def building_exists(name: str) -> bool:
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM buildings WHERE name = ?", (name,))
    exists = cur.fetchone() is not None
    conn.close()
    return exists

def ensure_building_exists(name: str) -> str:
    val = (name or "").strip() or "Unassigned"
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO buildings(name) VALUES (?)", (val,))
    conn.commit()
    conn.close()
    return val



@app.get("/admin", response_class=HTMLResponse)
async def admin(request: Request):
    buildings = get_building_options()  # from earlier step
    counts = dict(count_entries_by_building())
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "buildings": buildings,
            "counts": counts,
        },
    )

# --- Buildings CRUD-ish ---
@app.post("/admin/buildings/add")
async def admin_building_add(name: str = Form(...)):
    name = (name or "").strip() or "Unassigned"
    ensure_building_exists(name)
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/buildings/rename")
async def admin_building_rename(old_name: str = Form(...), new_name: str = Form(...)):
    old = (old_name or "").strip()
    new = (new_name or "").strip()
    if not old or not new:
        return RedirectResponse("/admin", status_code=303)

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    # Move entries
    cur.execute("""
        UPDATE entries
        SET building = ?
        WHERE COALESCE(NULLIF(building,''), 'Unassigned') = ?
    """, (new, old))
    # Update buildings table
    cur.execute("INSERT OR IGNORE INTO buildings(name) VALUES (?)", (new,))
    cur.execute("DELETE FROM buildings WHERE name = ?", (old,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/buildings/merge")
async def admin_building_merge(source: str = Form(...), target: str = Form(...)):
    src = (source or "").strip()
    tgt = (target or "").strip()
    if not src or not tgt or src == tgt:
        return RedirectResponse("/admin", status_code=303)

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("""
        UPDATE entries
        SET building = ?
        WHERE COALESCE(NULLIF(building,''), 'Unassigned') = ?
    """, (tgt, src))
    cur.execute("INSERT OR IGNORE INTO buildings(name) VALUES (?)", (tgt,))
    cur.execute("DELETE FROM buildings WHERE name = ?", (src,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

@app.post("/admin/buildings/delete")
async def admin_building_delete(name: str = Form(...), reassign_to: str = Form(None)):
    name = (name or "").strip()
    reassign = (reassign_to or "").strip()

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    # How many entries use this building?
    cur.execute("""
        SELECT COUNT(*) FROM entries
        WHERE COALESCE(NULLIF(building,''), 'Unassigned') = ?
    """, (name,))
    count = cur.fetchone()[0]

    if count and not reassign:
        # If entries exist and no reassign provided, just bail safely
        conn.close()
        # Could show a flash message; for now just reload
        return RedirectResponse("/admin", status_code=303)

    if count and reassign:
        cur.execute("""
            UPDATE entries SET building = ?
            WHERE COALESCE(NULLIF(building,''), 'Unassigned') = ?
        """, (reassign, name))

    cur.execute("DELETE FROM buildings WHERE name = ?", (name,))
    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

# --- Export / Import ---
@app.get("/admin/export")
async def admin_export():
    # Export buildings + entries as a JSON file
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT name FROM buildings ORDER BY name")
    buildings = [r[0] for r in cur.fetchall()]
    cur.execute("SELECT hash, name, room, weights, admission_date, COALESCE(NULLIF(building,''), 'Unassigned') FROM entries")
    entries = [
        {
            "hash": h, "name": n, "room": r, "weights": w,
            "admission_date": d, "building": b
        }
        for (h, n, r, w, d, b) in cur.fetchall()
    ]
    conn.close()

    payload = {"buildings": buildings, "entries": entries}
    tmp = os.path.join(BASE_DIR, "data", "export.json")
    os.makedirs(os.path.dirname(tmp), exist_ok=True)
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return FileResponse(tmp, media_type="application/json", filename="weights_export.json")

@app.post("/admin/import")
async def admin_import(file: UploadFile = File(...)):
    # Merge import: adds buildings; upserts or inserts entries
    data = json.loads((await file.read()).decode("utf-8"))
    buildings = data.get("buildings", [])
    entries = data.get("entries", [])

    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()

    for b in buildings:
        cur.execute("INSERT OR IGNORE INTO buildings(name) VALUES (?)", (b.strip() or "Unassigned",))

    for e in entries:
        h = e.get("hash")
        name = e.get("name")
        room = e.get("room")
        weights = e.get("weights", "")
        admission_date = e.get("admission_date")
        building = (e.get("building") or "Unassigned").strip() or "Unassigned"

        # Upsert by hash (if hash collides, we overwrite the row for simplicity)
        cur.execute("SELECT 1 FROM entries WHERE hash=?", (h,))
        if cur.fetchone():
            cur.execute("""
                UPDATE entries
                SET name=?, room=?, weights=?, admission_date=?, building=?
                WHERE hash=?
            """, (name, room, weights, admission_date, building, h))
        else:
            cur.execute("""
                INSERT INTO entries(hash, name, room, weights, admission_date, building)
                VALUES(?, ?, ?, ?, ?, ?)
            """, (h, name, room, weights, admission_date, building))

    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)

# --- Maintenance tools ---
@app.post("/admin/recalc-hashes")
async def admin_recalc_hashes():
    conn = sqlite3.connect(DATABASE)
    cur = conn.cursor()
    cur.execute("SELECT rowid, name, room, COALESCE(NULLIF(building,''),'Unassigned') FROM entries")
    rows = cur.fetchall()
    existing = set()
    cur.execute("SELECT hash FROM entries")
    existing |= {r[0] for r in cur.fetchall()}

    def _hash(n, r, b, salt=0):
        base = f"{(n or '').strip()}::{(r or '').strip() or 'N/A'}::{(b or '').strip() or 'Unassigned'}"
        if salt:
            base += f"::salt{salt}"
        return hashlib.sha256(base.encode()).hexdigest()[:12]

    updates = []
    for rowid, name, room, building in rows:
        salt = 0
        newh = _hash(name, room, building, salt)
        while newh in existing:
            salt += 1
            newh = _hash(name, room, building, salt)
        existing.add(newh)
        updates.append((newh, rowid))

    for newh, rid in updates:
        cur.execute("UPDATE entries SET hash=? WHERE rowid=?", (newh, rid))

    conn.commit()
    conn.close()
    return RedirectResponse("/admin", status_code=303)



@app.post("/add")
async def add_entry(
    name: str = Form(...),
    room: Optional[str] = Form(None),
    admission_date: str = Form(...),
    weight: float = Form(...),
    building: Optional[str] = Form(None),
):
    building_val = ensure_building_exists(building)
    room_val = (room or "").strip()
    h = entry_hash(name, room_val, building_val)  # keep your 3-part hash

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
    if building and not building_exists(building):
        ensure_building_exists(building)

    buildings = get_building_options()
    selected_building = building or (buildings[0] if buildings else "Unassigned")

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT hash, name, room, weights, admission_date
        FROM entries
        WHERE COALESCE(NULLIF(building,''),'Unassigned') = ?
        """,
        (selected_building,),
    )
    rows = cursor.fetchall()
    conn.close()

    return templates.TemplateResponse(
        "entries.html",
        {"request": request, "entries": rows, "buildings": buildings, "selected_building": selected_building},
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
    if selected and not building_exists(selected):
        ensure_building_exists(selected)

    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    if selected:
        cursor.execute(
            """
            SELECT name, room, weights, admission_date
            FROM entries
            WHERE COALESCE(NULLIF(building,''),'Unassigned') = ?
            """,
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
