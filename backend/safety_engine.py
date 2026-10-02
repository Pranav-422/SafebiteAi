"""
Safe Bite AI - ingredient parsing, matching and scoring.

Pure functions (no Flask / DB access) so the logic can be unit-tested directly.
"""
from __future__ import annotations

import re
import unicodedata

# ─────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────
AGE_COL = {
    "child": "age_child",
    "teen": "age_teen",
    "adult": "age_adult",
    "senior": "age_senior",
}
AGE_GROUPS = frozenset(AGE_COL)

# Restriction -> allergens that make a product unsafe for that user
RESTRICTION_ALLERGENS = {
    "nut_allergy": {"peanut", "tree_nut"},
    "peanut_allergy": {"peanut"},
    "tree_nut_allergy": {"tree_nut"},
    "lactose_intolerant": {"milk"},
    "milk_allergy": {"milk"},
    "gluten_intolerant": {"gluten"},
    "egg_allergy": {"egg"},
    "soy_allergy": {"soy"},
    "fish_allergy": {"fish"},
    "shellfish_allergy": {"shellfish"},
    "sesame_allergy": {"sesame"},
    "mustard_allergy": {"mustard"},
}
DIET_RESTRICTIONS = {"vegan": "is_vegan_unsafe", "vegetarian": "is_vegetarian_unsafe"}
# Health conditions -> additives that get an extra risk multiplier
CONDITION_RULES = {
    "diabetic": {"high fructose corn syrup", "sucralose", "aspartame", "saccharin"},
    "hypertension": {"sodium benzoate", "sodium nitrite", "msg", "monosodium glutamate"},
}
ALLOWED_RESTRICTIONS = frozenset(RESTRICTION_ALLERGENS) | frozenset(DIET_RESTRICTIONS) | frozenset(CONDITION_RULES)

RISK_SCORE_MAP = {"high": 2.4, "medium": 1.3, "low": 0.6, "safe": 0.0}
AGE_MULTIPLIER = {"avoid": 1.6, "limit": 1.3, "moderate": 1.1, "safe": 1.0}
CONDITION_MULTIPLIER = 1.4
ALLERGEN_RISK = 3.0
DIET_RISK = 1.5

SCORE_MAX = 10
PENALTY_SCALE = 1.2      # points lost per unit of risk
PENALTY_DECAY = 0.7      # each further flagged ingredient counts 70% of the previous one
ALLERGEN_SCORE_CAP = 1   # a matching allergen always means "unsafe"
DIET_SCORE_CAP = 3       # a diet conflict means "not suitable"

MAX_INGREDIENTS = 300

_NEGATION_BEFORE = re.compile(r"(?:^|\s)(?:non|no|no added|without|free from|zero)\s*$")
_NEGATION_AFTER = re.compile(r"^\s*free\b")
_TRACE_BEFORE = re.compile(r"(?:may contain|traces? of|processed in|made in a facility)")
_ECODE = re.compile(r"\b(?:e|ins)\s*(\d{3,4}[a-z]?)\b")
_BARE_CODE = re.compile(r"\d{3,4}[a-z]?")
_NOISE = {"ingredients", "ingredient", "contains", "and", "or", "allergen information", "allergens"}


# ─────────────────────────────────────────
# Parsing
# ─────────────────────────────────────────
def _normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return text.lower()


def parse_ingredients(raw_text: str) -> list[str]:
    """Turn a label's ingredient text into a de-duplicated list of normalized items.

    Parenthesised sub-ingredients are kept as separate items, e.g.
    "Seasoning (MSG, Tartrazine)" -> ["seasoning", "msg", "tartrazine"].
    """
    if not isinstance(raw_text, str):
        return []
    text = _normalize(raw_text)
    text = re.sub(r"[()\[\]{}:|*&]", ",", text)
    text = re.sub(r"\.(?!\d)", ",", text)               # sentence dots split, decimals stay
    text = re.sub(r"\s+and\s+", ",", text)
    text = re.sub(r"\d+(?:\.\d+)?\s*%", " ", text)      # percentages
    text = re.sub(r"[^a-z0-9 ,;/\n]", " ", text)        # hyphens etc. -> space
    items = []
    seen = set()
    for item in re.split(r"[,;/\n]", text):
        item = re.sub(r"\s+", " ", item).strip()
        if len(item) < 2 or item in _NOISE:
            continue
        item = _ECODE.sub(r"e\1", item)
        if _BARE_CODE.fullmatch(item):
            item = "e" + item                          # "(102)" on Indian labels = INS 102
        if item.isdigit():
            continue
        if item not in seen:
            seen.add(item)
            items.append(item)
    return items[:MAX_INGREDIENTS]


# ─────────────────────────────────────────
# Matching
# ─────────────────────────────────────────
class IngredientIndex:
    """Compiled matcher over ingredient names, aliases and E-numbers (longest name wins)."""

    def __init__(self, rows: list[dict], aliases: list[tuple[str, int]], allergens: dict[int, set[str]]):
        self.by_id = {r["id"]: r for r in rows}
        self.allergens = allergens
        lookup: dict[str, int] = {}
        for r in rows:
            lookup.setdefault(_normalize(r["name"]).strip(), r["id"])
        for alias, ing_id in aliases:
            if ing_id in self.by_id:
                lookup.setdefault(_normalize(alias).strip(), ing_id)
        for r in rows:
            e = (r.get("e_number") or "").strip().lower().replace(" ", "")
            if e:
                lookup.setdefault(e, r["id"])
        self.lookup = lookup
        keys = sorted(lookup, key=len, reverse=True)
        alternation = "|".join(re.escape(k) for k in keys) or r"(?!x)x"
        self.pattern = re.compile(rf"(?<![a-z0-9])({alternation})(?:s|es)?(?![a-z0-9])")

    def match(self, item: str) -> list[dict]:
        """Return [{row, matched_as, trace}] for every non-negated ingredient found in item."""
        found = []
        for m in self.pattern.finditer(item):
            before, after = item[:m.start()], item[m.end():]
            if _NEGATION_BEFORE.search(before) or _NEGATION_AFTER.match(after):
                continue
            row = self.by_id[self.lookup[m.group(1)]]
            found.append({"row": row, "matched_as": m.group(1), "trace": bool(_TRACE_BEFORE.search(before))})
        return found


# ─────────────────────────────────────────
# Scoring
# ─────────────────────────────────────────
def grade_for_score(score: int) -> str:
    for threshold, grade in ((8, "A"), (6, "B"), (4, "C"), (2, "D")):
        if score >= threshold:
            return grade
    return "F"


def status_for_score(score: int) -> str:
    if score >= 7:
        return "safe"
    if score >= 4:
        return "moderate"
    return "unsafe"


def analyze_ingredients(ingredients: list[str], age_group: str, restrictions: list[str],
                        index: IngredientIndex) -> dict:
    age_col = AGE_COL.get(age_group, "age_adult")
    restrictions = [r for r in restrictions if r in ALLOWED_RESTRICTIONS]
    blocked_allergens: dict[str, str] = {}
    for r in restrictions:
        for a in RESTRICTION_ALLERGENS.get(r, ()):
            blocked_allergens.setdefault(a, r)

    details = []
    hits: dict[int, dict] = {}            # ingredient id -> first match info
    for raw in ingredients:
        matches = index.match(raw)
        for m in matches:
            hits.setdefault(m["row"]["id"], m)
        details.append({"raw": raw, "matched": matches[0]["row"]["name"] if matches else None,
                        "matches": [m["row"]["name"] for m in matches], "flagged": False})

    flagged, allergen_alerts, diet_conflicts = [], [], []
    for ing_id, m in hits.items():
        row = m["row"]
        age_restriction = row.get(age_col) or "safe"
        risk = RISK_SCORE_MAP.get(row["risk_level"], 0.0) * AGE_MULTIPLIER.get(age_restriction, 1.0)
        risk_level = row["risk_level"]
        reasons = [row["reason"]] if row.get("reason") and risk > 0 else []
        restriction_hit = False

        for allergen in sorted(index.allergens.get(ing_id, ())):
            if allergen in blocked_allergens:
                restriction = blocked_allergens[allergen]
                allergen_alerts.append({"ingredient": row["name"], "allergen": allergen,
                                        "restriction": restriction, "trace": m["trace"]})
                reasons.insert(0, f"{'May contain' if m['trace'] else 'Contains'} {allergen.replace('_', ' ')} "
                                  f"- conflicts with your {restriction.replace('_', ' ')} profile")
                risk = max(risk, ALLERGEN_RISK)
                risk_level = "high"
                restriction_hit = True

        for r, col in DIET_RESTRICTIONS.items():
            if r in restrictions and row.get(col):
                diet_conflicts.append({"ingredient": row["name"], "restriction": r})
                reasons.append(f"Not suitable for a {r} diet ({row.get('reason') or row['name']})")
                if risk < DIET_RISK:
                    risk, risk_level = DIET_RISK, "medium"
                restriction_hit = True

        for r, names in CONDITION_RULES.items():
            if r in restrictions and row["name"] in names and risk > 0:
                risk *= CONDITION_MULTIPLIER
                reasons.append(f"Flagged for {r}")
                restriction_hit = True

        if risk > 0:
            flagged.append({
                "id": row["id"], "name": row["name"], "risk_level": risk_level,
                "category": row.get("category"), "reason": "; ".join(dict.fromkeys(reasons)),
                "age_restriction": age_restriction, "restriction_hit": restriction_hit,
                "risk_score": round(risk, 1), "matched_as": m["matched_as"], "trace": m["trace"],
            })

    flagged.sort(key=lambda f: -f["risk_score"])
    flagged_names = {f["name"] for f in flagged}
    for d in details:
        d["flagged"] = any(n in flagged_names for n in d["matches"])

    # Worst ingredient counts fully, each further one a bit less; list length does not dilute risk.
    penalty = sum(f["risk_score"] * PENALTY_DECAY ** i for i, f in enumerate(flagged)) * PENALTY_SCALE
    score = max(0, min(SCORE_MAX, int(round(SCORE_MAX - penalty))))
    if diet_conflicts:
        score = min(score, DIET_SCORE_CAP)
    if allergen_alerts:
        score = min(score, ALLERGEN_SCORE_CAP)

    matched_count = sum(1 for d in details if d["matches"])
    coverage = matched_count / len(details) if details else 0.0
    return {
        "safety_score": score,
        "score_out_of": SCORE_MAX,
        "grade": grade_for_score(score),
        "status": status_for_score(score),
        "match_confidence": round(coverage, 2),
        "flagged": flagged,
        "allergen_alerts": allergen_alerts,
        "diet_conflicts": diet_conflicts,
        "ingredient_details": details,
        "total_ingredients": len(details),
        "matched_count": matched_count,
        "flagged_count": len(flagged),
        "restrictions_applied": sorted(restrictions),
        "age_group": age_group if age_group in AGE_GROUPS else "adult",
    }
