"""Collect public privacy policies for the GDPR Article 13 checker.

Reads data/domains.txt, finds each site's privacy-policy page, extracts the text, and saves data/policies.json.
Polite: one request every ~1.5 s, a descriptive User-Agent, public pages only, resumable.
  python src\\01_collect_policies.py
Needs: pip install requests beautifulsoup4
"""
import json, re, sys, time
from pathlib import Path
from urllib.parse import urljoin, urlparse

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"
UA = "Mozilla/5.0 (compatible; privacy-policy-research-script/1.0)"
FALLBACK = ["/privacy", "/privacy-policy", "/legal/privacy", "/privacy-notice", "/legal/privacy-policy", "/policies/privacy"]
MIN_CHARS = 2500
DELAY = 1.5

def extract_text(html):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "style", "noscript", "nav", "footer", "header", "form", "svg", "iframe"]):
        t.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    lines = []
    for el in root.find_all(["h1", "h2", "h3", "h4", "p", "li", "td"]):
        txt = " ".join(el.get_text(" ", strip=True).split())
        if not txt: continue
        if el.name in ("h1", "h2", "h3", "h4"): lines.append("\n## " + txt)
        else: lines.append(txt)
    text = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", text).strip()

def policy_links(html, base):
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html, "html.parser"); scored = []
    for a in soup.find_all("a", href=True):
        label = (a.get_text(" ", strip=True) + " " + a["href"]).lower()
        if re.search(r"privacy (policy|notice|statement)|privacy$|/privacy|datenschutz", label):
            if re.search(r"cookie|choices|settings|California|do-not-sell|opt", label, re.I) and "policy" not in label: continue
            score = (3 if re.search(r"privacy (policy|notice|statement)", label) else 1)
            scored.append((score, urljoin(base, a["href"])))
    seen, out = set(), []
    for s, u in sorted(scored, key=lambda x: -x[0]):
        u = u.split("#")[0]
        if u not in seen: seen.add(u); out.append(u)
    return out[:3]

def english_ratio(text):
    words = re.findall(r"[a-zA-Z']+", text.lower())
    if not words: return 0.0
    return sum(w in {"the", "and", "of", "to", "your", "we", "you", "our", "data"} for w in words) / len(words)

def fetch(session, url):
    r = session.get(url, timeout=15, allow_redirects=True)
    if r.status_code != 200 or "text/html" not in r.headers.get("content-type", ""): return None, r.url
    return r.text, r.url

def main():
    import requests
    out_path = DATA / "policies.json"
    done = {p["id"]: p for p in json.load(open(out_path, encoding="utf-8"))["policies"]} if out_path.exists() else {}
    failed = set(json.load(open(DATA / "failed.json")) if (DATA / "failed.json").exists() else [])
    domains = [d.strip() for d in open(DATA / "domains.txt") if d.strip()]
    s = requests.Session(); s.headers["User-Agent"] = UA; s.headers["Accept-Language"] = "en"
    for i, d in enumerate(domains, 1):
        if d in done or d in failed: continue
        cands = []
        try:
            home, final = fetch(s, f"https://www.{d}/")
            if home is None: home, final = fetch(s, f"https://{d}/")
            if home: cands += policy_links(home, final)
        except Exception: pass
        cands += [f"https://www.{d}{p}" for p in FALLBACK]
        got = None
        for u in cands[:7]:
            time.sleep(DELAY)
            try:
                html, final = fetch(s, u)
                if not html: continue
                text = extract_text(html)
                if len(text) >= MIN_CHARS and "privacy" in text.lower()[:20000] and english_ratio(text) > 0.08:
                    got = {"id": d, "url": final, "n_chars": len(text), "fetched": time.strftime("%Y-%m-%d"), "text": text}
                    break
            except Exception: continue
        if got: done[d] = got; print(f"[{i}/{len(domains)}] OK   {d}  {got['n_chars']} chars")
        else: failed.add(d); print(f"[{i}/{len(domains)}] FAIL {d}")
        json.dump({"note": "Public privacy policies, fetched once. Texts belong to their publishers; do not redistribute.",
                   "policies": list(done.values())}, open(out_path, "w", encoding="utf-8"), indent=1)
        json.dump(sorted(failed), open(DATA / "failed.json", "w"))
    ps = list(done.values())
    print(f"\nCollected {len(ps)} policies; failed {len(failed)}")
    if ps:
        n = sorted(p["n_chars"] for p in ps)
        print("length chars: min/median/max =", n[0], n[len(n)//2], n[-1], "| <=12000 chars:", sum(x <= 12000 for x in n))

if __name__ == "__main__":
    main()
