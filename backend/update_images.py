import pymysql

DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root123",
    "database": "safebite_db",
    "charset": "utf8mb4"
}

conn = pymysql.connect(**DB_CONFIG)

updates = {
    "Instant Ramen": "/products/instant_ramen.png",
    "Fruity Loops Cereal": "/products/fruity_cereal.png"
}

with conn.cursor() as cur:
    for name, url in updates.items():
        cur.execute("UPDATE products SET image_url = %s WHERE name = %s", (url, name))

conn.commit()
conn.close()
print("Missing images updated successfully!")
