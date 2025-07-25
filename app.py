from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF
import sqlite3
import os
from jinja2 import Template

app = FastAPI()

DATABASE = "data/weights.db"

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

# Templates
ENTRY_FORM = '''
<html>
<body>
<h2>Weight Entry Form</h2>
<form action="/add" method="post">
Name: <input type="text" name="name" required><br>
Room: <input type="text" name="room" required><br>
Weight: <input type="number" step="0.1" name="weight" required><br>
<button type="submit">Add Entry</button>
</form>
<a href="/entries">View All Entries</a><br>
<a href="/report">Generate PDF Report</a>
</body>
</html>
'''

ENTRIES_TEMPLATE = '''
<html>
<body>
<h2>All Entries</h2>
<table border="1">
<tr><th>Name</th><th>Room</th><th>Weights</th><th>Action</th></tr>
{% for entry in entries %}
<tr>
<td>{{entry[1]}}</td>
<td>{{entry[2]}}</td>
<td>{{entry[3]}}</td>
<td><a href="/delete/{{entry[0]}}">Delete</a></td>
</tr>
{% endfor %}
</table>
<a href="/">Back to form</a>
</body>
</html>
'''

# Routes
@app.get("/", response_class=HTMLResponse)
async def form():
    return ENTRY_FORM

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

@app.get("/entries", response_class=HTMLResponse)
async def entries():
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entries")
    rows = cursor.fetchall()
    conn.close()
    template = Template(ENTRIES_TEMPLATE)
    return template.render(entries=rows)

@app.get("/delete/{entry_id}")
async def delete(entry_id: int):
    conn = sqlite3.connect(DATABASE)
    conn.execute("DELETE FROM entries WHERE id=?", (entry_id,))
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
    pdf.cell(0, 10, "Weight Report", ln=True, align="C")

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

# Run with: docker-compose up -d

