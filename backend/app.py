"""
Safe Bite AI – Flask Backend
Run:  python app.py
Deps: pip install flask flask-cors pymysql pillow pytesseract bcrypt pyjwt python-dotenv
"""

import os, re, json, base64, datetime
from shutil import which
from functools import wraps

import bcrypt
import jwt
import sqlite3
from dotenv import load_dotenv
from flask import Flask, jsonify, request, g
from flask_cors import CORS
from PIL import Image
import pytesseract
import io

# Load backend/.env so DB and JWT settings are available in local/dev runs.
load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

def configure_tesseract():
    """
    Configure pytesseract to find the binary on Windows and standard PATH setups.
    Priority:
    1) TESSERACT_CMD env var
    2) Existing PATH lookup
    3) Common Windows install locations
    """
    env_cmd = os.getenv("TESSERACT_CMD", "").strip()
    candidates = [env_cmd] if env_cmd else []

    path_cmd = which("tesseract")
    if path_cmd:
        candidates.append(path_cmd)

    candidates.extend([
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ])

    for cmd in candidates:
        if cmd and os.path.exists(cmd):
            pytesseract.pytesseract.tesseract_cmd = cmd
            return cmd
    return None

TESSERACT_PATH = configure_tesseract()

# ─────────────────────────────────────────
# App setup
# ─────────────────────────────────────────
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}})

SECRET_KEY = os.getenv("JWT_SECRET", "safebite-dev-secret-change-in-prod")
TOKEN_EXPIRY_HOURS = 24

# ─────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────

SCHEMA_COMPAT_CHECKED = False

class DatabaseUnavailableError(Exception):
    pass

def ensure_schema_compatibility(conn):
    """
    Keep runtime schema compatible with current app behavior.
    Manual/OCR analysis may not have a concrete product_id.
    """
    with conn.cursor() as cur:
        cur.execute(
            "ALTER TABLE product_analysis MODIFY COLUMN product_id INT NULL"
        )
    conn.commit()

def get_db():
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
    return g.db

@app.errorhandler(DatabaseUnavailableError)
def handle_db_unavailable(err):
    return jsonify({"error": str(err)}), 503

@app.errorhandler(sqlite3.Error)
def handle_mysql_error(err):
    app.logger.exception("MySQL query failed")
    return jsonify({"error": f"Database query failed: {err}"}), 500

@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db:
        db.close()

def query(sql, args=(), one=False):
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
    return cur.lastrowid

# ─────────────────────────────────────────
# JWT auth
# ─────────────────────────────────────────
def generate_token(user_id: int, email: str) -> str:
    payload = {
        "user_id": user_id,
        "email":   email,
        "exp":     datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get("Authorization", "").replace("Bearer ", "")
        if not token:
            return jsonify({"error": "Missing token"}), 401
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
            g.current_user_id = payload["user_id"]
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"error": "Invalid token"}), 401
        return f(*args, **kwargs)
    return decorated

# ─────────────────────────────────────────
# Ingredient safety engine
# ─────────────────────────────────────────
AGE_COL = {
    "child":  "age_child",
    "teen":   "age_teen",
    "adult":  "age_adult",
    "senior": "age_senior",
}

RESTRICTION_RULES = {
    "diabetic":           ["high fructose corn syrup", "sucralose", "aspartame", "saccharin"],
    "hypertension":       ["sodium benzoate", "sodium nitrite", "msg", "monosodium glutamate"],
    "vegan":              [],  # handled via is_vegan_unsafe flag
    "vegetarian":         [],  # handled via is_vegetarian_unsafe flag
    "nut_allergy":        ["peanut"],  # also checks allergen table
    "lactose_intolerant": ["milk"],
    "gluten_intolerant":  ["gluten"],
}

RISK_SCORE_MAP = {"high": 2.4, "medium": 1.3, "low": 0.6, "safe": 0.0}
RESTRICTION_MAP = {"avoid": 1.6, "limit": 1.3, "moderate": 1.1, "safe": 1.0}
SCORE_MAX = 10
MIN_RISK_BUDGET = 6.0
RISK_BUDGET_PER_INGREDIENT = 2.5

def parse_ingredients(raw_text: str) -> list[str]:
    """Normalize raw ingredient text into a clean list."""
    raw_text = raw_text.lower()
    raw_text = re.sub(r"\bingredients?\b\s*[:\-]?", " ", raw_text)
    raw_text = re.sub(r"\(.*?\)", " ", raw_text)   # remove parenthetical
    raw_text = re.sub(r"[^a-z0-9 ,;/\n]", " ", raw_text)
    raw_text = re.sub(r"\s+", " ", raw_text).strip()
    items = [i.strip() for i in re.split(r"[,;/\n]", raw_text) if i.strip()]
    return items

def _match_ingredient(raw_name: str, db_map: dict[str, dict]) -> dict | None:
    raw = re.sub(r"\s+", " ", raw_name.strip().lower())
    if not raw:
        return None

    for db_name, db_row in db_map.items():
        escaped = re.escape(db_name)
        pattern = rf"(^|[^a-z0-9]){escaped}([^a-z0-9]|$)"
        if re.search(pattern, raw):
            return db_row

    for db_name, db_row in db_map.items():
        if db_name in raw or raw in db_name:
            return db_row

    return None

def _grade_for_score(score: int) -> str:
    if score >= 8:
        return "A"
    if score >= 6:
        return "B"
    if score >= 4:
        return "C"
    if score >= 2:
        return "D"
    return "F"

def analyze_ingredients(ingredients: list[str], age_group: str, restrictions: list[str]) -> dict:
    """
    Core safety engine.
    Returns: safety_score (0-10), status, flagged list, and detail per ingredient.
    """
    age_col = AGE_COL.get(age_group, "age_adult")
    all_db_ingredients = query(
        f"SELECT id, name, risk_level, reason, category, {age_col} AS age_restriction, "
        f"is_vegan_unsafe, is_vegetarian_unsafe FROM ingredients"
    )
    db_map = {row["name"].lower(): row for row in all_db_ingredients}

    flagged = []
    total_risk = 0.0
    ingredient_details = []

    matched_count = 0
    for raw_name in ingredients:
        matched_row = _match_ingredient(raw_name, db_map)

        if matched_row:
            matched_count += 1
            base = RISK_SCORE_MAP.get(matched_row["risk_level"], 0)
            mult = RESTRICTION_MAP.get(matched_row["age_restriction"], 1.0)

            # Extra penalty for user's health restrictions
            restriction_hit = False
            for r in restrictions:
                r_lower = r.lower()
                if r_lower in ("vegan",) and matched_row["is_vegan_unsafe"]:
                    mult = max(mult, 1.8)
                    restriction_hit = True
                elif r_lower in ("vegetarian",) and matched_row["is_vegetarian_unsafe"]:
                    mult = max(mult, 1.8)
                    restriction_hit = True
                elif r_lower in RESTRICTION_RULES:
                    if matched_row["name"].lower() in RESTRICTION_RULES[r_lower]:
                        mult = max(mult, 1.4)
                        restriction_hit = True

            score = base * mult
            total_risk += score

            if score > 0:
                flagged.append({
                    "id":           matched_row["id"],
                    "name":         matched_row["name"],
                    "risk_level":   matched_row["risk_level"],
                    "category":     matched_row["category"],
                    "reason":       matched_row["reason"],
                    "age_restriction": matched_row["age_restriction"],
                    "restriction_hit": restriction_hit,
                    "risk_score":   round(score, 1),
                })

        ingredient_details.append({
            "raw":     raw_name,
            "matched": matched_row["name"] if matched_row else None,
            "flagged": matched_row is not None and (RISK_SCORE_MAP.get(matched_row["risk_level"], 0) > 0),
        })

    # Score on a 0-10 scale. Coverage penalty prevents misleading perfect scores when matches are sparse.
    coverage = (matched_count / len(ingredients)) if ingredients else 0.0
    coverage_penalty = 0.0
    if coverage < 0.25:
        coverage_penalty = round((0.25 - coverage) * 4.8, 1)

    risk_budget = max(MIN_RISK_BUDGET, len(ingredients) * RISK_BUDGET_PER_INGREDIENT)
    normalized_risk = min(1.0, total_risk / risk_budget)
    raw_score = SCORE_MAX * (1.0 - normalized_risk) - coverage_penalty
    safety_score = max(0, min(SCORE_MAX, int(round(raw_score))))
    grade = _grade_for_score(safety_score)

    if safety_score >= 7:
        status = "safe"
    elif safety_score >= 4:
        status = "moderate"
    else:
        status = "unsafe"

    return {
        "safety_score":      safety_score,
        "score_out_of":      SCORE_MAX,
        "grade":             grade,
        "match_confidence":  round(coverage, 2),
        "status":            status,
        "flagged":           sorted(flagged, key=lambda x: -x["risk_score"]),
        "ingredient_details": ingredient_details,
        "total_ingredients": len(ingredients),
        "matched_count":     matched_count,
        "flagged_count":     len(flagged),
    }

# ─────────────────────────────────────────
# OCR helper
# ─────────────────────────────────────────
def extract_text_from_image(image_bytes: bytes) -> str:
    if not TESSERACT_PATH:
        raise RuntimeError(
            "Tesseract binary not found. Install Tesseract OCR or set TESSERACT_CMD in backend/.env."
        )
    img = Image.open(io.BytesIO(image_bytes))
    # Pre-process for better OCR
    img = img.convert("L")          # grayscale
    text = pytesseract.image_to_string(img, config="--psm 6")
    return text

# ─────────────────────────────────────────
# Routes – Auth
# ─────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
def register():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")
    full_name = data.get("full_name", "")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    existing = query("SELECT id FROM users WHERE email=%s", (email,), one=True)
    if existing:
        return jsonify({"error": "Email already registered"}), 409

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    user_id = execute(
        "INSERT INTO users (email, password_hash, full_name) VALUES (%s,%s,%s)",
        (email, pw_hash, full_name)
    )
    token = generate_token(user_id, email)
    return jsonify({"token": token, "user_id": user_id, "email": email}), 201


@app.route("/api/auth/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email", "").strip().lower()
    password = data.get("password", "")

    user = query("SELECT * FROM users WHERE email=%s", (email,), one=True)
    if not user or not bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
        return jsonify({"error": "Invalid credentials"}), 401

    token = generate_token(user["id"], user["email"])
    return jsonify({"token": token, "user_id": user["id"], "email": user["email"]}), 200

# ─────────────────────────────────────────
# Routes – User Profile
# ─────────────────────────────────────────
@app.route("/api/user/profile", methods=["GET"])
@require_auth
def get_profile():
    user = query("SELECT id, email, full_name, age_group, created_at FROM users WHERE id=%s",
                 (g.current_user_id,), one=True)
    restrictions = query("SELECT restriction FROM user_restrictions WHERE user_id=%s",
                         (g.current_user_id,))
    user["restrictions"] = [r["restriction"] for r in restrictions]
    return jsonify(user)


@app.route("/api/user/profile", methods=["PUT"])
@require_auth
def update_profile():
    data = request.get_json()
    execute("UPDATE users SET full_name=%s, age_group=%s WHERE id=%s",
            (data.get("full_name"), data.get("age_group", "adult"), g.current_user_id))

    # Replace restrictions
    execute("DELETE FROM user_restrictions WHERE user_id=%s", (g.current_user_id,))
    for r in data.get("restrictions", []):
        execute("INSERT IGNORE INTO user_restrictions (user_id, restriction) VALUES (%s,%s)",
                (g.current_user_id, r))
    return jsonify({"message": "Profile updated"})

# ─────────────────────────────────────────
# Routes – Products
# ─────────────────────────────────────────
@app.route("/api/products", methods=["GET"])
def list_products():
    category = request.args.get("category")
    if category:
        products = query("SELECT * FROM products WHERE category=%s ORDER BY name", (category,))
    else:
        products = query("SELECT * FROM products ORDER BY category, name")
    return jsonify(products)


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = query("SELECT * FROM products WHERE id=%s", (product_id,), one=True)
    if not product:
        return jsonify({"error": "Not found"}), 404
    return jsonify(product)


@app.route("/api/products/barcode/<barcode>", methods=["GET"])
def get_by_barcode(barcode):
    product = query("SELECT * FROM products WHERE barcode=%s", (barcode,), one=True)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)

# ─────────────────────────────────────────
# Routes – Analysis
# ─────────────────────────────────────────
@app.route("/api/analyze/text", methods=["POST"])
@require_auth
def analyze_text():
    """Analyze from manually entered ingredient text."""
    data = request.get_json()
    raw_text   = data.get("ingredients_text", "")
    age_group  = data.get("age_group", "adult")
    product_id = data.get("product_id")

    user = query("SELECT age_group FROM users WHERE id=%s", (g.current_user_id,), one=True)
    restrictions_rows = query(
        "SELECT restriction FROM user_restrictions WHERE user_id=%s", (g.current_user_id,))
    profile_restrictions = [r["restriction"] for r in restrictions_rows]
    request_restrictions = data.get("restrictions", []) or []
    restrictions = sorted(set(profile_restrictions + [str(r).strip().lower() for r in request_restrictions if str(r).strip()]))

    age_group = age_group or (user["age_group"] if user else "adult")
    ingredients = parse_ingredients(raw_text)
    if not ingredients:
        return jsonify({"error": "No ingredients found in provided text"}), 422
    result = analyze_ingredients(ingredients, age_group, restrictions)

    # Persist analysis
    analysis_id = execute(
        "INSERT INTO product_analysis (product_id, user_id, safety_score, status, age_group, detected_flags) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (product_id, g.current_user_id, result["safety_score"], result["status"],
         age_group, json.dumps([f["id"] for f in result["flagged"]]))
    )

    # Log scan
    execute(
        "INSERT INTO scan_history (user_id, product_id, scan_type, ocr_raw_text, result_id) "
        "VALUES (%s,%s,'manual',%s,%s)",
        (g.current_user_id, product_id, raw_text, analysis_id)
    )

    # Fetch alternatives if unsafe/moderate
    alternatives = []
    if product_id and result["status"] in ("unsafe", "moderate"):
        alternatives = query("SELECT * FROM alternatives WHERE product_id=%s", (product_id,))

    result["analysis_id"] = analysis_id
    result["alternatives"] = alternatives
    return jsonify(result)


@app.route("/api/analyze/image", methods=["POST"])
@require_auth
def analyze_image():
    """Upload image → OCR → analyze."""
    data = request.get_json(silent=True) or {}
    if "image" not in request.files and "image_base64" not in data:
        return jsonify({"error": "No image provided"}), 400

    if "image" in request.files:
        image_bytes = request.files["image"].read()
    else:
        b64 = data["image_base64"]
        image_bytes = base64.b64decode(b64)

    try:
        ocr_text = extract_text_from_image(image_bytes)
    except Exception as e:
        return jsonify({"error": f"OCR failed: {str(e)}"}), 422

    age_group = request.form.get("age_group") or data.get("age_group", "adult")

    restrictions_rows = query(
        "SELECT restriction FROM user_restrictions WHERE user_id=%s", (g.current_user_id,))
    restrictions = [r["restriction"] for r in restrictions_rows]

    ingredients = parse_ingredients(ocr_text)
    if not ingredients:
        return jsonify({"error": "No ingredients found in image", "ocr_text": ocr_text}), 422

    result = analyze_ingredients(ingredients, age_group, restrictions)

    analysis_id = execute(
        "INSERT INTO product_analysis (product_id, user_id, safety_score, status, age_group, detected_flags) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (None, g.current_user_id, result["safety_score"], result["status"],
         age_group, json.dumps([f["id"] for f in result["flagged"]]))
    )
    execute(
        "INSERT INTO scan_history (user_id, scan_type, ocr_raw_text, result_id) "
        "VALUES (%s,'image',%s,%s)",
        (g.current_user_id, ocr_text, analysis_id)
    )

    result["ocr_text"] = ocr_text
    result["analysis_id"] = analysis_id
    result["alternatives"] = []
    return jsonify(result)


@app.route("/api/analyze/product/<int:product_id>", methods=["POST"])
@require_auth
def analyze_product(product_id):
    """Analyze a known product from DB."""
    product = query("SELECT * FROM products WHERE id=%s", (product_id,), one=True)
    if not product:
        return jsonify({"error": "Product not found"}), 404

    data = request.get_json() or {}
    age_group = data.get("age_group", "adult")

    restrictions_rows = query(
        "SELECT restriction FROM user_restrictions WHERE user_id=%s", (g.current_user_id,))
    restrictions = [r["restriction"] for r in restrictions_rows]

    ingredients = parse_ingredients(product["raw_ingredients"] or "")
    result = analyze_ingredients(ingredients, age_group, restrictions)

    analysis_id = execute(
        "INSERT INTO product_analysis (product_id, user_id, safety_score, status, age_group, detected_flags) "
        "VALUES (%s,%s,%s,%s,%s,%s)",
        (product_id, g.current_user_id, result["safety_score"], result["status"],
         age_group, json.dumps([f["id"] for f in result["flagged"]]))
    )
    execute(
        "INSERT INTO scan_history (user_id, product_id, scan_type, result_id) "
        "VALUES (%s,%s,'image',%s)",
        (g.current_user_id, product_id, analysis_id)
    )

    alternatives = query("SELECT * FROM alternatives WHERE product_id=%s", (product_id,))
    result["product"]      = product
    result["analysis_id"]  = analysis_id
    result["alternatives"] = alternatives
    return jsonify(result)

# ─────────────────────────────────────────
# Routes – History
# ─────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
@require_auth
def get_history():
    rows = query(
        """SELECT sh.id, sh.scan_type, sh.scanned_at,
                  p.name AS product_name, p.category,
                  pa.safety_score, pa.status
           FROM scan_history sh
           LEFT JOIN products p         ON sh.product_id = p.id
           LEFT JOIN product_analysis pa ON sh.result_id  = pa.id
           WHERE sh.user_id = %s
           ORDER BY sh.scanned_at DESC
           LIMIT 50""",
        (g.current_user_id,)
    )
    return jsonify(rows)

# ─────────────────────────────────────────
# Routes – Ingredients reference
# ─────────────────────────────────────────
@app.route("/api/ingredients", methods=["GET"])
def list_ingredients():
    risk = request.args.get("risk")
    if risk:
        rows = query("SELECT * FROM ingredients WHERE risk_level=%s ORDER BY name", (risk,))
    else:
        rows = query("SELECT * FROM ingredients ORDER BY risk_level DESC, name")
    return jsonify(rows)

# ─────────────────────────────────────────
# Health check
# ─────────────────────────────────────────
@app.route("/api/health")
def health():
    return jsonify({
        "status": "ok",
        "version": "1.0.0",
        "tesseract_ready": bool(TESSERACT_PATH),
        "tesseract_path": TESSERACT_PATH,
    })

# ─────────────────────────────────────────
if __name__ == "__main__":
    app.run(debug=True, port=5000)
