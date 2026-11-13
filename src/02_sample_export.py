"""Pick the policies to hand-label and export them in batches for reading.

  python src\\02_sample_export.py 0 5      # first 5 policies of the labelling sample -> reports\\batch.txt
  python src\\02_sample_export.py 5 5
Sample: policies with 8,000 to 30,000 characters (shorter = labellable), 20 drawn with seed 15; first 10 = dev, last 10 = test.
"""
import json, random, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
DATA, REP = ROOT / "data", ROOT / "reports"; REP.mkdir(exist_ok=True)
LO, HI, N, SEED = 8000, 30000, 20, 15

def main():
    pols = json.load(open(DATA / "policies.json", encoding="utf-8"))["policies"]
    sp = DATA / "label_sample.json"
    if sp.exists():
        sample = json.load(open(sp, encoding="utf-8"))["sample"]
    else:
        elig = sorted((p for p in pols if LO <= p["n_chars"] <= HI), key=lambda p: p["id"])
        picked = random.Random(SEED).sample(elig, min(N, len(elig)))
        half = len(picked) // 2
        sample = [{"id": p["id"], "split": "dev" if i < half else "test", "n_chars": p["n_chars"], "url": p["url"]}
                  for i, p in enumerate(picked)]
        json.dump({"note": f"seed {SEED}, {LO}-{HI} chars", "eligible": len(elig), "sample": sample},
                  open(sp, "w", encoding="utf-8"), indent=1)
        print(f"{len(elig)} eligible policies; sample of {len(sample)} saved to data/label_sample.json")
    start = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    n = int(sys.argv[2]) if len(sys.argv) > 2 else 5
    by_id = {p["id"]: p for p in pols}
    chunk = sample[start:start + n]
    out = []
    for s in chunk:
        out.append(f"ID: {s['id']} | split: {s['split']} | chars: {s['n_chars']}\n{by_id[s['id']]['text']}\n\n=====\n")
    open(REP / "batch.txt", "w", encoding="utf-8").write("\n".join(out))
    print(f"Wrote reports\\batch.txt with {len(chunk)} policies: " + ", ".join(f"{s['id']} ({s['split']})" for s in chunk))

if __name__ == "__main__":
    main()
