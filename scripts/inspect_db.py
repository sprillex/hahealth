import sqlite3
import os
import argparse
import sys

DB_FILE = "health_app.db"

def get_db_connection():
    if not os.path.exists(DB_FILE):
        print(f"Error: Database file '{DB_FILE}' not found.")
        sys.exit(1)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def list_tables(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    return [table['name'] for table in tables]

def count_rows(conn, table_name):
    cursor = conn.cursor()
    cursor.execute(f"SELECT COUNT(*) as count FROM {table_name}")
    return cursor.fetchone()['count']

def dump_table(conn, table_name, limit=None):
    cursor = conn.cursor()
    query = f"SELECT * FROM {table_name}"
    if limit:
        query += f" LIMIT {limit}"

    try:
        cursor.execute(query)
    except sqlite3.OperationalError as e:
        print(f"Error querying table '{table_name}': {e}")
        return

    rows = cursor.fetchall()
    if not rows:
        print(f"Table '{table_name}' is empty.")
        return

    # Get column names
    headers = rows[0].keys()
    print(f"--- {table_name} ---")
    print(" | ".join(headers))
    print("-" * (len(headers) * 10))

    for row in rows:
        print(" | ".join(str(item) for item in row))
    print("\n")

def main():
    parser = argparse.ArgumentParser(description="Inspect the health_app.db SQLite database.")
    parser.add_argument("table", nargs="?", help="Name of the table to dump (optional)")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of rows to display")
    parser.add_argument("--all", action="store_true", help="Dump all tables")

    args = parser.parse_args()

    conn = get_db_connection()

    if args.table:
        dump_table(conn, args.table, args.limit)
    elif args.all:
        tables = list_tables(conn)
        for table in tables:
            dump_table(conn, table, args.limit)
    else:
        print(f"Database: {DB_FILE}")
        tables = list_tables(conn)
        print(f"Found {len(tables)} tables:")
        print(f"{'Table Name':<30} {'Row Count'}")
        print("-" * 45)
        for table in tables:
            count = count_rows(conn, table)
            print(f"{table:<30} {count}")

        print("\nUsage:")
        print("  python scripts/inspect_db.py <table_name>   # Dump specific table")
        print("  python scripts/inspect_db.py --all          # Dump all tables")

    conn.close()

if __name__ == "__main__":
    main()
