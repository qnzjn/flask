import json
import unittest

import app as app_module
from govfeed.articles import CATEGORIES, format_when, is_news, is_related, pick_latest
from govfeed.collector import build_feed


POLICY = CATEGORIES[0]
LOCAL = next(cat for cat in CATEGORIES if cat["id"] == "local")


class ArticleTests(unittest.TestCase):
    def test_news_titles_are_excluded(self):
        self.assertTrue(is_news("[속보] 지원금 발표"))
        self.assertFalse(is_related(POLICY, "[속보] 새로운 지원제도 발표", "신청 안내"))

    def test_unrelated_post_is_dropped(self):
        posts = [
            {
                "title": "휴대용 정수기 고르는 법",
                "contents": "세균 제거 기준",
                "postUrl": "https://blog.naver.com/a/1",
                "addDate": 3000,
                "blogName": "생활",
            },
            {
                "title": "2026 청년 지원금 신청 방법 정리",
                "contents": "복지 혜택과 신청 안내",
                "postUrl": "https://blog.naver.com/a/2",
                "addDate": 2000,
                "blogName": "정책노트",
            },
        ]
        welfare = next(cat for cat in CATEGORIES if cat["id"] == "welfare")
        picked = pick_latest(welfare, posts)
        self.assertEqual([item["url"] for item in picked], ["https://blog.naver.com/a/2"])
        self.assertEqual(picked[0]["kind"], "article")

    def test_latest_order_and_local_notice(self):
        posts = [
            {
                "title": "울산시 청년 모집 공고",
                "contents": "주말 일정",
                "postUrl": "https://blog.naver.com/a/old",
                "addDate": 1000,
            },
            {
                "title": "서울시 청년 월세 지원 공고",
                "contents": "시청 모집",
                "postUrl": "https://blog.naver.com/a/new",
                "addDate": 5000,
            },
            {
                "title": "부산 맛집 후기",
                "contents": "저녁 메뉴",
                "postUrl": "https://blog.naver.com/a/food",
                "addDate": 9000,
            },
        ]
        picked = pick_latest(LOCAL, posts)
        self.assertEqual([item["url"] for item in picked], [
            "https://blog.naver.com/a/new",
            "https://blog.naver.com/a/old",
        ])

    def test_relative_time(self):
        self.assertEqual(format_when(1_000_000, 1_000_000 + 5 * 60 * 1000), "5분 전")

    def test_feed_uses_related_articles_only(self):
        def fake_fetch(keyword, limit=12):
            return [
                {
                    "title": f"{keyword} 신청 안내",
                    "contents": "최신 관련글",
                    "postUrl": f"https://blog.naver.com/post/{keyword}",
                    "addDate": 2_000,
                    "blogName": "안내노트",
                },
                {
                    "title": "[속보] 사건 사고",
                    "contents": keyword,
                    "postUrl": f"https://blog.naver.com/news/{keyword}",
                    "addDate": 9_000,
                    "blogName": "뉴스",
                },
            ]

        feed = build_feed(fetch_query=fake_fetch, now_ms=10_000)
        urls = [item["url"] for item in feed["items"]]
        self.assertTrue(urls)
        self.assertTrue(all("/news/" not in url for url in urls))
        self.assertEqual(feed["sort"], "latest")
        self.assertGreaterEqual(feed["items"][0]["published_at"], feed["items"][-1]["published_at"])


class PageTests(unittest.TestCase):
    def test_home_and_api_render_related_articles(self):
        def fake_fetch(keyword, limit=12):
            return [
                {
                    "title": f"{keyword} 신청 안내",
                    "contents": "최신 관련글",
                    "postUrl": f"https://blog.naver.com/post/{keyword}",
                    "addDate": 2_000,
                    "blogName": "안내노트",
                }
            ]

        app_module.get_feed = lambda force=False: build_feed(fetch_query=fake_fetch, now_ms=10_000)
        client = app_module.app.test_client()
        page = client.get("/")
        html = page.get_data(as_text=True)
        self.assertEqual(page.status_code, 200)
        self.assertIn("정부·공공기관 추천피드", html)
        self.assertIn("지원금·복지", html)
        self.assertIn("관련글", html)
        self.assertNotIn("[속보]", html)

        api = client.get("/api/gov-feed?cat=health")
        body = json.loads(api.data)
        self.assertTrue(body["items"])
        self.assertTrue(all(item["cat"] == "health" for item in body["items"]))
        self.assertTrue(all(item["kind"] == "article" for item in body["items"]))


if __name__ == "__main__":
    unittest.main()
