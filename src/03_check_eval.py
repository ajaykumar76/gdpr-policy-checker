"""GDPR Art. 13 privacy-policy checker: rules vs retrieval + local LLM.

Usage (venv active, Ollama running for llm):
  python src/03_check_eval.py --method rules --split dev
  python src/03_check_eval.py --method llm   --split dev
  python src/03_check_eval.py --method rules --split test      # run ONCE, after freezing
  python src/03_check_eval.py --method llm --population        # all collected policies

FREEZE RULE (stated before the test run): tune only on dev. Pick the method with the
higher dev micro-F1 as long as its false-assurance rate is not worse than the rules
baseline's. Then run test once and report whatever comes out.
False assurance = predicting an element is present when the gold label says it is not.
"""
import argparse, json, re, os, random
from pathlib import Path

D = Path(__file__).resolve().parent.parent / "data"
E = ["controller_contact","dpo_contact","legal_basis","recipients",
     "international_transfers","retention","data_subject_rights","supervisory_complaint"]

EMAIL = r"[\w.+-]+@[\w-]+\.[\w.-]+"
RULES = {
 "controller_contact": lambda t: bool(re.search(EMAIL, t)) or bool(re.search(
     r"registered (office|address)|our (postal )?address|P\.?O\.? Box|\b\d{1,5}\s+\w+\s+(Street|St\.|Road|Avenue|Ave\.|Strasse|Straße|Platz)\b", t, re.I)),
 "dpo_contact": lambda t: any(re.search(EMAIL + r"|address|P\.?O\.? Box|\+\d", t[max(0,m.start()-250):m.end()+250], re.I)
     for m in re.finditer(r"data protection officer|\bDPO\b", t, re.I)),
 "legal_basis": lambda t: bool(re.search(r"legal basis|lawful basis|legitimate interest|Article 6|6\(1\)|performance of (a|the) contract", t, re.I)),
 "recipients": lambda t: bool(re.search(r"service providers|processors|third[- ]part(y|ies)|affiliates|recipients|partners", t, re.I)),
 "international_transfers": lambda t: bool(re.search(r"standard contractual clauses|\bSCCs?\b|adequacy decision|binding corporate rules|data privacy framework|privacy shield|appropriate safeguards", t, re.I)),
 "retention": lambda t: bool(re.search(r"(retain|retention|how long|stored for|kept for|keep (the |your )?(personal )?(data|information)|store (the |your )?(personal )?(data|information)).{0,400}?((\d+|one|two|three|four|five|six|seven|ten)\s*(\(\d+\)\s*)?(days?|months?|years?)|criteria|depends on|determin|factors|as long as (you|your)|(laws?|regulations?|legal).{0,40}require)", t, re.I|re.S)),
 "data_subject_rights": lambda t: len(set(m.group(1).lower() for m in re.finditer(r"(access|eras|delet|rectif|correct|portab|object|restrict)", t, re.I))) >= 3
     and bool(re.search(r"\byour rights\b|right to|you (have|may) the right", t, re.I)),
 "supervisory_complaint": lambda t: bool(re.search(r"supervisory authorit|data protection authorit|lodge a complaint|file a complaint|Information Commissioner|regulator", t, re.I)),
}

CRIT = {
 "controller_contact": "the controller's identity AND real contact details (an email address or postal address). A bare link or placeholder does not count.",
 "dpo_contact": "a Data Protection Officer WITH contact details (email or address). Mentioning a DPO with only a link does not count.",
 "legal_basis": "the legal basis/bases for processing (e.g. consent, contract, legitimate interests, legal obligation).",
 "recipients": "who personal data is shared with (categories of recipients such as service providers, affiliates, partners).",
 "international_transfers": "transfers outside the EU/EEA AND a NAMED safeguard (standard contractual clauses, adequacy decision, binding corporate rules, Data Privacy Framework). Consent alone or a vague statement does not count.",
 "retention": "how long data is kept, or the specific criteria used to decide. 'As long as necessary' on its own does not count.",
 "data_subject_rights": "the user's rights (access, rectification, erasure, restriction, objection, portability, withdraw consent).",
 "supervisory_complaint": "the right to lodge a complaint with a supervisory/data protection authority.",
}
PLACEHOLDER = re.compile(r"click here|learn more|see below|\[.*?\]|n/?a\b", re.I)

def chunks(t, n=1200, o=200):
    return [t[i:i+n] for i in range(0, max(1, len(t)-o), n-o)]

_emb = None
def embedder():
    global _emb
    if _emb is None:
        from sentence_transformers import SentenceTransformer
        _emb = SentenceTransformer("all-MiniLM-L6-v2")
    return _emb

def llm_check(text, el, model, k, cache, key):
    if key in cache: return cache[key]
    import numpy as np, ollama
    ch = chunks(text); m = embedder()
    q = m.encode([CRIT[el]], normalize_embeddings=True)
    c = m.encode(ch, normalize_embeddings=True)
    top = np.argsort(-(c @ q.T).ravel())[:k]
    ctx = "\n---\n".join(ch[i] for i in sorted(top))
    prompt = (f"Below are excerpts from a privacy policy.\nQuestion: does the policy actually state {CRIT[el]}\n"
              "Answer only from the excerpts. If present, copy ONE exact quote (verbatim, at least 15 characters) that shows it.\n"
              'Reply as JSON: {"present": true/false, "quote": "..."}\n\n' + ctx)
    try:
        r = ollama.chat(model=model, messages=[{"role":"user","content":prompt}], format="json", options={"temperature":0})
        o = json.loads(r["message"]["content"])
    except Exception:
        o = {"present": False, "quote": ""}
    q_ = str(o.get("quote","")).strip()
    norm = lambda s: re.sub(r"\s+", " ", s).lower()
    ok = bool(o.get("present")) and len(q_) >= 15 and norm(q_) in norm(text) and not PLACEHOLDER.fullmatch(q_)
    cache[key] = ok
    return ok

def predict(p, method, model, k, cache):
    if method == "rules": return {e: int(RULES[e](p["text"])) for e in E}
    return {e: int(llm_check(p["text"], e, model, k, cache, f"{p['id']}|{e}|{model}|{k}")) for e in E}

def metrics(rows):
    tp=fp=fn=tn=0
    for g,pr in rows:
        for e in E:
            tp+=g[e]&pr[e]; fp+=(1-g[e])&pr[e]; fn+=g[e]&(1-pr[e]); tn+=(1-g[e])&(1-pr[e])
    P=tp/(tp+fp) if tp+fp else 0; R=tp/(tp+fn) if tp+fn else 0
    F=2*P*R/(P+R) if P+R else 0
    return dict(tp=tp,fp=fp,fn=fn,tn=tn,P=P,R=R,F1=F,acc=(tp+tn)/max(1,tp+fp+fn+tn),
                false_assurance=fp/max(1,fp+tn))

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["rules","llm"], default="rules")
    ap.add_argument("--split", choices=["dev","test"], default="dev")
    ap.add_argument("--population", action="store_true")
    ap.add_argument("--model", default="llama3.2")
    ap.add_argument("--k", type=int, default=5)
    a = ap.parse_args()
    pols = {p["id"]: p for p in json.load(open(D/"policies.json", encoding="utf-8"))["policies"]}
    cpath = D/f"cache_llm_{a.model}.json"
    cache = json.load(open(cpath)) if cpath.exists() else {}
    if a.population:
        res = {}
        for i,(pid,p) in enumerate(pols.items(),1):
            res[pid] = predict(p, a.method, a.model, a.k, cache)
            if i % 5 == 0: json.dump(cache, open(cpath,"w"))
        json.dump(cache, open(cpath,"w"))
        print(f"Population ({len(res)} policies), method={a.method}: share with element present")
        for e in E: print(f"  {e:24s} {sum(r[e] for r in res.values())/len(res):.0%}")
        json.dump(res, open(D/f"population_{a.method}.json","w"), indent=1)
        return
    gold = json.load(open(D/"gold_labels.json", encoding="utf-8-sig"))["labels"]
    gold = [g for g in gold if g["split"] == a.split and g["id"] in pols]
    rows = []; per = {e: [] for e in E}
    for g in gold:
        pr = predict(pols[g["id"]], a.method, a.model, a.k, cache); rows.append((g["labels"], pr))
        for e in E: per[e].append((g["labels"][e], pr[e], e in g["borderline"]))
    json.dump(cache, open(cpath,"w"))
    base = [(g, {e:0 for e in E}) for g,_ in rows]
    print(f"{a.method} on {a.split} ({len(rows)} policies, {len(rows)*8} items)")
    m = metrics(rows)
    print("  micro P={P:.2f} R={R:.2f} F1={F1:.2f} acc={acc:.2f} false_assurance={false_assurance:.2f} (FP={fp}, FN={fn})".format(**m))
    b = metrics(base); print("  always-absent baseline acc={:.2f}".format(b["acc"]))
    random.seed(15); fs=[]
    for _ in range(1000):
        s=[random.choice(rows) for _ in rows]; fs.append(metrics(s)["F1"])
    fs.sort(); print(f"  F1 bootstrap 95% CI (over policies): {fs[25]:.2f}-{fs[974]:.2f}")
    print("  per element (n=pos in gold | precision recall | false positives on borderline items):")
    for e in E:
        t = per[e]; tp=sum(g&p for g,p,_ in t); fp=sum((1-g)&p for g,p,_ in t); fn=sum(g&(1-p) for g,p,_ in t)
        print(f"   {e:24s} pos={sum(g for g,_,_ in t):2d} TP={tp} FP={fp} FN={fn}  borderline FP={sum(((1-g)&p) and bd for g,p,bd in t)}")

if __name__ == "__main__":
    main()



