# tools/web.py — web search + fetch. Search = chain HN Algolia + GitHub API + Wikipedia API
# (tanpa API key; HN & GitHub & Wiki terbuka). Fetch = HTTP murni.
import httpx, re, json
from html import unescape
from urllib.parse import quote

UA = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"}

def _clean(s: str) -> str:
    s = unescape(s)
    s = re.sub(r"<[^>]+>", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def _hn(query: str, n: int):
    try:
        r = httpx.get("https://hn.algolia.com/api/v1/search",
                      params={"query": query, "tags": "story", "hitsPerPage": n}, timeout=15)
        out = []
        for h in r.json().get("hits", []):
            url = h.get("url") or f"https://news.ycombinator.com/item?id={h.get('objectID')}"
            out.append({"title": h.get("title") or "", "url": url,
                        "snippet": (h.get("story_text") or "")[:200], "source": "hn"})
        return out
    except Exception:
        return []

def _gh(query: str, n: int):
    try:
        r = httpx.get("https://api.github.com/search/repositories",
                      params={"q": query, "per_page": n},
                      headers={**UA, "Accept": "application/vnd.github+json"}, timeout=15)
        out = []
        for it in r.json().get("items", []):
            out.append({"title": f"{it['full_name']} ({it['stargazers_count']} stars)",
                        "url": it["html_url"],
                        "snippet": (it.get("description") or "")[:200], "source": "github"})
        return out
    except Exception:
        return []

def _wiki(query: str, n: int):
    try:
        r = httpx.get("https://en.wikipedia.org/w/api.php",
                      params={"action": "query", "list": "search", "srsearch": query,
                              "format": "json", "utf8": 1, "srlimit": n}, timeout=15)
        out = []
        for s in r.json().get("query", {}).get("search", []):
            out.append({"title": s["title"],
                        "url": "https://en.wikipedia.org/wiki/" + quote(s["title"].replace(" ", "_")),
                        "snippet": _clean(s.get("snippet", ""))[:200], "source": "wikipedia"})
        return out
    except Exception:
        return []

def web_search(query: str, count: int = 8) -> dict:
    """Cari topik di web (HN + GitHub + Wikipedia, dedup). Tanpa API key."""
    seen, out = set(), []
    seen, out = set(), []
    for batch in (_hn(query, 6), _gh(query, 5), _wiki(query, 5)):
        for r in batch:
            key = (r["url"].split("/")[2] if "://" in r["url"] else r["url"], r["title"][:40])
            if key in seen or not r["title"]:
                continue
            seen.add(key)
            out.append(r)
        if len(out) >= count:
            break
    return {"ok": True, "engine": "hn+gh+wiki", "count": len(out[:count]),
            "results": out[:count]}

def web_fetch(url: str, max_chars: int = 4000) -> dict:
    """Ambil halaman web, extract teas utama (judul + paragraf pertama)."""
    try:
        r = httpx.get(url, headers=UA, timeout=25, follow_redirects=True)
        html = r.text
        title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
        title = _clean(title.group(1)) if title else url
        paras = [_clean(p) for p in re.findall(r"<p[^>]*>(.*?)</p>", html, re.S)]
        paras = [p for p in paras if len(p) > 40]
        body = " ".join(paras)[:max_chars]
        return {"ok": True, "url": url, "status": r.status_code,
                "title": title, "text": body, "bytes": len(html)}
    except Exception as e:
        return {"ok": False, "url": url, "error": str(e)}
