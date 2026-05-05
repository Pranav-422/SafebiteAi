import os

with open('backend/app.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Replace imports
code = code.replace('import pymysql\nimport pymysql.cursors', 'import sqlite3')

# Replace get_db
get_db_old = '''def get_db():
    global SCHEMA_COMPAT_CHECKED
    if "db" not in g:
        try:
            g.db = pymysql.connect(**DB_CONFIG)
            if not SCHEMA_COMPAT_CHECKED:
                try:
                    ensure_schema_compatibility(g.db)
                except pymysql.MySQLError:
                    app.logger.warning("Schema compatibility check skipped", exc_info=True)
                SCHEMA_COMPAT_CHECKED = True
        except Exception as exc:
            app.logger.exception("Database connection failed")
            raise DatabaseUnavailableError(
                "Database connection failed. Install backend dependencies and verify MySQL credentials."
            ) from exc
    return g.db'''

get_db_new = '''def get_db():
    if "db" not in g:
        try:
            db_path = os.path.join(os.path.dirname(__file__), "safebite.db")
            conn = sqlite3.connect(db_path, timeout=10)
            conn.row_factory = sqlite3.Row
            g.db = conn
        except Exception as exc:
            app.logger.exception("Database connection failed")
            raise DatabaseUnavailableError(
                "Database connection failed. Verify SQLite DB path."
            ) from exc
    return g.db'''

code = code.replace(get_db_old, get_db_new)

query_old = '''def query(sql, args=(), one=False):
    cur = get_db().cursor()
    cur.execute(sql, args)
    return (cur.fetchone() if one else cur.fetchall())

def execute(sql, args=()):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(sql, args)
        last_id = cur.lastrowid
    db.commit()
    return last_id'''

query_new = '''def query(sql, args=(), one=False):
    sql = sql.replace("%s", "?")
    cur = get_db().cursor()
    cur.execute(sql, args)
    rv = cur.fetchall()
    rv = [dict(row) for row in rv]
    return (rv[0] if rv else None) if one else rv

def execute(sql, args=()):
    sql = sql.replace("%s", "?")
    sql = sql.replace("INSERT IGNORE", "INSERT OR IGNORE")
    db = get_db()
    cur = db.cursor()
    cur.execute(sql, args)
    db.commit()
    return cur.lastrowid'''

code = code.replace(query_old, query_new)

code = code.replace('@app.errorhandler(pymysql.MySQLError)', '@app.errorhandler(sqlite3.Error)')
code = code.replace('pymysql.MySQLError', 'sqlite3.Error')

with open('backend/app.py', 'w', encoding='utf-8') as f:
    f.write(code)
print('app.py patched!')
