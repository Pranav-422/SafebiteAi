"""
Safe Bite AI – Flask Backend

Dev:   python app.py                    (needs JWT_SECRET in backend/.env, see .env.example)
Prod:  gunicorn -c gunicorn.conf.py app:app
"""

import base64
import binascii
import datetime
import io
import json
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
import uuid
from functools import wraps
from shutil import which

import bcrypt
import jwt
import pytesseract
from dotenv import load_dotenv
from flask import Flask, g, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from PIL import Image, UnidentifiedImageError
from werkzeug.exceptions import HTTPException
from werkzeug.middleware.proxy_fix import ProxyFix

import seed_data
from safety_engine import (AGE_GROUPS, ALLOWED_RESTRICTIONS, IngredientIndex, analyze_ingredients,
                           parse_ingredients)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s %(message)s")
log = logging.getLogger("safebite")


# ─────────────────────────────────────────
# Configuration (all from environment)
# ─────────────────────────────────────────
def _env_int(name, default):
    return int(os.getenv(name, default))


SECRET_KEY = os.getenv("JWT_SECRET", "")
if len(SECRET_KEY) < 32:
    raise RuntimeError(
        "JWT_SECRET must be set to a random value of at least 32 characters. "
        "Generate one with:  python -c \"import secrets; print(secrets.token_urlsafe(48))\""
    )
TOKEN_EXPIRY_HOURS = _env_int("TOKEN_EXPIRY_HOURS", 24)
JWT_ALGORITHM = "HS256"
JWT_ISSUER = "safebite-api"

# Relative paths are resolved against backend/, not the current working directory.
DATABASE_PATH = os.path.join(BASE_DIR, os.getenv("DATABASE_PATH", "safebite.db"))
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",") if o.strip()]

MAX_REQUEST_BYTES = _env_int("MAX_REQUEST_MB", 8) * 1024 * 1024
MAX_TEXT_CHARS = _env_int("MAX_INGREDIENT_TEXT_CHARS", 5000)
MAX_IMAGE_PIXELS = _env_int("MAX_IMAGE_PIXELS", 25_000_000)
OCR_MAX_SIDE = _env_int("OCR_MAX_SIDE", 2500)
OCR_TIMEOUT_SECONDS = _env_int("OCR_TIMEOUT_SECONDS", 30)
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[^@\s]+\.[^@\s]{2,}$")
MIN_PASSWORD_LEN = 8
MAX_PASSWORD_BYTES = 72          # bcrypt limit
MAX_NAME_LEN = 150
# Used to make login take the same time whether or not the email exists.
_DUMMY_HASH = bcrypt.hashpw(secrets.token_bytes(16), bcrypt.gensalt())


def configure_tesseract():
    """TESSERACT_CMD env var -> PATH -> common Windows install locations."""
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
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_BYTES
app.json.sort_keys = False
if os.getenv("TRUST_PROXY", "0") == "1":
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

CORS(app, resources={r"/api/*": {"origins": CORS_ORIGINS}},
     allow_headers=["Content-Type", "Authorization"], methods=["GET", "POST", "PUT", "OPTIONS"])

limiter = Limiter(
    get_remote_address,
    app=app,
    storage_uri=os.getenv("RATELIMIT_STORAGE_URI", "memory://"),
    default_limits=[os.getenv("DEFAULT_RATE_LIMIT", "300 per minute")],
    headers_enabled=True,
    enabled=os.getenv("RATELIMIT_ENABLED", "1") == "1",
)
LOGIN_LIMIT = os.getenv("LOGIN_RATE_LIMIT", "5 per minute")
LOGIN_IP_LIMIT = os.getenv("LOGIN_IP_RATE_LIMIT", "30 per minute")
REGISTER_LIMIT = os.getenv("REGISTER_RATE_LIMIT", "10 per hour")
ANALYZE_LIMIT = os.getenv("ANALYZE_RATE_LIMIT", "60 per minute")
OCR_LIMIT = os.getenv("OCR_RATE_LIMIT", "10 per minute")


def _login_key():
    data = request.get_json(silent=True)
    email = data.get("email") if isinstance(data, dict) else None
    return f"{get_remote_address()}|{str(email).strip().lower()}"


class ApiError(Exception):
    def __init__(self, message, status=400):
        super().__init__(message)
        self.message, self.status = message, status


@app.errorhandler(ApiError)
def handle_api_error(err):
    return jsonify({"error": err.message}), err.status


@app.errorhandler(HTTPException)
def handle_http_error(err):
    messages = {413: "Request too large", 429: "Too many requests, please slow down"}
    return jsonify({"error": messages.get(err.code, err.name)}), err.code


@app.errorhandler(Exception)
def handle_unexpected(err):
    error_id = uuid.uuid4().hex[:12]
    log.exception("Unhandled error id=%s path=%s", error_id, request.path)
    return jsonify({"error": "Internal server error", "error_id": error_id}), 500


@app.after_request
def security_headers(resp):
    resp.headers["X-Content-Type-Options"] = "nosniff"
    resp.headers["X-Frame-Options"] = "DENY"
    resp.headers["Referrer-Policy"] = "no-referrer"
    resp.headers["Content-Security-Policy"] = "default-src 'none'; frame-ancestors 'none'"
    resp.headers["Cache-Control"] = "no-store"
    if request.is_secure:
        resp.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return resp


# ─────────────────────────────────────────
# DB helpers
# ─────────────────────────────────────────
def _connect():
    conn = sqlite3.connect(DATABASE_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 15000")
    return conn


def init_db():
    """Create tables and seed reference data. Safe to run on every start."""
    os.makedirs(os.path.dirname(os.path.abspath(DATABASE_PATH)), exist_ok=True)
    conn = _connect()
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        with open(os.path.join(BASE_DIR, "schema.sql"), encoding="utf-8") as f:
            conn.executescript(f.read())
        seed_data.apply(conn)
        conn.execute("DELETE FROM revoked_tokens WHERE expires_at < ?", (int(time.time()),))
        conn.commit()
    finally:
        conn.close()


def get_db():
    if "db" not in g:
        g.db = _connect()
    return g.db


@app.teardown_appcontext
def close_db(_):
    db = g.pop("db", None)
    if db:
        db.close()


def query(sql, args=(), one=False):
    rows = [dict(r) for r in get_db().execute(sql, args).fetchall()]
    return (rows[0] if rows else None) if one else rows


def execute(sql, args=(), commit=True):
    db = get_db()
    cur = db.execute(sql, args)
    if commit:
        db.commit()
    return cur.lastrowid


# Cached matcher; rebuilt when the reference data changes.
_index_lock = threading.Lock()
_index_cache = {"sig": None, "index": None}


def get_ingredient_index() -> IngredientIndex:
    sig = tuple(get_db().execute(
        "SELECT (SELECT COUNT(*) FROM ingredients), (SELECT MAX(id) FROM ingredients), "
        "(SELECT COUNT(*) FROM ingredient_aliases), (SELECT COUNT(*) FROM ingredient_allergens)").fetchone())
    with _index_lock:
        if _index_cache["sig"] != sig:
            rows = query("SELECT * FROM ingredients")
            aliases = [(r["alias"], r["ingredient_id"]) for r in query("SELECT alias, ingredient_id FROM ingredient_aliases")]
            allergens: dict[int, set[str]] = {}
            for r in query("SELECT ia.ingredient_id, a.name FROM ingredient_allergens ia "
                           "JOIN allergens a ON a.id = ia.allergen_id"):
                allergens.setdefault(r["ingredient_id"], set()).add(r["name"])
            _index_cache.update(sig=sig, index=IngredientIndex(rows, aliases, allergens))
        return _index_cache["index"]


# ─────────────────────────────────────────
# Input validation helpers
# ─────────────────────────────────────────
def json_body() -> dict:
    data = request.get_json(silent=True)
    if data is None:
        data = {}
        if request.data and not request.form:
            raise ApiError("Request body must be valid JSON")
    if not isinstance(data, dict):
        raise ApiError("Request body must be a JSON object")
    return data


def str_field(data, key, required=False, max_len=None, default=""):
    value = data.get(key, default)
    if value is None:
        value = default
    if not isinstance(value, str):
        raise ApiError(f"'{key}' must be a string")
    value = value.strip()
    if required and not value:
        raise ApiError(f"'{key}' is required")
    if max_len and len(value) > max_len:
        raise ApiError(f"'{key}' is too long (max {max_len} characters)")
    return value


def validate_age_group(value, default=None):
    if value in (None, ""):
        return default
    if value not in AGE_GROUPS:
        raise ApiError(f"age_group must be one of: {', '.join(sorted(AGE_GROUPS))}")
    return value


def validate_restrictions(value):
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(r, str) for r in value):
        raise ApiError("restrictions must be a list of strings")
    cleaned = sorted({r.strip().lower() for r in value if r.strip()})
    unknown = [r for r in cleaned if r not in ALLOWED_RESTRICTIONS]
    if unknown:
        raise ApiError(f"Unknown restrictions: {', '.join(unknown)}")
    return cleaned


def validate_product_id(value):
    if value in (None, ""):
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ApiError("product_id must be an integer")
    if not query("SELECT id FROM products WHERE id=?", (value,), one=True):
        raise ApiError("Product not found", 404)
    return value


# ─────────────────────────────────────────
# JWT auth
# ─────────────────────────────────────────
def generate_token(user_id: int, email: str) -> str:
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": str(user_id),
        "email": email,
        "iat": now,
        "nbf": now,
        "exp": now + datetime.timedelta(hours=TOKEN_EXPIRY_HOURS),
        "iss": JWT_ISSUER,
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def require_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        header = request.headers.get("Authorization", "")
        if not header.startswith("Bearer ") or not header[7:].strip():
            return jsonify({"error": "Missing token"}), 401
        try:
            payload = jwt.decode(
                header[7:].strip(), SECRET_KEY, algorithms=[JWT_ALGORITHM], issuer=JWT_ISSUER,
                options={"require": ["exp", "iat", "sub", "jti", "iss"]},
            )
            user_id = int(payload["sub"])
        except jwt.ExpiredSignatureError:
            return jsonify({"error": "Token expired"}), 401
        except (jwt.InvalidTokenError, ValueError, TypeError):
            return jsonify({"error": "Invalid token"}), 401
        if query("SELECT 1 FROM revoked_tokens WHERE jti=?", (payload["jti"],), one=True):
            return jsonify({"error": "Token revoked"}), 401
        if not query("SELECT 1 FROM users WHERE id=?", (user_id,), one=True):
            return jsonify({"error": "Invalid token"}), 401
        g.current_user_id = user_id
        g.token_payload = payload
        return f(*args, **kwargs)
    return decorated


# ─────────────────────────────────────────
# OCR helper
# ─────────────────────────────────────────
def load_image_bytes(data: dict) -> bytes:
    if "image" in request.files:
        return request.files["image"].read()
    b64 = data.get("image_base64")
    if not isinstance(b64, str) or not b64.strip():
        raise ApiError("No image provided")
    if b64.startswith("data:"):
        b64 = b64.split(",", 1)[-1]
    try:
        return base64.b64decode(b64.strip(), validate=True)
    except (binascii.Error, ValueError):
        raise ApiError("image_base64 is not valid base64")


def extract_text_from_image(image_bytes: bytes) -> str:
    if not TESSERACT_PATH:
        raise ApiError("OCR is not available on this server", 503)
    try:
        img = Image.open(io.BytesIO(image_bytes))
        if img.width * img.height > MAX_IMAGE_PIXELS:
            raise ApiError("Image resolution too large", 413)
        img.load()
    except Image.DecompressionBombError:
        raise ApiError("Image resolution too large", 413)
    except (UnidentifiedImageError, OSError, SyntaxError):
        raise ApiError("File is not a supported image", 400)
    img = img.convert("L")
    if max(img.size) > OCR_MAX_SIDE:
        img.thumbnail((OCR_MAX_SIDE, OCR_MAX_SIDE))
    try:
        return pytesseract.image_to_string(img, config="--psm 6", timeout=OCR_TIMEOUT_SECONDS)
    except RuntimeError:                       # pytesseract raises RuntimeError on timeout
        raise ApiError("OCR timed out, try a smaller or clearer image", 422)
    except pytesseract.TesseractError:
        log.exception("Tesseract failed")
        raise ApiError("Could not read text from image", 422)


# ─────────────────────────────────────────
# Routes – Auth
# ─────────────────────────────────────────
@app.route("/api/auth/register", methods=["POST"])
@limiter.limit(REGISTER_LIMIT)
def register():
    data = json_body()
    email = str_field(data, "email", required=True, max_len=255).lower()
    password = data.get("password")
    full_name = str_field(data, "full_name", max_len=MAX_NAME_LEN)

    if not EMAIL_RE.match(email):
        raise ApiError("Please enter a valid email address")
    if not isinstance(password, str) or len(password) < MIN_PASSWORD_LEN:
        raise ApiError(f"Password must be at least {MIN_PASSWORD_LEN} characters")
    if len(password.encode()) > MAX_PASSWORD_BYTES:
        raise ApiError(f"Password must be at most {MAX_PASSWORD_BYTES} bytes")

    if query("SELECT id FROM users WHERE email=?", (email,), one=True):
        return jsonify({"error": "Email already registered"}), 409

    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    try:
        user_id = execute("INSERT INTO users (email, password_hash, full_name) VALUES (?,?,?)",
                          (email, pw_hash, full_name))
    except sqlite3.IntegrityError:
        return jsonify({"error": "Email already registered"}), 409
    return jsonify({"token": generate_token(user_id, email), "user_id": user_id, "email": email}), 201


@app.route("/api/auth/login", methods=["POST"])
@limiter.limit(LOGIN_IP_LIMIT)
@limiter.limit(LOGIN_LIMIT, key_func=_login_key)
def login():
    data = json_body()
    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str):
        return jsonify({"error": "Invalid credentials"}), 401
    pw = password.encode()[:MAX_PASSWORD_BYTES]

    user = query("SELECT * FROM users WHERE email=?", (email.strip().lower(),), one=True)
    stored = user["password_hash"].encode() if user else _DUMMY_HASH
    ok = bcrypt.checkpw(pw, stored)            # always run bcrypt -> no timing oracle
    if not user or not ok:
        return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({"token": generate_token(user["id"], user["email"]),
                    "user_id": user["id"], "email": user["email"]}), 200


@app.route("/api/auth/logout", methods=["POST"])
@require_auth
def logout():
    execute("INSERT OR IGNORE INTO revoked_tokens (jti, expires_at) VALUES (?,?)",
            (g.token_payload["jti"], int(g.token_payload["exp"])))
    return jsonify({"message": "Logged out"})


# ─────────────────────────────────────────
# Routes – User Profile
# ─────────────────────────────────────────
@app.route("/api/user/profile", methods=["GET"])
@require_auth
def get_profile():
    user = query("SELECT id, email, full_name, age_group, created_at FROM users WHERE id=?",
                 (g.current_user_id,), one=True)
    user["restrictions"] = [r["restriction"] for r in
                            query("SELECT restriction FROM user_restrictions WHERE user_id=? ORDER BY restriction",
                                  (g.current_user_id,))]
    return jsonify(user)


@app.route("/api/user/profile", methods=["PUT"])
@require_auth
def update_profile():
    """Partial update: only fields present in the body are changed."""
    data = json_body()
    updates = {}
    if "full_name" in data:
        updates["full_name"] = str_field(data, "full_name", max_len=MAX_NAME_LEN)
    if "age_group" in data:
        updates["age_group"] = validate_age_group(data["age_group"], default="adult")
    restrictions = validate_restrictions(data["restrictions"]) if "restrictions" in data else None

    db = get_db()
    with db:  # single transaction
        if updates:
            cols = ", ".join(f"{k}=?" for k in updates)
            db.execute(f"UPDATE users SET {cols}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                       (*updates.values(), g.current_user_id))
        if restrictions is not None:
            db.execute("DELETE FROM user_restrictions WHERE user_id=?", (g.current_user_id,))
            db.executemany("INSERT OR IGNORE INTO user_restrictions (user_id, restriction) VALUES (?,?)",
                           [(g.current_user_id, r) for r in restrictions])
    return jsonify({"message": "Profile updated"})


# ─────────────────────────────────────────
# Routes – Products
# ─────────────────────────────────────────
@app.route("/api/products", methods=["GET"])
def list_products():
    category = request.args.get("category")
    if category:
        return jsonify(query("SELECT * FROM products WHERE category=? ORDER BY name", (category,)))
    return jsonify(query("SELECT * FROM products ORDER BY category, name"))


@app.route("/api/products/<int:product_id>", methods=["GET"])
def get_product(product_id):
    product = query("SELECT * FROM products WHERE id=?", (product_id,), one=True)
    if not product:
        return jsonify({"error": "Not found"}), 404
    return jsonify(product)


@app.route("/api/products/barcode/<barcode>", methods=["GET"])
def get_by_barcode(barcode):
    product = query("SELECT * FROM products WHERE barcode=?", (barcode[:64],), one=True)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    return jsonify(product)


# ─────────────────────────────────────────
# Routes – Analysis
# ─────────────────────────────────────────
def _user_context(data: dict, form_age=None):
    """Resolve age group (request -> profile -> adult) and restrictions (profile + request)."""
    user = query("SELECT age_group FROM users WHERE id=?", (g.current_user_id,), one=True)
    profile_age = user["age_group"] if user and user["age_group"] in AGE_GROUPS else "adult"
    age_group = validate_age_group(form_age or data.get("age_group"), default=profile_age)

    profile_restrictions = [r["restriction"] for r in
                            query("SELECT restriction FROM user_restrictions WHERE user_id=?", (g.current_user_id,))]
    req_restrictions = data.get("restrictions")
    if req_restrictions is None and request.form.get("restrictions"):
        try:
            req_restrictions = json.loads(request.form["restrictions"])
        except ValueError:
            raise ApiError("restrictions must be a JSON list")
    restrictions = sorted(set(profile_restrictions) | set(validate_restrictions(req_restrictions)))
    return age_group, restrictions


def _run_analysis(ingredients, age_group, restrictions, product_id, scan_type, raw_text):
    result = analyze_ingredients(ingredients, age_group, restrictions, get_ingredient_index())
    db = get_db()
    with db:
        analysis_id = db.execute(
            "INSERT INTO product_analysis (product_id, user_id, safety_score, status, age_group, detected_flags) "
            "VALUES (?,?,?,?,?,?)",
            (product_id, g.current_user_id, result["safety_score"], result["status"], age_group,
             json.dumps([f["id"] for f in result["flagged"]])),
        ).lastrowid
        db.execute(
            "INSERT INTO scan_history (user_id, product_id, scan_type, ocr_raw_text, result_id) VALUES (?,?,?,?,?)",
            (g.current_user_id, product_id, scan_type, raw_text, analysis_id),
        )
    result["analysis_id"] = analysis_id
    result["alternatives"] = (query("SELECT * FROM alternatives WHERE product_id=?", (product_id,))
                              if product_id and result["status"] in ("unsafe", "moderate") else [])
    return result


@app.route("/api/analyze/text", methods=["POST"])
@require_auth
@limiter.limit(ANALYZE_LIMIT)
def analyze_text():
    data = json_body()
    raw_text = str_field(data, "ingredients_text", required=True, max_len=MAX_TEXT_CHARS)
    product_id = validate_product_id(data.get("product_id"))
    age_group, restrictions = _user_context(data)

    ingredients = parse_ingredients(raw_text)
    if not ingredients:
        return jsonify({"error": "No ingredients found in provided text"}), 422
    return jsonify(_run_analysis(ingredients, age_group, restrictions, product_id, "manual", raw_text))


@app.route("/api/analyze/image", methods=["POST"])
@require_auth
@limiter.limit(OCR_LIMIT)
def analyze_image():
    """Upload image (multipart 'image' or JSON 'image_base64') -> OCR -> analyze."""
    data = request.get_json(silent=True)
    data = data if isinstance(data, dict) else {}
    image_bytes = load_image_bytes(data)
    age_group, restrictions = _user_context(data, form_age=request.form.get("age_group"))

    ocr_text = extract_text_from_image(image_bytes)
    ingredients = parse_ingredients(ocr_text)
    if not ingredients:
        return jsonify({"error": "No ingredients found in image", "ocr_text": ocr_text}), 422

    result = _run_analysis(ingredients, age_group, restrictions, None, "image", ocr_text[:MAX_TEXT_CHARS])
    result["ocr_text"] = ocr_text
    return jsonify(result)


@app.route("/api/analyze/product/<int:product_id>", methods=["POST"])
@require_auth
@limiter.limit(ANALYZE_LIMIT)
def analyze_product(product_id):
    product = query("SELECT * FROM products WHERE id=?", (product_id,), one=True)
    if not product:
        return jsonify({"error": "Product not found"}), 404
    data = json_body()
    age_group, restrictions = _user_context(data)

    ingredients = parse_ingredients(product["raw_ingredients"] or "")
    result = _run_analysis(ingredients, age_group, restrictions, product_id, "product", None)
    result["product"] = product
    if result["status"] in ("unsafe", "moderate"):
        result["alternatives"] = query("SELECT * FROM alternatives WHERE product_id=?", (product_id,))
    return jsonify(result)


# ─────────────────────────────────────────
# Routes – History / reference
# ─────────────────────────────────────────
@app.route("/api/history", methods=["GET"])
@require_auth
def get_history():
    return jsonify(query(
        """SELECT sh.id, sh.scan_type, sh.scanned_at,
                  p.name AS product_name, p.category,
                  pa.safety_score, pa.status
           FROM scan_history sh
           LEFT JOIN products p          ON sh.product_id = p.id
           LEFT JOIN product_analysis pa ON sh.result_id  = pa.id
           WHERE sh.user_id = ?
           ORDER BY sh.scanned_at DESC, sh.id DESC
           LIMIT 50""",
        (g.current_user_id,)))


@app.route("/api/ingredients", methods=["GET"])
def list_ingredients():
    risk = request.args.get("risk")
    if risk:
        return jsonify(query("SELECT * FROM ingredients WHERE risk_level=? ORDER BY name", (risk,)))
    return jsonify(query("SELECT * FROM ingredients ORDER BY risk_level DESC, name"))


@app.route("/api/restrictions", methods=["GET"])
def list_restrictions():
    return jsonify(sorted(ALLOWED_RESTRICTIONS))


# ─────────────────────────────────────────
# Health checks
# ─────────────────────────────────────────
@app.route("/api/health")
@limiter.exempt
def health():
    """Liveness: process is up."""
    return jsonify({"status": "ok", "version": "1.1.0"})


@app.route("/api/ready")
@limiter.exempt
def ready():
    """Readiness: DB reachable and OCR binary present."""
    try:
        get_db().execute("SELECT 1").fetchone()
        db_ok = True
    except sqlite3.Error:
        log.exception("Readiness DB check failed")
        db_ok = False
    ok = db_ok and bool(TESSERACT_PATH)
    return jsonify({"status": "ready" if ok else "degraded", "database": db_ok,
                    "ocr": bool(TESSERACT_PATH)}), (200 if ok else 503)


init_db()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1", host="127.0.0.1", port=_env_int("PORT", 5000))
