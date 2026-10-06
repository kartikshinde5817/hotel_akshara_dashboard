#!/usr/bin/env python3
"""Export your existing local akshara.db (from the Python version) to
akshara-export.json, so it can be imported into the Netlify version
(Admin -> Settings -> Import data).

    python tools/export_db.py [path/to/akshara.db]
"""
import json
import os
import sqlite3
import sys

here = os.path.dirname(os.path.abspath(__file__))
path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "akshara.db")
con = sqlite3.connect(path)
con.row_factory = sqlite3.Row
cols = [r["name"] for r in con.execute("PRAGMA table_info(categories)")]
sec = "COALESCE(section,'hotel')" if "section" in cols else "'hotel'"
cats = [dict(r) for r in con.execute(
    "SELECT id,name_mr,name_en,sort,{} AS section FROM categories ORDER BY sort,id".format(sec))]
cmap = {c["id"]: c["section"] for c in cats}
items = []
for r in con.execute("SELECT * FROM items ORDER BY sort,id"):
    items.append({"id": r["id"], "category_id": r["category_id"], "name_mr": r["name_mr"],
                  "name_en": r["name_en"], "type": r["type"], "active": r["active"], "sort": r["sort"],
                  "variants": json.loads(r["variants"] or "[]"), "section": cmap.get(r["category_id"], "hotel")})
bcols = [r["name"] for r in con.execute("PRAGMA table_info(bills)")]
bills = []
for r in con.execute("SELECT * FROM bills ORDER BY created_at,id"):
    bills.append({"id": r["id"], "created_at": r["created_at"], "table_no": r["table_no"] or "",
                  "customer": r["customer"] or "", "items": json.loads(r["items"] or "[]"),
                  "subtotal": r["subtotal"], "discount": r["discount"], "total": r["total"],
                  "section": (r["section"] if "section" in bcols else "hotel") or "hotel"})
keys = ["hotel_mr", "hotel_en", "tag_mr", "tag_en", "addr_mr", "addr_en", "phone", "gstin",
        "footer_mr", "footer_en", "paper", "table_count"]
settings = {r["key"]: r["value"] for r in con.execute("SELECT key,value FROM settings") if r["key"] in keys}
out = os.path.join(here, "..", "akshara-export.json")
with open(out, "w", encoding="utf-8") as f:
    json.dump({"categories": cats, "items": items, "bills": bills, "settings": settings}, f, ensure_ascii=False)
print("Exported {} categories, {} items, {} bills -> {}".format(len(cats), len(items), len(bills), os.path.abspath(out)))
