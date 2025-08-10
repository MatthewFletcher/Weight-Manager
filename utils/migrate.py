#!/usr/bin/env python3
import os
import sqlite3
import hashlib
import argparse
import sys

DEFAULT_DB = os.environ.get("DB_PATH", "/app/data/weights.db")  # adjust if needed

def compute_hash(name: str, room: str | None, building: str | None, salt: int = 0) -> str:
    room_val = (room or "").strip() or "N/A"
    building_val = (building or "").strip() or "Unassigned"
    base = f"{name.strip()}::{room_val}::{building_val}"
    if salt:
        base = f"{base}::salt{salt}"
    return hashlib.sha256(base.encode()).hexdigest()[:12]

def column_exists(cur: sqlite3.Cursor, table: str, col: str) -> bool:
    cur.execute(f"PRAGMA table_info({table})")
    return any(row[1] == col for row in cur.fetchall())

def main():
    ap = argparse.ArgumentParser(description="Migrate DB: add building column and re-hash primary keys.")
    ap.add_argument("--db", default=DEFAULT_DB, help=f"Path to sqlite DB (default: {DEFAULT_DB})")
    ap.add_argument("--dry-run", action="store_true", help="Show what would change, but do not write.")
    ap.add_argument("--verbose", action="store_true", help="Print per-row changes.")
    args = ap.parse_args()

    if not os.path.exists(args.db):
        print(f"ERROR: DB not found at {args.db}", file=sys.stderr)
        return 1

    conn = sqlite3.connect(args.db)
    conn.isolation_level = None  # explicit transactions
    cur = conn.cursor()

    try:
        cur.execute("BEGIN")

        # 1) Ensure table exists
        cur.execute("""
            SELECT name FROM sqlite_master WHERE type='table' AND name='entries'
        """)
        if cur.fetchone() is None:
            raise RuntimeError("Table 'entries' not found")

        # 2) Add building column if missing
        if not column_exists(cur, "entries", "building"):
            cur.execute("ALTER TABLE entries ADD COLUMN building TEXT")
            if args.verbose:
                print("Added column 'building'")

        # 3) Default building to 'Unassigned' if NULL/empty
        cur.execute("""
            UPDATE entries SET building = 'Unassigned'
            WHERE building IS NULL OR TRIM(building) = ''
        """)
        if args.verbose:
            print("Backfilled empty/NULL 'building' to 'Unassigned'")

        # 4) Fetch rows to recompute hashes
        cur.execute("""
            SELECT rowid, hash, name, room, building FROM entries
        """)
        rows = cur.fetchall()

        # Build a set of hashes to quickly check collisions (current + planned)
        cur.execute("SELECT hash FROM entries")
        existing_hashes = {h[0] for h in cur.fetchall()}

        updates = []
        for rowid, old_hash, name, room, building in rows:
            # Compute new hash (may be identical if your prior scheme already matched)
            salt = 0
            new_hash = compute_hash(name, room, building, salt)
            # If it's the same, skip
            if new_hash == old_hash:
                continue
            # Collision safety: make sure it's unique (excluding the row itself, which still has old_hash)
            while new_hash in existing_hashes:
                salt += 1
                new_hash = compute_hash(name, room, building, salt)
            # Reserve it to avoid future collisions in this loop
            existing_hashes.add(new_hash)
            updates.append((new_hash, rowid))
            if args.verbose:
                print(f"rowid={rowid} {old_hash} -> {new_hash}  (name='{name}', room='{room}', building='{building}')")

        if args.dry_run:
            print(f"DRY RUN: would update {len(updates)} rows")
            cur.execute("ROLLBACK")
            return 0

        # 5) Apply updates
        for new_hash, rowid in updates:
            cur.execute("UPDATE entries SET hash = ? WHERE rowid = ?", (new_hash, rowid))

        cur.execute("COMMIT")
        print(f"Migration complete. Updated hashes: {len(updates)}")
        print("Tip: consider running 'VACUUM' during maintenance to compact the DB.")
        return 0

    except Exception as e:
        cur.execute("ROLLBACK")
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    finally:
        conn.close()

if __name__ == "__main__":
    raise SystemExit(main())

