"""
SafeBite AI - regression suite (logic + API + security).

Run from backend/:  python -m pytest -q
Each test documents a defect found in the October 2026 audit and guards against regressions.
"""
import base64
import hashlib
import hmac
import io
import json
import os
import sqlite3
import time

import pytest

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(BACKEND)
APP_SRC = open(os.path.join(BACKEND, "app.py"), encoding="utf-8").read()


# ───────────────────────── helpers ─────────────────────────
_counter = [0]


def new_user(client, restrictions=None, age_group=None):
    _counter[0] += 1
    email = f"user{_counter[0]}@test.com"
    r = client.post("/api/auth/register", json={"email": email, "password": "Passw0rd!x", "full_name": "T"})
    assert r.status_code == 201, r.data
    h = {"Authorization": f"Bearer {r.get_json()['token']}"}
    body = {}
    if restrictions is not None:
        body["restrictions"] = restrictions
    if age_group:
        body["age_group"] = age_group
    if body:
        assert client.put("/api/user/profile", headers=h, json=body).status_code == 200
    return h, r.get_json()["user_id"]


def analyze(client, h, text, **kw):
    r = client.post("/api/analyze/text", headers=h, json={"ingredients_text": text, **kw})
    assert r.status_code == 200, r.data
    return r.get_json()


def b64(d):
    return base64.urlsafe_b64encode(d).rstrip(b"=").decode()


def forge(payload, secret):
    h = b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode())
    p = b64(json.dumps(payload).encode())
    s = b64(hmac.new(secret.encode(), f"{h}.{p}".encode(), hashlib.sha256).digest())
    return f"{h}.{p}.{s}"


def flagged_names(r):
    return {f["name"] for f in r["flagged"]}


def text_image(text, size=(1400, 200)):
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("L", size, 255)
    ImageDraw.Draw(img).text((20, 60), text, fill=0, font=ImageFont.load_default(size=48))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()


# ═════════════════════ 1. SETUP / DEPLOYABILITY ═════════════════════
class TestSetup:
    def test_fresh_database_is_initialised(self, appmod, client):
        assert os.path.exists(appmod.DATABASE_PATH)
        assert len(client.get("/api/products").get_json()) == 8

    def test_schema_is_rerunnable(self, appmod):
        appmod.init_db()
        appmod.init_db()

    def test_requirements_match_code(self):
        req = open(os.path.join(BACKEND, "requirements.txt")).read().lower()
        assert "pymysql" not in req and "gunicorn" in req and "pyjwt" in req

    def test_no_secrets_or_binaries_committed(self):
        assert not os.path.exists(os.path.join(BACKEND, "update_images.py"))
        assert not os.path.exists(os.path.join(BACKEND, "jwt.py")), "local jwt.py shadows PyJWT"
        for v in (".venv_clean", ".venv_fix"):
            assert not os.path.isdir(os.path.join(BACKEND, v))

    def test_debug_mode_off(self):
        assert "debug=True" not in APP_SRC

    def test_missing_secret_refuses_to_start(self):
        import subprocess, sys
        env = {k: v for k, v in os.environ.items() if k != "JWT_SECRET"}
        env["JWT_SECRET"] = "short"
        p = subprocess.run([sys.executable, "-c", "import app"], cwd=BACKEND, env=env,
                           capture_output=True, text=True)
        assert p.returncode != 0 and "JWT_SECRET" in p.stderr

    def test_seeded_products_have_images(self, client):
        prods = client.get("/api/products").get_json()
        assert all(p["image_url"] for p in prods)


# ═════════════════════ 2. HAPPY PATH ═════════════════════
class TestHappyPath:
    def test_health_and_ready(self, client):
        assert client.get("/api/health").get_json()["status"] == "ok"
        assert client.get("/api/ready").status_code in (200, 503)

    def test_register_login_profile(self, client):
        h, uid = new_user(client)
        r = client.get("/api/user/profile", headers=h)
        assert r.status_code == 200 and r.get_json()["id"] == uid

    def test_products_analyze(self, client):
        h, _ = new_user(client)
        prods = {p["name"]: p for p in client.get("/api/products").get_json()}
        def status(name):
            r = client.post(f"/api/analyze/product/{prods[name]['id']}", headers=h, json={})
            assert r.status_code == 200
            return r.get_json()["status"]
        assert status("Pure Bloom Kombucha") == "safe"
        assert status("Rainbow Fruit Candy") == "unsafe"
        assert status("Instant Ramen") == "unsafe"

    def test_history_is_per_user(self, client):
        h1, _ = new_user(client)
        h2, _ = new_user(client)
        analyze(client, h1, "tbhq, salt")
        assert client.get("/api/history", headers=h2).get_json() == []
        assert len(client.get("/api/history", headers=h1).get_json()) == 1

    def test_product_scan_type(self, client, appmod):
        h, uid = new_user(client)
        client.post("/api/analyze/product/1", headers=h, json={})
        assert client.get("/api/history", headers=h).get_json()[0]["scan_type"] == "product"

    def test_sql_injection_params(self, client):
        for p in ["/api/products?category=' OR 1=1--", "/api/products/barcode/x' OR '1'='1",
                  "/api/ingredients?risk=high' OR 1=1--"]:
            r = client.get(p)
            assert r.status_code in (200, 404)
            assert r.get_json() in ([], {"error": "Product not found"})

    def test_restrictions_endpoint(self, client):
        rs = client.get("/api/restrictions").get_json()
        assert {"nut_allergy", "vegan", "egg_allergy"} <= set(rs)


# ═════════════════════ 3. SAFETY-ENGINE LOGIC ═════════════════════
class TestEngineLogic:
    def test_nut_allergy_flags_peanut(self, client):
        h, _ = new_user(client, ["nut_allergy"])
        r = analyze(client, h, "peanuts, sugar, salt")
        assert r["status"] == "unsafe" and r["allergen_alerts"][0]["allergen"] == "peanut"

    def test_nut_allergy_flags_tree_nuts(self, client):
        h, _ = new_user(client, ["nut_allergy"])
        r = analyze(client, h, "sugar, cashews, almond flour")
        assert {a["ingredient"] for a in r["allergen_alerts"]} == {"cashew", "almond"}

    def test_lactose_flags_milk_derivatives(self, client):
        h, _ = new_user(client, ["lactose_intolerant"])
        r = analyze(client, h, "sugar, whey powder, skimmed milk powder, butter")
        assert {"whey", "milk"} <= flagged_names(r) and r["status"] == "unsafe"

    def test_gluten_flags_wheat_variants(self, client):
        h, _ = new_user(client, ["gluten_intolerant"])
        for text in ("wheat flour, sugar", "maida, salt", "barley malt extract", "semolina"):
            assert analyze(client, h, text)["status"] == "unsafe", text

    def test_allergen_ignored_for_users_without_restriction(self, client):
        h, _ = new_user(client)
        r = analyze(client, h, "peanuts, sugar")
        assert r["status"] == "safe" and r["allergen_alerts"] == []

    def test_may_contain_traces(self, client):
        h, _ = new_user(client, ["nut_allergy"])
        r = analyze(client, h, "sugar, cocoa. may contain traces of peanuts")
        assert r["status"] == "unsafe" and r["allergen_alerts"][0]["trace"] is True

    def test_request_restrictions_merged(self, client):
        h, _ = new_user(client)
        r = analyze(client, h, "egg, sugar", restrictions=["egg_allergy"])
        assert r["status"] == "unsafe"

    def test_vegan_flags_animal_products(self, client):
        h, _ = new_user(client, ["vegan"])
        r = analyze(client, h, "milk, egg, gelatin, honey")
        assert len(r["diet_conflicts"]) == 4 and r["status"] == "unsafe"

    def test_vegetarian_allows_dairy(self, client):
        h, _ = new_user(client, ["vegetarian"])
        r = analyze(client, h, "milk, sugar, gelatine")
        assert [d["ingredient"] for d in r["diet_conflicts"]] == ["gelatin"]

    def test_palm_oil_is_vegan(self, client):
        h, _ = new_user(client, ["vegan"])
        r = analyze(client, h, "palm oil")
        assert r["diet_conflicts"] == []

    def test_plant_lookalikes_not_dairy(self, client):
        h, _ = new_user(client, ["lactose_intolerant", "nut_allergy"])
        r = analyze(client, h, "cocoa butter, coconut milk, cream of tartar, nutmeg")
        assert r["allergen_alerts"] == [], r["allergen_alerts"]

    def test_additives_inside_parentheses_detected(self, client):
        h, _ = new_user(client)
        r = analyze(client, h, "potatoes, seasoning (msg, tartrazine, tbhq)")
        assert {"msg", "tartrazine", "tbhq"} <= flagged_names(r)

    def test_e_numbers_and_ins_codes(self, client):
        h, _ = new_user(client)
        r = analyze(client, h, "water, e102, E-211, INS 319, colour (110)")
        assert {"tartrazine", "sodium benzoate", "tbhq", "sunset yellow"} <= flagged_names(r)

    def test_indian_label_terms(self, client):
        h, _ = new_user(client)
        r = analyze(client, h, "refined wheat flour (maida), edible vegetable oil (palmolein), vanaspati")
        assert {"palm oil", "hydrogenated oil"} <= flagged_names(r)

    def test_padding_with_water_does_not_hide_risk(self, client):
        h, _ = new_user(client)
        r = analyze(client, h, "tbhq, bha, bht, sodium nitrite, " + ", ".join(["water"] * 30))
        assert r["status"] == "unsafe"

    def test_score_independent_of_list_length(self, client):
        h, _ = new_user(client)
        a = analyze(client, h, "tartrazine, salt")["safety_score"]
        b = analyze(client, h, "tartrazine, salt, water, rice, sugar, pepper, onion, garlic")["safety_score"]
        assert a == b

    def test_duplicates_counted_once(self, client):
        h, _ = new_user(client)
        a = analyze(client, h, "tbhq")["safety_score"]
        b = analyze(client, h, "tbhq, tbhq, TBHQ, e319")["safety_score"]
        assert a == b

    def test_generic_oil_not_flagged_as_palm(self, client):
        h, _ = new_user(client)
        assert analyze(client, h, "olive oil, oil")["flagged"] == []

    def test_single_letter_token_no_false_match(self, client):
        h, _ = new_user(client)
        r = analyze(client, h, "a, b, re, salt")
        assert r["matched_count"] == 0 and r["flagged"] == []

    def test_negations(self, client):
        h, _ = new_user(client, ["gluten_intolerant"])
        r = analyze(client, h, "non-hydrogenated oil, msg free seasoning, gluten-free oats, free from tartrazine")
        assert r["flagged"] == [], r["flagged"]

    def test_partially_hydrogenated_matches_specific_row(self, client):
        h, _ = new_user(client)
        r = analyze(client, h, "partially hydrogenated oil")
        assert r["ingredient_details"][0]["matched"] == "partially hydrogenated oil"

    def test_unicode_label(self, client):
        h, _ = new_user(client, ["lactose_intolerant"])
        r = analyze(client, h, "Crème fraîche, Lait (milk), sucre")
        assert r["status"] == "unsafe"

    def test_profile_age_group_used_when_not_sent(self, client):
        h, _ = new_user(client, [], age_group="child")
        assert analyze(client, h, "tartrazine")["safety_score"] == \
            analyze(client, h, "tartrazine", age_group="child")["safety_score"]
        assert analyze(client, h, "tartrazine")["age_group"] == "child"

    def test_child_scored_stricter_than_adult(self, client):
        h, _ = new_user(client)
        assert analyze(client, h, "tartrazine", age_group="child")["safety_score"] < \
            analyze(client, h, "tartrazine", age_group="adult")["safety_score"]

    def test_invalid_age_group_rejected(self, client):
        h, _ = new_user(client)
        assert client.put("/api/user/profile", headers=h, json={"age_group": "toddler"}).status_code == 400
        assert client.post("/api/analyze/text", headers=h,
                           json={"ingredients_text": "salt", "age_group": "toddler"}).status_code == 400

    def test_restrictions_validated(self, client):
        h, _ = new_user(client)
        assert client.put("/api/user/profile", headers=h, json={"restrictions": "vegan"}).status_code == 400
        assert client.put("/api/user/profile", headers=h, json={"restrictions": ["telepathy"]}).status_code == 400
        assert client.get("/api/user/profile", headers=h).get_json()["restrictions"] == []

    def test_product_id_validated(self, client):
        h, _ = new_user(client)
        r = client.post("/api/analyze/text", headers=h, json={"ingredients_text": "salt", "product_id": 999999})
        assert r.status_code == 404

    def test_profile_update_partial(self, client):
        h, _ = new_user(client)
        client.put("/api/user/profile", headers=h, json={"restrictions": ["vegan"]})
        p = client.get("/api/user/profile", headers=h).get_json()
        assert p["full_name"] == "T" and p["restrictions"] == ["vegan"]


# ═════════════════════ 4. OCR ═════════════════════
@pytest.fixture
def needs_ocr(appmod):
    if not appmod.TESSERACT_PATH:
        pytest.skip("tesseract not installed")


class TestOcr:
    def test_multipart_upload_with_restrictions(self, client, needs_ocr):
        h, _ = new_user(client)
        data = {"image": (io.BytesIO(text_image("Ingredients: sugar, peanuts, salt")), "label.png"),
                "age_group": "adult", "restrictions": json.dumps(["nut_allergy"])}
        r = client.post("/api/analyze/image", headers=h, data=data, content_type="multipart/form-data")
        assert r.status_code == 200, r.data
        assert r.get_json()["status"] == "unsafe"

    def test_base64_upload(self, client, needs_ocr):
        h, _ = new_user(client)
        img = base64.b64encode(text_image("Ingredients: water, tartrazine")).decode()
        r = client.post("/api/analyze/image", headers=h, json={"image_base64": "data:image/png;base64," + img})
        assert r.status_code == 200 and "tartrazine" in flagged_names(r.get_json())

    def test_non_image_rejected(self, client, needs_ocr):
        h, _ = new_user(client)
        r = client.post("/api/analyze/image", headers=h,
                        json={"image_base64": base64.b64encode(b"not an image").decode()})
        assert r.status_code == 400 and "not a supported image" in r.get_json()["error"]


# ═════════════════════ 5. INPUT ROBUSTNESS ═════════════════════
class TestRobustness:
    @pytest.mark.parametrize("body", [None, [], "x", 123])
    def test_register_bad_body_no_500(self, client, body):
        if body is None:
            r = client.post("/api/auth/register", data="notjson", content_type="text/plain")
        else:
            r = client.post("/api/auth/register", json=body)
        assert r.status_code == 400

    def test_login_non_string_email_no_500(self, client):
        assert client.post("/api/auth/login", json={"email": 1, "password": "x"}).status_code == 401

    def test_analyze_text_null_text(self, client):
        h, _ = new_user(client)
        assert client.post("/api/analyze/text", headers=h, json={"ingredients_text": None}).status_code == 400

    def test_invalid_base64_image(self, client):
        h, _ = new_user(client)
        assert client.post("/api/analyze/image", headers=h, json={"image_base64": "abc"}).status_code == 400

    def test_deleted_user_token(self, client, appmod):
        tok = appmod.generate_token(987654, "ghost@x.com")
        assert client.get("/api/user/profile", headers={"Authorization": f"Bearer {tok}"}).status_code == 401

    def test_non_ascii_token(self, client):
        good = forge({"sub": "1", "exp": int(time.time()) + 60}, "wrong")
        h, p, _ = good.split(".")
        r = client.get("/api/user/profile", headers={"Authorization": f"Bearer {h}.{p}.é"})
        assert r.status_code == 401

    def test_token_without_sub(self, client, appmod):
        now = int(time.time())
        tok = forge({"exp": now + 60, "iat": now, "jti": "x", "iss": appmod.JWT_ISSUER}, appmod.SECRET_KEY)
        assert client.get("/api/user/profile", headers={"Authorization": f"Bearer {tok}"}).status_code == 401

    def test_long_password(self, client):
        r = client.post("/api/auth/register", json={"email": "longpw@x.com", "password": "A" * 100})
        assert r.status_code == 400

    def test_unknown_route_json_404(self, client):
        r = client.get("/api/nope")
        assert r.status_code == 404 and r.is_json


# ═════════════════════ 6. SECURITY ═════════════════════
class TestSecurity:
    def test_old_default_secret_rejected(self, client):
        h, uid = new_user(client)
        now = int(time.time())
        tok = forge({"sub": str(uid), "user_id": uid, "exp": now + 3600, "iat": now},
                    "safebite-dev-secret-change-in-prod")
        assert client.get("/api/user/profile", headers={"Authorization": f"Bearer {tok}"}).status_code == 401

    def test_token_without_exp_rejected(self, client, appmod):
        h, uid = new_user(client)
        tok = forge({"sub": str(uid), "iat": int(time.time()), "jti": "x", "iss": appmod.JWT_ISSUER},
                    appmod.SECRET_KEY)
        assert client.get("/api/user/profile", headers={"Authorization": f"Bearer {tok}"}).status_code == 401

    def test_alg_none_rejected(self, client):
        h = b64(json.dumps({"alg": "none"}).encode())
        p = b64(json.dumps({"sub": "1"}).encode())
        assert client.get("/api/user/profile", headers={"Authorization": f"Bearer {h}.{p}."}).status_code == 401

    def test_logout_revokes_token(self, client):
        h, _ = new_user(client)
        assert client.post("/api/auth/logout", headers=h).status_code == 200
        assert client.get("/api/user/profile", headers=h).status_code == 401

    def test_login_rate_limited(self, client, appmod):
        appmod.limiter.reset()
        client.post("/api/auth/register", json={"email": "victim@x.com", "password": "Secret123!"})
        codes = [client.post("/api/auth/login", json={"email": "victim@x.com", "password": f"g{i}"}).status_code
                 for i in range(10)]
        assert 429 in codes
        appmod.limiter.reset()

    def test_password_policy(self, client):
        assert client.post("/api/auth/register", json={"email": "not-an-email", "password": "Secret123!"}).status_code == 400
        assert client.post("/api/auth/register", json={"email": "ok@x.com", "password": "1"}).status_code == 400

    def test_user_enumeration_timing(self, client, appmod):
        appmod.limiter.reset()
        client.post("/api/auth/register", json={"email": "known@x.com", "password": "Secret123!"})

        def t(email):
            s = time.perf_counter()
            for _ in range(4):
                assert client.post("/api/auth/login", json={"email": email, "password": "wrong"}).status_code == 401
            return (time.perf_counter() - s) / 4
        known, unknown = t("known@x.com"), t("nobody@x.com")
        appmod.limiter.reset()
        assert unknown > known * 0.5, f"known={known*1000:.0f}ms unknown={unknown*1000:.0f}ms"

    def test_cors_allow_list(self, client):
        evil = client.get("/api/health", headers={"Origin": "https://evil.example"})
        assert evil.headers.get("Access-Control-Allow-Origin") is None
        good = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
        assert good.headers.get("Access-Control-Allow-Origin") == "http://localhost:3000"

    def test_security_headers(self, client):
        r = client.get("/api/health")
        assert r.headers["X-Content-Type-Options"] == "nosniff"
        assert r.headers["X-Frame-Options"] == "DENY"

    def test_health_does_not_leak_paths(self, client):
        assert "tesseract_path" not in client.get("/api/health").get_json()
        assert "tesseract_path" not in client.get("/api/ready").get_json()

    def test_internal_errors_not_leaked(self, appmod):
        with appmod.app.test_request_context("/api/x"):
            resp, code = appmod.handle_unexpected(sqlite3.OperationalError("no such table: users"))
            assert code == 500 and "no such table" not in resp.get_data(as_text=True)

    def test_request_size_limited(self, client):
        h, _ = new_user(client)
        r = client.post("/api/analyze/text", headers=h, data=b"{" + b" " * (9 * 1024 * 1024) + b"}",
                        content_type="application/json")
        assert r.status_code == 413

    def test_large_ingredient_list_rejected_fast(self, client):
        h, _ = new_user(client)
        text = ", ".join(f"thing{i}" for i in range(20000))
        s = time.perf_counter()
        r = client.post("/api/analyze/text", headers=h, json={"ingredients_text": text})
        assert r.status_code == 400 and time.perf_counter() - s < 1.0

    def test_max_size_text_is_fast(self, client):
        h, _ = new_user(client)
        text = ", ".join(f"item{i}" for i in range(800))[:5000]
        s = time.perf_counter()
        analyze(client, h, text)
        assert time.perf_counter() - s < 1.0

    def test_decompression_bomb_rejected(self, client, needs_ocr):
        from PIL import Image
        h, _ = new_user(client)
        buf = io.BytesIO()
        Image.new("L", (9000, 9000), 255).save(buf, "PNG")
        r = client.post("/api/analyze/image", headers=h,
                        json={"image_base64": base64.b64encode(buf.getvalue()).decode()})
        assert r.status_code == 413
