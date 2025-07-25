import os
import sqlite3
import shutil
import pytest
from fastapi.testclient import TestClient
from app import app, DATABASE, init_db

@pytest.fixture(autouse=True)
def setup_and_teardown_db(tmp_path):
    # Ensure test isolation: use a temp DB file
    test_db = tmp_path / "test_weights.db"
    os.environ["TEST_DATABASE"] = str(test_db)
    # Patch the global variable
    global DATABASE
    DATABASE = str(test_db)
    init_db()
    yield
    # Clean up
    if os.path.exists(test_db):
        os.remove(test_db)

@pytest.fixture
def client():
    return TestClient(app)

def test_entry_form_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert "Weight Entry Form" in resp.text

def test_add_entry_and_list_entries(client):
    # Add an entry
    resp = client.post("/add", data={"name": "Alice", "room": "101", "weight": 150.0})
    assert resp.status_code == 303

    # Should be in /entries
    resp2 = client.get("/entries")
    assert resp2.status_code == 200
    assert "Alice" in resp2.text
    assert "101" in resp2.text
    assert "150" in resp2.text

def test_add_weight(client):
    # Add and get entry id
    client.post("/add", data={"name": "Bob", "room": "202", "weight": 180.5})
    # Query for Bob's ID
    conn = sqlite3.connect(DATABASE)
    row = conn.execute("SELECT id FROM entries WHERE name=? AND room=?", ("Bob", "202")).fetchone()
    entry_id = row[0]
    conn.close()

    # Add a second weight
    resp = client.post(f"/add_weight/{entry_id}", data={"weight": 179.5})
    assert resp.status_code == 303

    # Check both weights present in DB
    conn = sqlite3.connect(DATABASE)
    weights = conn.execute("SELECT weights FROM entries WHERE id=?", (entry_id,)).fetchone()[0]
    assert weights.split(",")[-2:] == ["180.5", "179.5"]
    conn.close()

def test_delete_entry(client):
    # Add entry
    client.post("/add", data={"name": "Carol", "room": "301", "weight": 160.0})
    conn = sqlite3.connect(DATABASE)
    entry_id = conn.execute("SELECT id FROM entries WHERE name=?", ("Carol",)).fetchone()[0]
    conn.close()

    # Delete entry
    resp = client.post("/delete", data={"delete_ids": str(entry_id)})
    assert resp.status_code == 303

    # Check not in DB
    conn = sqlite3.connect(DATABASE)
    row = conn.execute("SELECT * FROM entries WHERE id=?", (entry_id,)).fetchone()
    assert row is None
    conn.close()

def test_generate_report(client):
    # Add entry
    client.post("/add", data={"name": "Dave", "room": "401", "weight": 200.0})
    resp = client.get("/report")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"

def test_help_page(client, tmp_path):
    # Create a help file
    help_dir = tmp_path / "help"
    help_dir.mkdir()
    help_file = help_dir / "entries.md"
    help_file.write_text("# Help for entries page")
    # Patch location
    import app as appmod
    old_dir = os.getcwd()
    os.chdir(tmp_path)
    try:
        resp = client.get("/help/entries")
        assert resp.status_code == 200
        assert "Help for entries page" in resp.text
    finally:
        os.chdir(old_dir)
