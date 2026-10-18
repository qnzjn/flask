"""관련글 고르기. 뉴스 기사는 빼고, 주제와 맞는 글만 최신순으로 남깁니다."""

import html
import re
from datetime import datetime, timezone, timedelta

KST = timezone(timedelta(hours=9))

# 언론 기사·속보 제목. 추천피드에는 넣지 않습니다.
_NEWS_RE = re.compile(
    r"속보|단독|인터뷰|논란|구속|피의자|사망|신문|헤드라인|"
    r"기자\s|취재|보도자료|브리핑|긴급"
)
_NOISE_RE = re.compile(r"데뷔|굿즈|머그컵|세일페스타|유튜브 근황|동안 자기관리|맛집")
_TAG_RE = re.compile(r"<[^>]+>")
_SPACE_RE = re.compile(r"\s+")

_STOP = {"방법", "정리", "안내", "총정리", "관련", "최신", "공식", "등", "및"}

# 검색어에서 제목에 반드시 남아야 하는 핵심어를 anchor 로 둡니다.
CATEGORIES = [
    {
        "id": "policy",
        "name": "정부 정책",
        "desc": "새로운 지원제도·정책 안내",
        "color": "#1d4ed8",
        "queries": [
            {"q": "에너지바우처 신청", "anchor": "바우처"},
            {"q": "정부 지원금", "anchor": "지원금"},
            {"q": "바우처 신청", "anchor": "바우처"},
        ],
    },
    {
        "id": "welfare",
        "name": "지원금·복지",
        "desc": "청년 지원금·복지 혜택",
        "color": "#0f766e",
        "queries": [
            {"q": "청년 월세 지원", "anchor": "청년"},
            {"q": "청년 지원금", "anchor": "청년"},
            {"q": "청년 수당", "anchor": "청년"},
        ],
    },
    {
        "id": "local",
        "name": "지역 소식",
        "desc": "부산·서울·울산 등 지자체 공지",
        "color": "#0369a1",
        "queries": [
            {"q": "서울시 청년 지원", "anchor": "서울"},
            {"q": "부산시 청년 지원", "anchor": "부산"},
            {"q": "울산시 청년", "anchor": "울산"},
            {"q": "서울시 공고", "anchor": "서울"},
            {"q": "부산시 공고", "anchor": "부산"},
            {"q": "울산시 공고", "anchor": "울산"},
            {"q": "서울시 지원", "anchor": "서울"},
            {"q": "부산시 지원", "anchor": "부산"},
            {"q": "울산시 지원", "anchor": "울산"},
        ],
    },
    {
        "id": "festival",
        "name": "축제·행사",
        "desc": "지역 축제·무료 행사",
        "color": "#c2410c",
        "queries": [
            {"q": "축제 일정", "anchor": "축제"},
            {"q": "무료 축제", "anchor": "축제"},
            {"q": "부산 축제", "anchor": "축제"},
            {"q": "서울 축제", "anchor": "축제"},
        ],
    },
    {
        "id": "jobs",
        "name": "일자리",
        "desc": "공공기관 채용·취업지원",
        "color": "#4338ca",
        "queries": [
            {"q": "채용 공고", "anchor": "채용"},
            {"q": "공공기관 채용", "anchor": "채용"},
            {"q": "취업 지원금", "anchor": "취업"},
        ],
    },
    {
        "id": "housing",
        "name": "주거·부동산",
        "desc": "공공임대·주택 청약 안내",
        "color": "#b45309",
        "queries": [
            {"q": "아파트 청약", "anchor": "청약"},
            {"q": "공공임대 신청", "anchor": "공공임대"},
            {"q": "주택청약", "anchor": "청약"},
        ],
    },
    {
        "id": "edu",
        "name": "교육",
        "desc": "무료 강좌·자격증 지원",
        "color": "#7c3aed",
        "queries": [
            {"q": "자격증 국비", "anchor": "자격증"},
            {"q": "국비 강좌", "anchor": "국비"},
            {"q": "내일배움카드 자격증", "anchor": "내일배움"},
        ],
    },
    {
        "id": "health",
        "name": "건강",
        "desc": "질병관리청 등 공식 건강정보",
        "color": "#be123c",
        "queries": [
            {"q": "독감 예방접종", "anchor": "예방접종"},
            {"q": "코로나 예방접종", "anchor": "예방접종"},
            {"q": "질병관리청", "anchor": "질병관리"},
        ],
    },
]

CATEGORY_BY_ID = {c["id"]: c for c in CATEGORIES}


def clean_text(value):
    text = _TAG_RE.sub(" ", value or "")
    text = html.unescape(text)
    return _SPACE_RE.sub(" ", text).strip()


def is_news(title):
    return bool(_NEWS_RE.search(title or ""))


def _folded(value):
    return _SPACE_RE.sub("", value or "").lower()


def _contains(title, word):
    if not word:
        return False
    return word.lower() in title.lower() or word.lower() in _folded(title)


def _query_tokens(query):
    return [word for word in query.split() if len(word) >= 2 and word not in _STOP]


def title_matches_query(title, query, anchor=""):
    tokens = _query_tokens(query)
    if anchor and not _contains(title, anchor):
        return False
    if not tokens:
        return bool(anchor and _contains(title, anchor))
    hits = sum(1 for word in tokens if _contains(title, word))
    need = 1 if len(tokens) == 1 else 2
    return hits >= need


def is_related(category, title, desc=""):
    title = title or ""
    if is_news(title) or _NOISE_RE.search(title):
        return False
    for query in category["queries"]:
        text = query["q"] if isinstance(query, dict) else query
        anchor = query.get("anchor", "") if isinstance(query, dict) else ""
        if title_matches_query(title, text, anchor):
            return True
    return False


def published_ms(value):
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def format_when(ms, now_ms=None):
    if not ms:
        return ""
    if now_ms is None:
        now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    delta = max(0, now_ms - ms)
    minutes = delta // 60000
    if minutes < 1:
        label = "방금"
    elif minutes < 60:
        label = f"{minutes}분 전"
    elif minutes < 60 * 24:
        label = f"{minutes // 60}시간 전"
    elif minutes < 60 * 24 * 7:
        label = f"{minutes // (60 * 24)}일 전"
    else:
        label = datetime.fromtimestamp(ms / 1000, KST).strftime("%Y.%m.%d")
    return label


def pick_latest(category, posts, limit=12):
    """주제와 맞는 관련글만 최신순으로 고릅니다."""
    chosen = []
    seen = set()
    for post in posts:
        title = clean_text(post.get("title"))
        desc = clean_text(post.get("desc") or post.get("contents"))
        url = (post.get("url") or post.get("postUrl") or "").strip()
        if not title or not url or url in seen:
            continue
        if post.get("marketPost"):
            continue
        if not is_related(category, title, desc):
            continue
        seen.add(url)
        ms = published_ms(post.get("published_at") or post.get("addDate"))
        thumb = post.get("img") or ""
        if not thumb:
            thumbs = post.get("thumbnails") or []
            if thumbs and isinstance(thumbs[0], dict):
                thumb = thumbs[0].get("url") or ""
        chosen.append(
            {
                "cat": category["id"],
                "catName": category["name"],
                "catDesc": category["desc"],
                "color": category["color"],
                "title": title,
                "desc": desc[:180],
                "url": url,
                "source": clean_text(post.get("source") or post.get("blogName") or post.get("nickName") or "관련글"),
                "img": thumb,
                "published_at": ms,
                "when": format_when(ms),
                "kind": "article",
            }
        )
    chosen.sort(key=lambda item: item["published_at"], reverse=True)
    return chosen[:limit]
