"""최신 관련글을 모아 정부·공공기관 추천피드를 만듭니다."""

import json
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor

from govfeed.articles import CATEGORIES, format_when, pick_latest

_SEARCH = "https://section.blog.naver.com/ajax/SearchList.naver"
_CACHE = {"at": 0.0, "feed": None}
_TTL = 600


def _fetch_query(keyword, limit=12, opener=None):
    query = urllib.parse.urlencode(
        {
            "countPerPage": str(max(limit, 20)),
            "currentPage": "1",
            "keyword": keyword,
            "orderBy": "recentdate",
            "type": "post",
        }
    )
    req = urllib.request.Request(
        f"{_SEARCH}?{query}",
        headers={
            "User-Agent": "Mozilla/5.0",
            "Referer": "https://section.blog.naver.com/",
        },
    )
    open_fn = opener or urllib.request.urlopen
    with open_fn(req, timeout=12) as res:
        raw = res.read().decode("utf-8", "replace")
    if raw.startswith(")]}',"):
        raw = raw.split("\n", 1)[1]
    data = json.loads(raw)
    return (data.get("result") or {}).get("searchList") or []


def build_feed(fetch_query=_fetch_query, now_ms=None):
    grouped = {cat["id"]: [] for cat in CATEGORIES}

    jobs = []
    with ThreadPoolExecutor(max_workers=8) as pool:
        for cat in CATEGORIES:
            for query in cat["queries"]:
                keyword = query["q"] if isinstance(query, dict) else query
                jobs.append((cat, pool.submit(fetch_query, keyword)))
        for cat, future in jobs:
            try:
                grouped[cat["id"]].extend(future.result())
            except Exception:
                continue

    sections = []
    flat = []
    for cat in CATEGORIES:
        items = pick_latest(cat, grouped[cat["id"]], limit=12)
        if now_ms is not None:
            for item in items:
                item["when"] = format_when(item["published_at"], now_ms)
        sections.append(
            {
                "id": cat["id"],
                "name": cat["name"],
                "desc": cat["desc"],
                "color": cat["color"],
                "items": items,
            }
        )
        flat.extend(items)

    flat.sort(key=lambda item: item["published_at"], reverse=True)
    latest_ms = flat[0]["published_at"] if flat else 0
    return {
        "ok": True,
        "kind": "related-articles",
        "title": "정부·공공기관 추천피드",
        "sort": "latest",
        "updatedAt": latest_ms,
        "sections": sections,
        "items": flat,
    }


def get_feed(force=False):
    now = time.time()
    cached = _CACHE["feed"]
    if not force and cached and now - _CACHE["at"] < _TTL:
        return cached
    feed = build_feed()
    _CACHE["at"] = now
    _CACHE["feed"] = feed
    return feed
