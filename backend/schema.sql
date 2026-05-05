-- =====================================================
-- Safe Bite AI - MySQL Database Schema
-- =====================================================




-- ─────────────────────────────────────────
-- 1. USERS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    email         VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name     VARCHAR(150),
    age_group     TEXT DEFAULT 'adult',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP 
);

-- ─────────────────────────────────────────
-- 2. USER HEALTH RESTRICTIONS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS user_restrictions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INT NOT NULL,
    restriction TEXT NOT NULL,
    UNIQUE (user_id, restriction),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────
-- 3. ALLERGENS MASTER
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS allergens (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    severity    TEXT DEFAULT 'medium'
);

INSERT OR IGNORE INTO allergens (name, description, severity) VALUES
('peanut',        'Tree nut – anaphylaxis risk',                          'high'),
('milk',          'Dairy – lactose/casein intolerance',                   'medium'),
('gluten',        'Wheat protein – celiac disease',                       'high'),
('soy',           'Soy protein – common allergen',                       'medium'),
('egg',           'Egg protein – common in baked goods',                  'medium'),
('fish',          'Fish protein – common allergen',                       'high'),
('shellfish',     'Crustacean shellfish',                                 'high'),
('tree_nut',      'Tree nuts (cashew, walnut, almond)',                   'high'),
('sesame',        'Sesame seeds/oil',                                     'medium'),
('mustard',       'Mustard seeds/powder',                                 'low');

-- ─────────────────────────────────────────
-- 4. INGREDIENTS MASTER
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingredients (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         VARCHAR(200) UNIQUE NOT NULL,
    e_number     VARCHAR(20),
    category     TEXT DEFAULT 'other',
    risk_level   TEXT DEFAULT 'safe',
    reason       TEXT,
    -- age-specific restrictions
    age_child    TEXT DEFAULT 'safe',
    age_teen     TEXT DEFAULT 'safe',
    age_adult    TEXT DEFAULT 'safe',
    age_senior   TEXT DEFAULT 'safe',
    -- nutrition flags
    is_vegan_unsafe   INTEGER DEFAULT 0,
    is_vegetarian_unsafe INTEGER DEFAULT 0,
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

INSERT OR IGNORE INTO ingredients
  (name, e_number, category, risk_level, reason, age_child, age_teen, age_adult, age_senior, is_vegan_unsafe, is_vegetarian_unsafe)
VALUES
-- Colors
('tartrazine',              'E102', 'color',       'high',   'Hyperactivity in children, allergic reactions', 'avoid','limit','moderate','moderate', 0,0),
('sunset yellow',           'E110', 'color',       'high',   'May cause hyperactivity, asthma',               'avoid','limit','moderate','moderate', 0,0),
('allura red',              'E129', 'color',       'medium', 'Potential hyperactivity trigger',               'avoid','limit','safe',    'safe',     0,0),
('brilliant blue',          'E133', 'color',       'medium', 'Synthetic dye, allergic reactions',             'limit','moderate','safe', 'safe',     0,0),
('carmoisine',              'E122', 'color',       'high',   'Hyperactivity, asthma risk',                    'avoid','limit','moderate','moderate', 0,0),
-- Preservatives
('sodium benzoate',         'E211', 'preservative','medium', 'May form benzene with vitamin C',               'limit','limit','safe',    'safe',     0,0),
('tbhq',                    'E319', 'preservative','high',   'Synthetic antioxidant, toxicity in studies',    'avoid','limit','limit',   'limit',    0,0),
('bha',                     'E320', 'preservative','high',   'Possible carcinogen, endocrine disruptor',      'avoid','avoid','limit',   'limit',    0,0),
('bht',                     'E321', 'preservative','high',   'Potential carcinogen',                         'avoid','avoid','limit',   'limit',    0,0),
('sodium nitrite',          'E250', 'preservative','high',   'Forms carcinogenic nitrosamines when heated',   'avoid','limit','limit',   'limit',    0,0),
('sulfur dioxide',          'E220', 'preservative','medium', 'Can trigger asthma',                           'limit','limit','moderate','moderate', 0,0),
('potassium sorbate',       'E202', 'preservative','low',    'Generally safe, mild reactions possible',       'safe', 'safe', 'safe',    'safe',     0,0),
-- Sweeteners
('aspartame',               'E951', 'sweetener',   'medium', 'Phenylketonuria risk, headaches',               'limit','limit','moderate','moderate', 0,0),
('saccharin',               'E954', 'sweetener',   'medium', 'Past cancer concerns at high doses',            'limit','limit','moderate','moderate', 0,0),
('sucralose',               'E955', 'sweetener',   'low',    'Generally safe, gut bacteria concerns',         'moderate','safe','safe',  'safe',     0,0),
('high fructose corn syrup','',     'sweetener',   'high',   'Obesity, diabetes, liver issues',               'limit','limit','limit',   'limit',    0,0),
-- Fats
('palm oil',                '',     'fat',         'medium', 'High saturated fat, cardiovascular concerns',   'limit','moderate','moderate','moderate',1,1),
('hydrogenated oil',        '',     'fat',         'high',   'Trans fats, heart disease',                     'avoid','avoid','limit',   'limit',    0,0),
('partially hydrogenated oil','',   'fat',         'high',   'Trans fats, cardiovascular risks',              'avoid','avoid','limit',   'limit',    0,0),
-- Flavors
('msg',                     'E621', 'flavor',      'medium', 'Headaches in sensitive individuals',            'limit','limit','moderate','moderate', 0,0),
('monosodium glutamate',    'E621', 'flavor',      'medium', 'Headaches in sensitive individuals',            'limit','limit','moderate','moderate', 0,0),
-- Other
('carrageenan',             'E407', 'thickener',   'medium', 'Digestive inflammation concerns',               'limit','moderate','moderate','moderate',0,0),
('propyl gallate',          'E310', 'preservative','medium', 'Endocrine disruptor concerns',                  'limit','limit','moderate','moderate', 0,0);

-- ─────────────────────────────────────────
-- 5. INGREDIENT <-> ALLERGEN LINKS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ingredient_allergens (
    ingredient_id INT NOT NULL,
    allergen_id   INT NOT NULL,
    PRIMARY KEY (ingredient_id, allergen_id),
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id) ON DELETE CASCADE,
    FOREIGN KEY (allergen_id)   REFERENCES allergens(id)   ON DELETE CASCADE
);

-- ─────────────────────────────────────────
-- 6. PRODUCTS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS products (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         VARCHAR(255) NOT NULL,
    brand        VARCHAR(150),
    barcode      VARCHAR(50) UNIQUE,
    category     TEXT DEFAULT 'other',
    image_url    VARCHAR(500),
    raw_ingredients TEXT,           -- comma-separated raw text from label
    created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ─────────────────────────────────────────
-- 7. PRODUCT <-> INGREDIENT LINKS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS product_ingredients (
    product_id    INT NOT NULL,
    ingredient_id INT NOT NULL,
    quantity_note VARCHAR(100),     -- e.g. "high", "<5%"
    PRIMARY KEY (product_id, ingredient_id),
    FOREIGN KEY (product_id)    REFERENCES products(id)     ON DELETE CASCADE,
    FOREIGN KEY (ingredient_id) REFERENCES ingredients(id)  ON DELETE CASCADE
);

-- ─────────────────────────────────────────
-- 8. PRODUCT ANALYSIS RESULTS
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS product_analysis (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id      INT NULL,
    user_id         INT,
    safety_score    INTEGER NOT NULL,   -- 0-100
    status          TEXT NOT NULL,
    age_group       TEXT DEFAULT 'adult',
    detected_flags  TEXT,           -- list of flagged ingredient ids
    analysis_notes  TEXT,
    analyzed_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id)    REFERENCES users(id)    ON DELETE SET NULL
);

-- ─────────────────────────────────────────
-- 9. ALTERNATIVES
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS alternatives (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id   INT NOT NULL,       -- the unsafe product
    alt_name     VARCHAR(255) NOT NULL,
    alt_brand    VARCHAR(150),
    reason       VARCHAR(255),
    image_url    VARCHAR(500),
    score_delta  REAL,       -- points improvement
    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
);

-- ─────────────────────────────────────────
-- 10. SCAN HISTORY
-- ─────────────────────────────────────────
CREATE TABLE IF NOT EXISTS scan_history (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id      INT NOT NULL,
    product_id   INT,
    scan_type    TEXT DEFAULT 'image',
    ocr_raw_text TEXT,
    result_id    INT,               -- FK to product_analysis
    scanned_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id)    REFERENCES users(id)            ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(id)         ON DELETE SET NULL,
    FOREIGN KEY (result_id)  REFERENCES product_analysis(id) ON DELETE SET NULL
);

-- ─────────────────────────────────────────
-- SEED SAMPLE PRODUCTS
-- ─────────────────────────────────────────
INSERT OR IGNORE INTO products (name, brand, barcode, category, raw_ingredients) VALUES
('Pure Bloom Kombucha', 'Pure Bloom', 'PB-001', 'beverage', 'water, organic tea, organic sugar, live cultures'),
('Popular Cola Drink',  'Generic',    'GN-002', 'beverage', 'carbonated water, high fructose corn syrup, caramel color, phosphoric acid, natural flavors, caffeine, sodium benzoate'),
('Classic Potato Chips','Generic',    'GN-003', 'snack',    'potatoes, palm oil, salt, msg, tartrazine, tbhq'),
('Energy Drink',        'Generic',    'GN-004', 'beverage', 'carbonated water, high fructose corn syrup, taurine, caffeine, sodium benzoate, tartrazine, brilliant blue, sucralose'),
('Rainbow Fruit Candy', 'Generic',    'GN-005', 'candy',    'sugar, corn syrup, tartrazine, sunset yellow, allura red, brilliant blue, carmoisine, artificial flavors'),
('Milk Chocolate Bar',  'Generic',    'GN-006', 'candy',    'sugar, cocoa butter, milk, cocoa mass, soy lecithin, vanilla extract'),
('Instant Ramen',       'Generic',    'GN-007', 'meal',     'wheat flour, palm oil, salt, msg, sodium benzoate, tartrazine, tbhq'),
('Fruity Loops Cereal', 'Generic',    'GN-008', 'breakfast','corn flour, sugar, wheat flour, tartrazine, sunset yellow, allura red, bht');

-- ─────────────────────────────────────────
-- INDEXES for performance
-- ─────────────────────────────────────────
CREATE INDEX idx_scan_user      ON scan_history(user_id);
CREATE INDEX idx_analysis_prod  ON product_analysis(product_id);
CREATE INDEX idx_prod_barcode   ON products(barcode);
CREATE INDEX idx_ingr_name      ON ingredients(name);
