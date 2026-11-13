import json, re, importlib.util
from pathlib import Path
D = Path("data")
s = importlib.util.spec_from_file_location("c", "src/03_check_eval.py")
c = importlib.util.module_from_spec(s); s.loader.exec_module(c)
pols = {p["id"]: p for p in json.load(open(D/"policies.json", encoding="utf-8"))["policies"]}
gold = json.load(open(D/"gold_labels.json", encoding="utf-8-sig"))["labels"]
for g in gold:
    if g["split"] != "dev" or g["labels"]["retention"] != 1: continue
    t = pols[g["id"]]["text"]
    if c.RULES["retention"](t): continue
    print("=====", g["id"])
    seen = 0
    for m in re.finditer(r"retain|retention|how long|kept|keep your|stored for|delete", t, re.I):
        print("  ...", t[max(0, m.start()-80):m.end()+220].replace("\n", " "))
        seen += 1
        if seen >= 3: break
