import sqlite3

DB_PATH = r".\instance\manto.db"

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

tables = cur.execute(
    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
).fetchall()

print("tables:", tables)

# tenta contar talentos em algumas tabelas comuns
candidates = ["talent", "talents", "people", "persons", "artists", "users"]
for t in candidates:
    try:
        n = cur.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        print(f"count {t}:", n)
    except Exception as e:
        pass

conn.close()
