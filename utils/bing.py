import os
import requests
from enum import Enum


# Bing Search API で検索するニュースカテゴリ
class BingSearchNewsCategory(Enum):
    Business = "Business"
    Entertainment = "Entertainment"
    Japan = "Japan"
    LifeStyle = "LifeStyle"
    Politics = "Politics"
    ScienceAndTechnology = "ScienceAndTechnology"
    Sports = "Sports"
    World = "World"


class BingSearchClient:

    def __init__(self):
        self.api_key = os.environ.get("BING_SEARCH_API_KEY")

    def search_web_pages(self, query: str, mkt: str = "ja-JP", count: int = 10, offset: int = 0) -> list[dict]:
        """
        Bing Web Search API を利用して、指定されたクエリに一致するWebページを検索する。

        Args:
            query (str): 検索クエリ
            mkt (str): マーケットコード
            count (int): 取得する検索結果の最大数
            offset (int): 検索結果のオフセット

        Returns:
            list[dict]: 検索結果のリスト
        """
        params = {"q": query, "mkt": mkt, "count": count, "offset": offset, "sortby": "date"}
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        resp = requests.get(f"https://api.bing.microsoft.com/v7.0/search", params=params, headers=headers)
        resp.raise_for_status()
        resp = resp.json()
        return resp["webPages"]["value"] if "webPages" in resp else []

    def search_news(
        self,
        query: str,
        mkt: str = "ja-JP",
        count: int = 10,
        offset: int = 0,
        sortby: str = "date",  # relevance,
        freshness: str = "month",  # day, week, month
    ) -> list[dict]:
        """
        Bing News Search API を利用して、指定されたクエリに一致するニュース記事を検索する。

        Args:
            query (str): 検索クエリ
            mkt (str): マーケットコード
            count (int): 取得する検索結果の最大数
            offset (int): 検索結果のオフセット
            sortby (str): ソート方法
            freshness (str): 検索対象の期間

        Returns:
            list[dict]: 検索結果のリスト
        """
        params = {"q": query, "mkt": mkt, "count": count, "offset": offset, "sortby": sortby, "freshness": freshness}
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        resp = requests.get(f"https://api.bing.microsoft.com/v7.0//news/search", params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()["value"]

    def search_news_by_category(
        self,
        category: BingSearchNewsCategory = BingSearchNewsCategory.Japan,
        mkt: str = "ja-JP",
        count: int = 10,
        offset: int = 0,
        sortby: str = "date",  # relevance,
        freshness: str = "month",  # day, week, month
    ):
        """
        Bing News Search API を利用して、指定されたカテゴリに一致するニュース記事を検索する。

        Args:
            category (BingSearchNewsCategory): ニュースカテゴリ
            mkt (str): マーケットコード
            count (int): 取得する検索結果の最大数
            offset (int): 検索結果のオフセット
            sortby (str): ソート方法
            freshness (str): 検索対象の期間

        Returns:
            list[dict]: 検索結果のリスト
        """
        params = {"category": category.value, "mkt": mkt, "count": count, "offset": offset, "sortby": sortby, "freshness": freshness}
        headers = {"Ocp-Apim-Subscription-Key": self.api_key}
        resp = requests.get(f"https://api.bing.microsoft.com/v7.0/news", params=params, headers=headers)
        resp.raise_for_status()
        return resp.json()["value"]
