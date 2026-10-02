"""
Reference data for the safety engine: allergen-bearing ingredients, animal-derived
ingredients, alternative names (aliases) and "shadow" entries that stop false matches
(e.g. "cocoa butter" must not be read as dairy "butter").

apply(conn) is idempotent and runs on every start after schema.sql.
"""

# (name, category, risk_level, reason, e_number, vegan_unsafe, vegetarian_unsafe, allergens, aliases)
INGREDIENTS = [
    # ── Peanut / tree nuts ──
    ("peanut", "allergen", "safe", "Peanut - common cause of severe allergic reactions", "", 0, 0,
     ["peanut"], ["groundnut", "arachis oil", "arachis", "peanut butter", "peanut oil", "peanut flour", "monkey nut"]),
    ("almond", "allergen", "safe", "Tree nut", "", 0, 0, ["tree_nut"], ["almond flour", "almond milk", "badam"]),
    ("cashew", "allergen", "safe", "Tree nut", "", 0, 0, ["tree_nut"], ["kaju", "cashew nut"]),
    ("walnut", "allergen", "safe", "Tree nut", "", 0, 0, ["tree_nut"], ["akhrot"]),
    ("hazelnut", "allergen", "safe", "Tree nut", "", 0, 0, ["tree_nut"], ["filbert"]),
    ("pistachio", "allergen", "safe", "Tree nut", "", 0, 0, ["tree_nut"], ["pista"]),
    ("pecan", "allergen", "safe", "Tree nut", "", 0, 0, ["tree_nut"], []),
    ("macadamia", "allergen", "safe", "Tree nut", "", 0, 0, ["tree_nut"], ["macadamia nut"]),
    ("tree nuts", "allergen", "safe", "Tree nuts", "", 0, 0, ["tree_nut"], ["nuts", "mixed nuts", "brazil nut"]),
    # ── Milk ──
    ("milk", "allergen", "safe", "Dairy - milk protein / lactose", "", 1, 0, ["milk"],
     ["milk solids", "milk powder", "skimmed milk", "skim milk", "whole milk", "milk fat", "milk protein",
      "condensed milk", "cream", "butter", "butterfat", "buttermilk", "cheese", "ghee", "yogurt", "yoghurt",
      "curd", "paneer", "khoa", "khoya", "milk chocolate", "dairy"]),
    ("whey", "allergen", "safe", "Dairy protein", "", 1, 0, ["milk"], ["whey powder", "whey protein"]),
    ("casein", "allergen", "safe", "Dairy protein", "", 1, 0, ["milk"], ["caseinate", "sodium caseinate", "calcium caseinate"]),
    ("lactose", "allergen", "safe", "Milk sugar", "", 1, 0, ["milk"], []),
    # ── Gluten cereals ──
    ("wheat", "allergen", "safe", "Contains gluten", "", 0, 0, ["gluten"],
     ["wheat flour", "whole wheat", "wheat starch", "enriched flour", "refined wheat flour", "maida", "atta",
      "semolina", "sooji", "suji", "rava", "durum", "spelt", "bulgur", "couscous", "seitan", "farina"]),
    ("barley", "allergen", "safe", "Contains gluten", "", 0, 0, ["gluten"],
     ["malt", "malt extract", "barley malt", "malted barley", "malt vinegar"]),
    ("rye", "allergen", "safe", "Contains gluten", "", 0, 0, ["gluten"], []),
    ("gluten", "allergen", "safe", "Gluten", "", 0, 0, ["gluten"], ["wheat gluten"]),
    # ── Egg (egg is non-vegetarian under Indian FSSAI labelling) ──
    ("egg", "allergen", "safe", "Egg protein - common allergen", "", 1, 1, ["egg"],
     ["egg white", "egg yolk", "whole egg", "egg powder", "albumin", "albumen", "ovalbumin", "mayonnaise"]),
    # ── Soy ──
    ("soy", "allergen", "safe", "Soy protein - common allergen", "", 0, 0, ["soy"],
     ["soya", "soybean", "soya bean", "soy lecithin", "soya lecithin", "soy protein", "soya protein", "soy sauce",
      "soy milk", "tofu", "edamame"]),
    # ── Fish / shellfish ──
    ("fish", "allergen", "safe", "Fish protein - common allergen", "", 1, 1, ["fish"],
     ["fish sauce", "fish oil", "anchovy", "anchovies", "tuna", "salmon", "cod", "sardine", "mackerel"]),
    ("shellfish", "allergen", "safe", "Crustacean / mollusc - common allergen", "", 1, 1, ["shellfish"],
     ["shrimp", "prawn", "crab", "lobster", "crayfish", "oyster", "mussel", "clam", "squid"]),
    # ── Sesame / mustard ──
    ("sesame", "allergen", "safe", "Sesame - common allergen", "", 0, 0, ["sesame"],
     ["sesame seed", "sesame oil", "tahini", "til", "gingelly", "gingelly oil"]),
    ("mustard", "allergen", "safe", "Mustard - allergen", "", 0, 0, ["mustard"],
     ["mustard seed", "mustard oil", "mustard powder", "sarson"]),
    # ── Animal-derived (diet) ──
    ("gelatin", "animal", "safe", "Animal-derived (bones/skin)", "E441", 1, 1, [], ["gelatine"]),
    ("carmine", "animal", "safe", "Red colour made from insects", "E120", 1, 1, [], ["cochineal", "carminic acid"]),
    ("lard", "animal", "safe", "Pork fat", "", 1, 1, [], []),
    ("tallow", "animal", "safe", "Animal fat", "", 1, 1, [], ["beef fat", "beef tallow"]),
    ("meat", "animal", "safe", "Meat", "", 1, 1, [],
     ["chicken", "beef", "pork", "mutton", "bacon", "ham", "meat extract", "chicken extract", "chicken fat"]),
    ("rennet", "animal", "safe", "Usually from calf stomach", "", 1, 1, [], ["animal rennet"]),
    ("isinglass", "animal", "safe", "Fish bladder", "", 1, 1, ["fish"], []),
    ("honey", "animal", "safe", "Bee product", "", 1, 0, [], []),
    ("beeswax", "animal", "safe", "Bee product", "E901", 1, 0, [], []),
    ("shellac", "animal", "safe", "Insect resin", "E904", 1, 0, [], []),
    # ── Shadow entries: plant-based look-alikes (stop false dairy/nut matches) ──
    ("cocoa butter", "fat", "safe", "Plant fat from cocoa beans", "", 0, 0, [], []),
    ("shea butter", "fat", "safe", "Plant fat", "", 0, 0, [], []),
    ("coconut milk", "other", "safe", "Plant based", "", 0, 0, [], ["coconut cream"]),
    ("oat milk", "other", "safe", "Plant based", "", 0, 0, [], []),
    ("rice milk", "other", "safe", "Plant based", "", 0, 0, [], []),
    ("cream of tartar", "other", "safe", "Potassium bitartrate", "E336", 0, 0, [], []),
    ("nutmeg", "spice", "safe", "Spice (not a tree nut)", "", 0, 0, [], []),
    ("buckwheat", "grain", "safe", "Gluten-free pseudo-cereal", "", 0, 0, [], ["kuttu"]),
]

# Extra names for additives already seeded by schema.sql
ADDITIVE_ALIASES = {
    "tartrazine": ["yellow 5", "fd c yellow 5"],
    "sunset yellow": ["yellow 6", "sunset yellow fcf"],
    "allura red": ["red 40", "allura red ac"],
    "brilliant blue": ["blue 1", "brilliant blue fcf"],
    "carmoisine": ["azorubine"],
    "tbhq": ["tertiary butylhydroquinone", "tert butylhydroquinone"],
    "bha": ["butylated hydroxyanisole"],
    "bht": ["butylated hydroxytoluene"],
    "sulfur dioxide": ["sulphur dioxide"],
    "high fructose corn syrup": ["hfcs", "glucose fructose syrup", "fructose glucose syrup", "corn syrup solids"],
    "palm oil": ["palmolein", "palm olein", "palm fat", "palm kernel oil", "palm kernel fat"],
    "partially hydrogenated oil": ["partially hydrogenated vegetable oil", "partially hydrogenated fat"],
    "hydrogenated oil": ["hydrogenated vegetable oil", "hydrogenated fat", "vanaspati", "shortening"],
    "monosodium glutamate": ["flavour enhancer 621", "flavor enhancer 621"],
}


def apply(conn):
    cur = conn.cursor()
    for (name, category, risk, reason, e_num, vegan_u, veg_u, allergens, aliases) in INGREDIENTS:
        cur.execute(
            "INSERT OR IGNORE INTO ingredients (name, e_number, category, risk_level, reason, "
            "is_vegan_unsafe, is_vegetarian_unsafe) VALUES (?,?,?,?,?,?,?)",
            (name, e_num, category, risk, reason, vegan_u, veg_u),
        )
        ing_id = cur.execute("SELECT id FROM ingredients WHERE name=?", (name,)).fetchone()[0]
        for a in allergens:
            cur.execute(
                "INSERT OR IGNORE INTO ingredient_allergens (ingredient_id, allergen_id) "
                "SELECT ?, id FROM allergens WHERE name=?", (ing_id, a))
        for alias in aliases:
            cur.execute("INSERT OR IGNORE INTO ingredient_aliases (alias, ingredient_id) VALUES (?,?)",
                        (alias, ing_id))
    for name, aliases in ADDITIVE_ALIASES.items():
        row = cur.execute("SELECT id FROM ingredients WHERE name=?", (name,)).fetchone()
        if row:
            for alias in aliases:
                cur.execute("INSERT OR IGNORE INTO ingredient_aliases (alias, ingredient_id) VALUES (?,?)",
                            (alias, row[0]))
    conn.commit()
