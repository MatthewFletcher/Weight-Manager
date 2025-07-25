from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF
import sqlite3
import os
from typing import List, Optional

app = FastAPI()
DATABASE = "data/weights.db"
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Ensure database exists
def init_db():
    conn = sqlite3.connect(DATABASE)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS entries (
            id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            room TEXT NOT NULL,
            weights TEXT NOT NULL
        )
    ''')
    conn.close()

init_db()

@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    return templates.TemplateResponse("entry_form.html", {"request": request})

@app.post("/add")
async def add_entry(name: str = Form(...), room: str = Form(...), weight: float = Form(...)):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT weights FROM entries WHERE name=? AND room=?", (name, room))
    row = cursor.fetchone()
    if row:
        weights = row[0].split(",") + [str(weight)]
        weights = weights[-5:]  # Keep last 5
        cursor.execute("UPDATE entries SET weights=? WHERE name=? AND room=?", (",".join(weights), name, room))
    else:
        cursor.execute("INSERT INTO entries (name, room, weights) VALUES (?, ?, ?)", (name, room, str(weight)))
    conn.commit()
    conn.close()
    return RedirectResponse("/", status_code=303)

@app.post("/add_weight/{entry_id}")
async def add_weight(entry_id: int, weight: float = Form(...)):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT weights FROM entries WHERE id=?", (entry_id,))
    row = cursor.fetchone()
    if row:
        weights = row[0].split(",") + [str(weight)]
        weights = weights[-5:]
        cursor.execute("UPDATE entries SET weights=? WHERE id=?", (",".join(weights), entry_id))
        conn.commit()
    conn.close()
    return RedirectResponse("/entries", status_code=303)

@app.get("/entries", response_class=HTMLResponse)
async def entries(request: Request):
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries")
    rows = cursor.fetchall()
    conn.close()
    return templates.TemplateResponse("entries.html", {"request": request, "entries": rows})

@app.post("/delete")
async def delete(delete_ids: Optional[List[str]] = Form(None)):
    if delete_ids:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.executemany("DELETE FROM entries WHERE id=?", [(int(entry_id),) for entry_id in delete_ids])
        conn.commit()
        conn.close()
    return RedirectResponse("/entries", status_code=303)

@app.get("/report")
async def generate_report():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT name, room, weights FROM entries")
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
    pdf.cell(40, 10, "Last Weight", 1)
    pdf.cell(50, 10, "Notes", 1, ln=True)

    pdf.set_font("Arial", "", 12)
    for name, room, weights in rows:
        last_weight = weights.split(",")[-1]
        pdf.cell(60, 10, name, 1)
        pdf.cell(40, 10, room, 1)
        pdf.cell(40, 10, last_weight, 1)
        pdf.cell(50, 10, "", 1, ln=True)

    report_path = "data/report.pdf"
    pdf.output(report_path)
    return FileResponse(report_path, media_type="application/pdf", filename="weight_report.pdf")

