"""Configuration for Douban scraper."""

HOT_CATALOG_URL = "https://book.douban.com/chart"
LATEST_CATALOG_URL = "https://book.douban.com/latest"

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

CATALOG_SCHEMA = {
    "name": "DoubanCatalog",
    "baseSelector": "li.media.clearfix",
    "fields": [
        {
            "name": "title",
            "selector": "div.media__body h2 a.fleft",
            "type": "text",
        },
        {
            "name": "url",
            "selector": "div.media__body h2 a.fleft",
            "type": "attribute",
            "attribute": "href",
        },
    ],
}

BOOK_DETAIL_SCHEMA = {
    "name": "DoubanBookDetail",
    "baseSelector": "body",
    "fields": [
        {"name": "title", "selector": 'h1 span[property="v:itemreviewed"]', "type": "text"},
        {"name": "rating", "selector": "strong.rating_num", "type": "text"},
        {"name": "votes", "selector": 'span[property="v:votes"]', "type": "text"},
        {"name": "info", "selector": "#info", "type": "text"},
        {"name": "intro_all", "selector": "#link-report .all .intro", "type": "text"},
        {"name": "intro_short", "selector": "#link-report .intro", "type": "text"}
    ],
}
