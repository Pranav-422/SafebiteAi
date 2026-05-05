import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import analyze_ingredients, parse_ingredients, app, get_db

with app.app_context():
    print("RAMEN:")
    res = analyze_ingredients(parse_ingredients("wheat flour, palm oil, salt, msg, sodium benzoate, tartrazine, tbhq"), "adult", [])
    print("Score:", res["safety_score"])

    print("CANDY:")
    res = analyze_ingredients(parse_ingredients("sugar, corn syrup, tartrazine, sunset yellow, allura red, brilliant blue, carmoisine, artificial flavors"), "adult", [])
    print("Score:", res["safety_score"])

    print("CHOC:")
    res = analyze_ingredients(parse_ingredients("sugar, cocoa butter, milk, cocoa mass, soy lecithin, vanilla extract"), "adult", [])
    print("Score:", res["safety_score"])
